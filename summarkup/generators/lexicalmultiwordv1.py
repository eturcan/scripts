import numpy as np
import re
import string
from nltk.corpus import stopwords
from summarkup.utils import detokenize, make_word_match_header
from summarkup.generators.conceptv1 import ConceptV1


en_stopwords = set(stopwords.words('english') + ["'s", "'ll", "'re"])
punc = set(string.punctuation) 
translations = ["edi-nmt", "umd-nmt", "umd-smt"]

class LexicalMultiWordV1:

    def __call__(self, doc, budget=100):
        query = doc.annotations["QUERY"]

        exact_match_sentids = set()
        stem_match_sentids = set()
        exact_matches = []
        stem_matches = []

        query_terms_found = []

        for i, utt in enumerate(doc):
            sent_ann = {
                k: doc.annotations[k]["annotation"][i]
                for k in doc.annotations.keys() 
                if k != "QUERY"
            }
            
            best_exact_trans = self.find_best_translation(sent_ann)
            exact_ann = best_exact_trans + ".exact_match"
            exact_score = doc.annotations[exact_ann]["annotation"][i]\
                ["sentence"]["sum"]
            query_terms_found.append(
                np.array(
                    doc.annotations[exact_ann]["annotation"][i]\
                        ["word"]["matches"]
                ).sum(axis=0)
            )


            best_stem_trans = self.find_best_translation(sent_ann, stem=True)
            stem_ann = best_stem_trans + ".stem_match"
            stem_score = doc.annotations[stem_ann]["annotation"][i]\
                ["sentence"]["sum"]
            query_terms_found.append(
                np.array(
                    doc.annotations[stem_ann]["annotation"][i]\
                        ["word"]["matches"]
                ).sum(axis=0)
            )

            if exact_score > 0:
                exact_matches.append((i, exact_score, best_exact_trans))
                exact_match_sentids.add(i)
                
            elif stem_score > 0:
                stem_matches.append((i, stem_score, best_stem_trans))
                stem_match_sentids.add(i)

        query_terms_found = np.stack(query_terms_found).sum(axis=0) > 0
        stopped_terms = [x.word for x in query.content.tokens 
                         if x.word.lower() not in en_stopwords]
        found_terms = [x for x, f in zip(stopped_terms, query_terms_found)
                       if f > 0]

        exact_matches = sorted(exact_matches, key=lambda x: x[1], reverse=True)
        stem_matches = sorted(stem_matches, key=lambda x: x[1], reverse=True)
        markup_lines = []


        size = 0
        if len(found_terms) > 0:
            header_line, wc = make_word_match_header(query, found_terms)
            size += wc
            markup_lines.append(header_line)
            
        if len(exact_matches) > 0:
           
            for i, score, best_trans in exact_matches:
                line, wc = self.make_utterance_markup(doc, i, best_trans, 
                                                      budget - size, query)
                markup_lines.append(line)
                size += wc
                if size >= budget:
                    break

        if len(stem_matches) > 0 and size < budget:
            
            for i, score, best_trans in stem_matches:
                line, wc = self.make_utterance_markup(doc, i, best_trans,
                                                      budget - size, query,
                                                      stem=True)
                markup_lines.append(line)
                size += wc
                if size >= budget:
                    break

        if len(markup_lines) > 0:
            return "\n".join(markup_lines)
        else:
            return ConceptV1()(doc, budget=budget)

    def make_utterance_markup(self, doc, utt_index, translation, budget, query,
                              stem=False):
        score_key = translation + (".stem_match" if stem else ".exact_match")
        match_style = "rel_close_match" if stem else "rel_exact_match"
        rel_style = "rel_close" if stem else "rel_exact"
        utt = doc.utterances[utt_index]["translations"][translation]
        raw_token_scores = np.array(
            doc.annotations[score_key]["annotation"][utt_index]\
                ["word"]["matches"]
        )
        
        query_tokens = [x.word for x in query.content.tokens 
                        if x.word.lower() not in en_stopwords]
        assert len(query_tokens) == raw_token_scores.shape[1]

        found_words = set()
        for qword, qscore in zip(query_tokens, raw_token_scores.sum(axis=0)):
            if qscore > 0:
                found_words.add(qword)

        token_scores = raw_token_scores.sum(axis=1)
        token_scores = token_scores.ravel()
        mark_sims = set()
        if any(raw_token_scores.sum(axis=0) == 0):
            sim_scores = np.array(doc.annotations[translation + ".glove42Bsim.content_semcons"]["annotation"][utt_index]["word"]["sims"]).ravel()

            for top_sim in np.argsort(sim_scores)[::-1]:
                if token_scores[top_sim] == 0:
                    mark_sims.add(top_sim)
                if len(mark_sims) >= 2:
                    break


        line_items = []
        for t, token in enumerate(utt.tokens): 
            if token_scores[t] > 0:
                line_items.append(
                    '<span_class="[STYLE]">{}</span>'.format(token.word)
                )
            elif t in mark_sims:
                line_items.append(
                    '<span_class="[REL]">{}</span>'.format(token.word)
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
        line = re.sub(r"\[REL\]", rel_style, line)
        return "<p>{}</p>\n".format(line), wc

    def find_best_translation(self, annotations, stem=False):

        scores = {}
        for trans in translations:
            ann_key = trans + (".stem_match" if stem else ".exact_match")
            exact_matches = annotations[ann_key]["sentence"]["gt0_sum"] 
#            soft_matches = annotations[trans + ".glove42Bsim.content_semcons"]["sentence"]["max"]
            scores[trans] = exact_matches 
        return sorted(scores, key=lambda x: scores[x], reverse=True)[0]

