import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import string
from nltk.corpus import stopwords
en_stopwords = set(stopwords.words('english') + ["'s", "'ll", "'re"])
punc = set(string.punctuation) 


class MorphMatcher:

    def __init__(self, translation, en_embedding_name, embeddings=None):
        self.translation = translation
        self.embeddings = embeddings["en"][en_embedding_name]
        self.en_embedding_name = en_embedding_name

    def filter_tokens(self, tokens):
        fltr_tokens = []
        for tok in tokens:
            if self.remove_stopwords and tok.word.lower() in en_stopwords:
                continue
            if self.remove_stopwords and all([c in punc for c in tok.word]):
                continue
            fltr_tokens.append(tok.word.lower())
        return fltr_tokens

    def __call__(self, query, doc):

        if self.translation not in doc.utterances[0]["translations"]:
            return None
        if query.morphological_constraint is None:
            return None

        morph = query.morphological_constraint.morph
        morph_word = morph.word.lower()

        annotations = []
        for i, utt in enumerate(doc):
            utt = utt["translations"][self.translation]
            matches = []
            for j, token in enumerate(utt.tokens):
                match = self.check_match(utt.tokens, j, query)
                if match is not None:
                    matches.append(match)
            annotations.append(matches)
        meta = {
            "query": query.string,
            "type": "MorphMatcher",
            "args": {
                "translation": self.translation,
                "en_embedding_name": self.en_embedding_name,
            },
        }

        return {"annotation": annotations, "meta": meta}



        return
        #print(query)
        if query.morphological_constraint is None:
            return None

        print(query)
        #print(query)
        #print(query.morphological_constraint)


        query_forms = self.filter_tokens(query.content.tokens)
        annotations = []
        for utt in doc:
            utt = utt["translations"][self.translation]

            matches = [] 

            for token in utt.tokens:
                utt_form = token.word.lower() if self.uncased else token.word
                matches.append([1 if qf == utt_form else 0 
                                for qf in query_forms])
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
        meta = {
            "query": query.string,
            "type": "ExactMatcher", 
            "args": {"translation": self.translation, "uncased": self.uncased},
        }
        return {"annotation": annotations, "meta": meta}

    def check_match(self, tokens, i, query):
        midx = i
        morph = query.morphological_constraint.morph
        exact_morph = False
        morph_cons = False
        match_quality = []

        for q in query.content.tokens:
            if midx == len(tokens):
                break
            if tokens[midx].word in ["``", "''"]:
                return
            if tokens[midx].pos == "PNC":
                return 
            if q == morph:
                if tokens[midx].pos == q.pos \
                        and tokens[midx].number == q.number \
                        and (
                            tokens[midx].stem.lower() == q.stem.lower() \
                            or tokens[midx].word.lower() == q.word.lower()):
                    exact_morph = True
                    morph_cons = True
                    match_quality.append(1)
                    midx += 1    
                elif tokens[midx].pos == q.pos \
                        and tokens[midx].number == q.number:

                    if tokens[midx].word.lower() in self.embeddings \
                            and q.word.lower() in self.embeddings:
                        emb1 = self.embeddings[tokens[midx].word.lower()]
                        emb2 = self.embeddings[q.word.lower()]
                        sim = cosine_similarity(emb1.reshape(1, -1), 
                                                emb2.reshape(1, -1))
                        match_quality.append(sim[0,0])
                    else:
                        match_quality.append(-1)
        
                    exact_morph = False
                    morph_cons = match_quality[-1] > .8
                    midx += 1    

                else:
                    return
            elif q.word.lower() == tokens[midx].word.lower() or \
                    q.stem.lower() == tokens[midx].stem.lower():

                match_quality.append(1)
                midx += 1
            else:
                if tokens[midx].word.lower() in self.embeddings \
                        and q.word.lower() in self.embeddings:
                    emb1 = self.embeddings[tokens[midx].word.lower()]
                    emb2 = self.embeddings[q.word.lower()]
                    sim = cosine_similarity(emb1.reshape(1, -1), 
                                            emb2.reshape(1, -1))
                    match_quality.append(sim[0,0])
                    
                else:
                    match_quality.append(-1)
                midx += 1
        if (exact_morph or morph_cons) and \
                    all([x >= .5 for x in match_quality]):
            return {"match_quality": match_quality,
                    "match_score": sum(match_quality),
                    "exact_morph": exact_morph,
                    "token_position": i}
