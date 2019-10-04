import numpy as np
import string
from nltk.corpus import stopwords
en_stopwords = set(stopwords.words('english') + ["'s", "'ll", "'re"])
punc = set(string.punctuation) 


class StemMatcher:

    def __init__(self, translation, embeddings=None,
                 remove_stopwords=True):
        self.translation = translation
        self.remove_stopwords = remove_stopwords

    def filter_tokens(self, tokens):
        fltr_tokens = []
        for tok in tokens:
            if self.remove_stopwords and tok.word.lower() in en_stopwords:
                continue
            if self.remove_stopwords and all([c in punc for c in tok.word]):
                continue
            fltr_tokens.append(tok.stem)
        return fltr_tokens


    def __call__(self, query, doc):

        query_forms = self.filter_tokens(query.content.tokens)
        if query.semantic_constraint is not None \
                and query.semantic_constraint.type == "syn":
            query_forms.extend(
                self.filter_tokens(query.semantic_constraint.tokens))
 
        annotations = []
        for utt in doc:
            utt = utt["translations"][self.translation]

            matches = [] 

            for token in utt.tokens:
                utt_form = token.stem.lower()
                matches.append([1 if qf == utt_form else 0 
                                for qf in query_forms])
            
            if len(matches) > 0:
                matches = np.array(matches)
                annotations.append({
                    "sentence": {
                "sum": matches.sum(), 
                "max": matches.sum(axis=1).max(),
                "prod": matches.prod(axis=1).max(),
                "sum_min": matches.sum(axis=0).min(),
                "gt0_sum": (matches.sum(axis=0) > 0).sum(),
                    },
                    "word": {
                        "matches": np.array(matches).tolist(),
                    },
                })
            else:
                annotations.append({
                    "sentence": {
                "sum": 0, 
                "max": 0,
                "prod": 0,
                "sum_min": 0,
                "gt0_sum": 0,
                    },
                    "word": {
                        "matches": []
                    },
                })

        meta = {
            "query": query.string,
            "type": "StemMatcher", 
            "args": {"translation": self.translation, 
                     "remove_stopwords": self.remove_stopwords},
        }
        return {"annotation": annotations, "meta": meta}
