from sumpsq.client import PSQClient
import os
from scripts_sum.text_normalizer import TextNormalizer
from nltk.corpus import stopwords
en_stopwords = set(stopwords.words('english') + ["'s", "'ll", "'re"])


class PSQ:

    def __init__(self, port=None, embeddings=None):
        if port is None:
            port = int(os.getenv("PSQ_PORT"))
        self.psqclient = PSQClient(port)


    def get_psq(self, query):
        tn = TextNormalizer("en")
        psq_idf = self.psqclient.get_psq(query.id)
        psq = psq_idf["psq"]
        idf = psq_idf["idf"]
#        print(psq)

        
        query_words = [
            tn.normalize(subword.strip(), False, False, False)
            for token in query.content.tokens
            if token.word.lower() not in en_stopwords
            for subword in token.word.lower().split("-")
            if subword.strip() != '' and subword not in en_stopwords
        ] 
        if query.semantic_constraint is not None:
            query_words += [
                tn.normalize(subword.strip(), False, False, False)
                for token in query.semantic_constraint.tokens
                if token.word.lower() not in en_stopwords
                for subword in token.word.lower().split("-")
                if subword.strip() != '' and subword not in en_stopwords
            ]

        return {
            w: {k: v * idf[w] for k,v in psq[w].items()} 
            for w in query_words 
            if w in psq and (psq[w] is not None) and (idf[w] is not None)
        }

    def __call__(self, query, doc):
        tn = TextNormalizer(doc.source_lang)
        try:
            psq = self.get_psq(query)
        except RuntimeError as e:
            if str(e) == "Bad query id: {}".format(query.id):
                from warnings import warn
                warn("No psq for {}.".format(doc.source_lang))
                return
            else:
                raise e

        scores = []
        offsets = []
        for utt in doc.utterances:
            norm_tokens = [
                tn.normalize(t.word, False, False, False) 
                for t in utt["source"].tokens
            ]
            sentence_score = 0
            for i, t in enumerate(norm_tokens):
                for q, translations in psq.items():
                    if translations is None:
                        from warnings import warn
                        warn("{} has empty psq translation.".format(q))
                        continue
                    if t in translations:
                        offsets.append([
                            utt["source"].tokens[i].offsets,
                            translations[t]
                        ])
                            
                        sentence_score += translations[t]
            scores.append(sentence_score)
       
        meta = {
            "query": query.string,
            "type": "PSQ",
            "args": {},
            "offsets": offsets,
        } 
        return {"annotation": scores, "meta": meta}   
