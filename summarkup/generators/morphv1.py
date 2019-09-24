import numpy as np
import re
import string
from summarkup.utils import detokenize, make_word_match_header
from summarkup.generators.conceptv1 import ConceptV1
from scripts_sum.summary_instructions import get_instructions


punc = set(string.punctuation)
translations = ["edi-nmt", "umd-nmt", "umd-smt"]

class MorphV1:
    def __call__(self, doc, budget=100):
        query = doc.annotations["QUERY"]


#        if query.morphological_constraint.morph.pos != "NN":
#            return "<p>SKIP</p>"
        pos = "np"

        matches = []      
        match_qualities = []  
        for i, utt in enumerate(doc):

            tr2ann = {}
            tr2score = {}
            for trans in translations:
                k = trans + ".morph_match_" + pos
                ann = doc.annotations[k]["annotations"][i]
                if len(ann) > 0:
                    tr2ann[trans] = ann
                    tr2score[trans] = max([x["match_score"] for x in ann])
                 
            if len(tr2ann) == 0:
                continue

            srt_trans = sorted(tr2ann.keys(), key=lambda x: tr2score[x], 
                               reverse=True)
            if len(srt_trans) > 1 \
                    and tr2score[srt_trans[0]] == tr2score[srt_trans[1]]:
                if "nmt" in srt_trans[0]:
                    best_trans = srt_trans[0]
                else:
                    best_trans = srt_trans[1]
            else:
                best_trans = srt_trans[0]
            
            for ann in tr2ann[best_trans]:
                match_qualities.append(
                    [x >= 1 for x in ann["match_quality"]])
            matches.append({
                "sent": i,
                "trans": best_trans,
                "anns": tr2ann[best_trans],
                "score": tr2score[best_trans],
                "exact_morph": any([x["exact_morph"] 
                                    for x in tr2ann[best_trans]])
            })

        
        # sort is stable sorting should put exact matches first by higest score
        # then soft matches, by highest score
        matches.sort(key=lambda x: x["score"], reverse=True)
        matches.sort(key=lambda x: x["exact_morph"], reverse=True)

        if len(match_qualities) == 0:
            return ConceptV1()(doc, budget=budget)

        found_term_ind = np.array(match_qualities).sum(axis=0)
        found_terms = [q.word
                       for q, ind in zip(query.content.tokens, found_term_ind)
                       if ind]

        markup_lines = []

        header, size = make_word_match_header(query, found_terms)
        markup_lines.append(header)
    
        for match in matches:
            sent = doc.utterances[match["sent"]]["translations"][match["trans"]]
            tokens = [token.word for token in sent.tokens]
            for m in match["anns"]:
                for j, s in enumerate(m["match_quality"], m["token_position"]):
                    if s >= 1:
                        tokens[j] = '<span_class="RELEXACTMATCH">' \
                            + tokens[j] + '</span>'
                    else:
                        tokens[j] = '<span_class="RELEXACT">' \
                            + tokens[j] + '</span>'
                        
            line = detokenize(" ".join(tokens))
            wc = len(line.split())
            if wc + size > budget:
                wc = budget - size
                line = " ".join(line.split()[:wc]) + "..."
            
            size += wc
            line = line.replace("RELEXACTMATCH", "rel_exact_match")
            line = line.replace("RELEXACT", "rel_exact")
            line = line.replace("span_class", "span class")
            markup_lines.append("<p>{}</p>".format(line))
            if size >= budget:
                break

        missing_terms = [t.word.lower() for t in query.content.tokens
                         if t.word.lower() not in found_terms]
        
        instructions = get_instructions(
            query.string, found_terms, missing_terms)
        return "\n".join(markup_lines), instructions
