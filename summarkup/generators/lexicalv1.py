import numpy as np
import re
import string
from summarkup.utils import detokenize, make_word_match_header
from summarkup.generators.conceptv1 import ConceptV1
from scripts_sum.summary_instructions import get_instructions


punc = set(string.punctuation)
translations = ["edi-nmt", "umd-nmt", "umd-smt"]

class LexicalV1:


    def instructions(self, doc):
        query = doc.annotations["QUERY"]
        
        


        


    def __call__(self, doc, budget=100):
        query = doc.annotations["QUERY"]

        exact_match_sentids = set()
        stem_match_sentids = set()
        exact_matches = []
        stem_matches = []

        for i, utt in enumerate(doc):
            sent_ann = {
                k: doc.annotations[k]["annotation"][i]
                for k in doc.annotations.keys() 
                if k != "QUERY" if doc.annotations[k] is not None
            }
            
            best_exact_trans = self.find_best_translation(sent_ann)
            exact_ann = best_exact_trans + ".exact_match"
            exact_score = doc.annotations[exact_ann]["annotation"][i]\
                ["sentence"]["sum"]

            best_stem_trans = self.find_best_translation(sent_ann, stem=True)
            stem_ann = best_stem_trans + ".stem_match"
            stem_score = doc.annotations[stem_ann]["annotation"][i]\
                ["sentence"]["sum"]

            if exact_score > 0:
                exact_matches.append((i, exact_score, best_exact_trans))
                exact_match_sentids.add(i)
                
            elif stem_score > 0:
                stem_matches.append((i, stem_score, best_stem_trans))
                stem_match_sentids.add(i)

        exact_matches = sorted(exact_matches, key=lambda x: x[1], reverse=True)
        stem_matches = sorted(stem_matches, key=lambda x: x[1], reverse=True)
        markup_lines = []

        size = 0

        if len(exact_matches) > 0 or len(stem_matches) > 0:
            
            header_line, wc = make_word_match_header(
                query, [x.word for x in query.content.tokens])
            size += wc
            markup_lines.append(header_line) 

        if len(exact_matches) > 0:
#            header_line, wc = make_word_match_header(
#                query, [x.word for x in query.content.tokens])
#            size += wc
#            markup_lines.append(header_line)
           
            for i, score, best_trans in exact_matches:
                line, wc = self.make_utterance_markup(doc, i, best_trans, 
                                                      budget - size)
                markup_lines.append(line)
                size += wc
                if size >= budget:
                    break

#        header_line, wc = make_match_header(query, stem=True)
        if len(stem_matches) > 0 and size < budget:
#            size += wc
#            markup_lines.append(header_line)
            
            for i, score, best_trans in stem_matches:
                line, wc = self.make_utterance_markup(doc, i, best_trans,
                                                      budget - size, stem=True)
                markup_lines.append(line)
                size += wc
                if size >= budget:
                    break

        if len(markup_lines) > 0:
            if len(exact_matches) > 0:
                instructions = get_instructions(
                    query.string, [query.content.tokens[0].word], [])
            else:
                instructions = get_instructions(
                    query.string, [], [query.content.tokens[0].word])

            return "\n".join(markup_lines), instructions
        else:
            return ConceptV1()(doc, budget=budget)

    def make_utterance_markup(self, doc, utt_index, translation, budget, 
                              stem=False):
        score_key = translation + (".stem_match" if stem else ".exact_match")
        match_style = "rel_close_match" if stem else "rel_exact_match"
        utt = doc.utterances[utt_index]["translations"][translation]
        token_scores = np.array(
            doc.annotations[score_key]["annotation"][utt_index]\
                ["word"]["matches"]
        )
        assert token_scores.ndim == 2 and token_scores.shape[1] == 1
        token_scores = token_scores.ravel()

        line_items = []
        for t, token in enumerate(utt.tokens): 
            if token_scores[t] > 0:
                line_items.append(
                    '<span_class="[STYLE]">{}</span>'.format(token.word)
                )
            else:
                line_items.append(token.word)
                        
        line = detokenize(" ".join(line_items))
        wc = len(line.split())
        if wc > budget:
            wc = budget
            line = " ".join(line.split()[:wc]) + "..."
        line = re.sub(r"span_class", "span class", line)
        line = re.sub(r"\[STYLE\]", match_style, line)
        return "<p>{}</p>\n".format(line), wc

    def find_best_translation(self, annotations, stem=False):

        scores = {}
        for trans in translations:
            ann_key = trans + (".stem_match" if stem else ".exact_match")
            exact_matches = annotations[ann_key]["sentence"]["sum"] 
#            soft_matches = annotations[trans + ".glove42Bsim.content_semcons"]["sentence"]["max"]
            scores[trans] = exact_matches 
        return sorted(scores, key=lambda x: scores[x], reverse=True)[0]

