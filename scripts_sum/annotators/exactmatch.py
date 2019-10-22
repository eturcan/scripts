import numpy as np
import string
from nltk.corpus import stopwords
en_stopwords = set(stopwords.words('english') + ["'s", "'ll", "'re"])
punc = set(string.punctuation) 


class ExactMatcher:

    def __init__(self, translation, uncased=True, embeddings=None,
                 remove_stopwords=True):
        self.translation = translation
        self.uncased = uncased
        self.remove_stopwords = remove_stopwords

    def filter_tokens(self, tokens):
        fltr_tokens = []
        for tok in tokens:
            if self.remove_stopwords and tok.word.lower() in en_stopwords:
                continue
            if self.remove_stopwords and all([c in punc for c in tok.word]):
                continue
            if self.uncased:
                fltr_tokens.append(tok.word.lower())
            else:
                fltr_tokens.append(tok.word)
        return fltr_tokens


    def __call__(self, query, doc):

        if self.translation not in doc.utterances[0]["translations"]:
            return None

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
                utt_form = token.word.lower() if self.uncased else token.word
                matches.append([1 if qf == utt_form else 0 
                                for qf in query_forms])
            matches = np.array(matches)
            if len(query_forms) > 0 and matches.shape[0] != 0:
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
                        "sum": float("-inf"), 
                        "max": float("-inf"),
                        "prod": float("-inf"),
                        "sum_min": float("-inf"),
                        "gt0_sum": float("-inf"),
                    },
                    "word": {
                        "matches": np.array(matches).tolist(),
                    },
                })

        meta = {
            "query": query.string,
            "type": "ExactMatcher", 
            "args": {"translation": self.translation, "uncased": self.uncased},
        }
        return {"annotation": annotations, "meta": meta}
