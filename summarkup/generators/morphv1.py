from summarkup.generators.conceptv2 import ConceptV2
import numpy as np
import re
import string
from summarkup.utils import detokenize, make_word_match_header
from summarkup.generators.conceptv1 import ConceptV1
from scripts_sum.summary_instructions import get_instructions

from nltk.corpus import stopwords
en_stopwords = set(stopwords.words('english') + ["'s", "'ll", "'re"])

def apply_getter(item, getter):
    for g in getter:
        item = item[g]
    return item

def annotator_key(ann):
    return ann[0] + ":" + ".".join([str(x) for x in ann])

class MorphV1:

    def __init__(self, translations, annotators, translation_annotators,
                 default_args=None, default_kwargs=None):
        self.translations = translations
        self.annotators = annotators
        self.translation_annotators = translation_annotators
        self.default_args = default_args if default_args else []
        self.default_kwargs = default_kwargs if default_kwargs else {}


    def get_best_translations(self, doc):

        trans_scores = [dict() for utt in doc.utterances]
        for trans, annotators in self.translation_annotators.items():
            scores = np.array(
                [self.get_mt_scores(doc, ann) for ann in annotators])
            scores[scores == float("-inf")] = -1
            scores = scores.sum(axis=0)
            for i, score in enumerate(scores):
                trans_scores[i][trans] = score
        
        best_translations = []
        for ts in trans_scores:
            best_trans = sorted(ts, key=lambda x: ts[x], reverse=True)[0]
            best_translations.append(best_trans)
        return best_translations

    def get_scores(self, doc):

        scores = [] 
        for i, utt in enumerate(doc):
            score = 0
            for ann in self.annotators:
                ann = doc.annotations[ann]["annotation"][i]
                for a in ann:
                    if any([x >= 1 for x in a["match_quality"]]):
                        score += 1
            scores.append(score)
        return scores

    def get_mt_scores(self, doc, annotator):
    
        anns = doc.annotations[annotator[0]]["annotation"]
        scores = []
        for ann in anns:
            if len(ann) == 0:
                score = float(0)
            else:
                score = sum([apply_getter(a, annotator[1]) for a in ann])
            #if score != score:
            #    score = float("-inf")
            scores.append(score)
        return scores

    def get_found_words(self, doc, translations, query):

        query_words = [t.word.lower() for t in query.content.tokens]
        if query.semantic_constraint is not None:
            query_words += [
                t.word.lower() for t in query.semantic_constraint.tokens
            ]
        query_words = set([t for t in query_words if t not in en_stopwords])
        found_words = set()
        for utt, trans in zip(doc.utterances, translations):
            for token in utt["translations"][trans].tokens:
                token = token.word.lower()
                if token in query_words:
                    found_words.add(token)
        return found_words

    def __call__(self, doc, budget=100):
        query = doc.annotations["QUERY"]

        best_translations = self.get_best_translations(doc)
        scores = self.get_scores(doc)

        I = np.argsort(scores)[::-1]
        if scores[I[0]] == 0:
            return ConceptV2(*self.default_args, **self.default_kwargs)(
                doc, budget=budget)

        header = "Match found for {}, check number/tense/meaning:".format(" ".join([t.word for t in query.content.tokens]))
        size = len(header.split())
        markup_lines = ["<h1>{}</h1>".format(header)]
        for idx in I:
            score = scores[idx]
            if score == 0:
                break
            trans = best_translations[idx]
            sent = doc.utterances[idx]["translations"][trans]
            tokens = [token.word for token in sent.tokens]
            mname = self.translation_annotators[trans][0][0]
            for m in doc.annotations[mname]["annotation"][idx]:
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
            line = line.replace("RELEXACT", "rel_close_match")
            line = line.replace("span_class", "span class")
            markup_lines.append("<p>{}</p>".format(line))
            if size >= budget:
                break

        found_terms = self.get_found_words(doc, best_translations, query)
        missing_terms = [t.word.lower() for t in query.content.tokens
                         if t.word.lower() not in found_terms \
                         and t.word.lower() not in en_stopwords]
#        
        instructions = get_instructions(
            query.string, found_terms, missing_terms)
        #return "\n".join(markup_lines), instructions       
        return "\n".join(markup_lines), instructions, {}
        return "", "", {}

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
