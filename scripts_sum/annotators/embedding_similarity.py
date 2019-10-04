from nltk.corpus import stopwords
import string
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
en_stopwords = set(stopwords.words('english') + ["'s", "'ll", "'re"])
punc = set(string.punctuation) 
from scripts_sum.utils import unpack_masked_constant


class EmbeddingSimilarity:

    def __init__(self, translation, embedding_name, uncased=True,
                 remove_stopwords=True, embeddings=None):

        self.translation = translation
        self.embedding_name = embedding_name
        self.embeddings = embeddings["en"][embedding_name]
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

    def make_mask(self, tokens):
        mask = []
        for tok in tokens:
            if self.remove_stopwords and tok.word.lower() in en_stopwords:
                mask.append(1)
                continue
            elif self.remove_stopwords and all([c in punc for c in tok.word]):
                mask.append(1)
                continue
            if self.uncased:
                if tok.word.lower() not in self.embeddings:
                    mask.append(1)
                else:
                    mask.append(0)
                    
            else:
                if tok.word not in self.embeddings:
                    mask.append(1)
                else:
                    mask.append(0)
        return np.array(mask)


    def __call__(self, query, doc):

        query_tokens = query.content.tokens
        if query.semantic_constraint:
            query_tokens = query_tokens + query.semantic_constraint.tokens
        query_tokens = self.filter_tokens(query_tokens)
        query_embedding = self.embeddings.average_embedding(query_tokens)
        is_nan_query = np.any(query_embedding != query_embedding)
        annotations = []
        for utt in doc:
            utt_toks = [t.word.lower() 
                        for t in utt["translations"][self.translation].tokens]
            if len(utt_toks) == 0:
                annotations.append({
                    "sentence": { 
                        "min": float("nan"),
                        "max": float("nan"),
                        "mean": float("nan"),
                    },
                    "word": {
                        "sims": [[]], 
                    },

                })
                continue

            utt_matrix = self.embeddings.lookup_sequence(utt_toks)

            if is_nan_query:
                sims = np.full((utt_matrix.shape[0],), float('nan'))
            else:
                sims = cosine_similarity(utt_matrix, query_embedding)\
                    .reshape(-1)

            mask = self.make_mask(utt["translations"][self.translation].tokens)
            sims = np.ma.masked_where(mask, sims)
            sims.fill_value = float("-inf")
            annotations.append({
                "sentence": { 
                    "min": unpack_masked_constant(sims.min()),
                    "max": unpack_masked_constant(sims.max()),
                    "mean": unpack_masked_constant(sims.mean()),
                },
                "word": {
                    "sims": sims.filled().reshape(-1, 1).tolist(), 
                },

            })
        meta = {
            "query": query.string,
            "type": "EmbeddingSimilarity", 
            "args": {"translation": self.translation, "uncased": self.uncased,
                     'embedding_name': self.embedding_name, 
                     'remove_stopwords': self.remove_stopwords},
        }

        return {"annotation": annotations, "meta": meta}

