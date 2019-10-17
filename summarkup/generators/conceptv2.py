
from scripts_sum.borda import merge_scores
from summarkup.utils import detokenize, make_relevant_header
import re

import numpy as np
#import re
#import string
#from summarkup.utils import make_relevant_header, detokenize
from scripts_sum.summary_instructions import get_instructions


from nltk.corpus import stopwords
en_stopwords = set(stopwords.words('english') + ["'s", "'ll", "'re"])

def apply_getter(item, getter):
    for g in getter:
        item = item[g]
    return item

def annotator_key(ann):
    return ann[0] + ":" + ".".join([str(x) for x in ann])

class ConceptV2:

    def __init__(self, translations, annotators, translation_annotators,
                 exact_matches=None,
                 stem_matches=None, soft_matches=None):
        self.translations = translations
        self.annotators = annotators
        self.translation_annotators = translation_annotators
        self.exact_matches = exact_matches
        self.stem_matches = stem_matches
        self.soft_matches = soft_matches

    def get_scores(self, doc, annotator):
        anns = doc.annotations[annotator[0]]["annotation"]
        scores = []
        for ann in anns:
            score = apply_getter(ann, annotator[1])
            if score != score:
                score = float("-inf")
            scores.append(score)
        return scores

    def get_exact_matches(self, doc, idx, trans):
        if self.exact_matches is None or trans not in self.exact_matches:
            return set()
        
        ann_name = self.exact_matches[trans]
        ann = doc.annotations[ann_name[0]]["annotation"]
        scores = np.array(apply_getter(ann[idx], ann_name[1]))
        if scores.ndim == 2:
            scores = scores.sum(axis=1)
        
        utt = doc.utterances[idx]["translations"][trans]    
        return set([t for t, s in zip(utt.tokens, scores) if s > 0.])

    def get_stem_matches(self, doc, idx, trans):
        if self.stem_matches is None or trans not in self.stem_matches:
            return set()
        
        ann_name = self.stem_matches[trans]
        ann = doc.annotations[ann_name[0]]["annotation"]
        scores = np.array(apply_getter(ann[idx], ann_name[1]))
        if scores.ndim == 2:
            scores = scores.sum(axis=1)
        
        utt = doc.utterances[idx]["translations"][trans]    
        return set([t for t, s in zip(utt.tokens, scores) if s > 0.])

    def get_soft_matches(self, doc, idx, trans):
        if self.soft_matches is None or trans not in self.soft_matches:
            return set()
        
        ann_name = self.soft_matches[trans]
        ann = doc.annotations[ann_name[0]]["annotation"]
        scores = np.array(apply_getter(ann[idx], ann_name[1]))
        if scores.ndim == 2:
            scores = scores.sum(axis=1)
        
        utt = doc.utterances[idx]["translations"][trans]    
        return set([t for t, s in zip(utt.tokens, scores) if s > 0.65])

    def get_found_words(self, doc, translations, query):

        query_words = [t.word.lower() for t in query.content.tokens]
        query_stems = [t.stem.lower() for t in query.content.tokens]
        if query.semantic_constraint is not None:
            query_words += [
                t.word.lower() for t in query.semantic_constraint.tokens
            ]
            query_stems += [
                t.stem.lower() for t in query.semantic_constraint.tokens
            ]

        query_words = set([t for t in query_words if t not in en_stopwords])
        query_stems = set([t for t in query_stems if t not in en_stopwords])

        found_words = set()
        for utt, trans in zip(doc.utterances, translations):
            for token in utt["translations"][trans].tokens:
                tokenstr = token.word.lower()
                tstem = token.stem.lower()
                if tokenstr in query_words or tstem in query_stems:
                    found_words.add(tokenstr)
        return found_words

    def get_best_translations(self, doc):

        trans_scores = [dict() for utt in doc.utterances]
        for trans, annotators in self.translation_annotators.items():
            scores = np.array(
                [
                    self.get_scores(doc, ann) for ann in annotators
                    if doc.annotations[ann[0]] is not None
                ]
            )
            # If we dont have a particular translation, skip it.
            if scores.shape != (0,):            
                scores[scores == float("-inf")] = -1
                scores = scores.sum(axis=0)
                for i, score in enumerate(scores):
                    trans_scores[i][trans] = score
        
        best_translations = []
        for ts in trans_scores:
            best_trans = sorted(ts, key=lambda x: ts[x], reverse=True)[0]
            best_translations.append(best_trans)
        return best_translations

    def __call__(self, doc, budget=100, make_header=True):
        query = doc.annotations["QUERY"]
        
        best_translations = self.get_best_translations(doc)

        score_dict = {
            annotator_key(ann): self.get_scores(doc, ann) 
            for ann in self.annotators
            if doc.annotations[ann[0]] is not None
        }

        keys = sorted(score_dict.keys())
        scores = [score_dict[key] for key in keys]
        ordered_indices, points = merge_scores(scores, return_points=True)

        header, size = make_relevant_header(query)
        markup_lines = [header]

        meta = {"translation": [], "markup": "conceptv2",
                "utterance_ids": [], "source_offsets": [], 
                "mode": doc.mode, "source_md5": doc.md5} 
        for idx in ordered_indices:
            trans = best_translations[idx]
            utt = doc.utterances[idx]["translations"][trans]
            src_utt = doc.utterances[idx]["source"]

            exact_matches = self.get_exact_matches(doc, idx, trans)
            stem_matches = self.get_stem_matches(doc, idx, trans)
            stem_matches = stem_matches - exact_matches
            soft_matches = self.get_soft_matches(doc, idx, trans)
            close_matches = stem_matches | soft_matches

            line, wc = self.make_utterance_markup(utt, budget - size, 
                exact_matches, close_matches)

            size += wc
            markup_lines.append(line)
            meta["translation"].append(trans)
            meta["utterance_ids"].append(int(idx))
            meta["source_offsets"].append(src_utt.offsets)
            if size >= budget:
                 break

        markup = "\n".join(markup_lines)

        found_terms = self.get_found_words(doc, best_translations, query)
        missing_terms = [t.word.lower() for t in query.content.tokens
                         if t.word.lower() not in found_terms and \
                            t.word.lower() not in en_stopwords]
        instr = get_instructions(query.string, found_terms, missing_terms)

        return markup, instr, meta


    def make_utterance_markup(self, utt, budget, exact_matches, close_matches):

        line_items = []
        for token in utt.tokens:
            if token in exact_matches:
                line_items.append(
                    '<span_class="[EXACTREL]">' + token.word + '</span>')
            elif token in close_matches:
                line_items.append( 
                   '<span_class="[REL]">' + token.word + '</span>')
            else:
                line_items.append(token.word)

        line = detokenize(" ".join(line_items))
        wc = len(line.split())
        if wc > budget:
            wc = budget
            line = " ".join(line.split()[:wc]) + "..."

        line = re.sub(r"span_class", "span class", line)
        line = re.sub(r"\[EXACTREL\]", "rel_exact_match", line)
        line = re.sub(r"\[REL\]", "rel_close_match", line)
        return "<p>{}</p>\n".format(line), wc
