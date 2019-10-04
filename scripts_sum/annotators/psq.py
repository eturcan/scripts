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
        psq = self.psqclient.get_psq(query.id)
#        print(psq)

        
        query_words = [
            tn.normalize(subword.strip(), False, False, False)
            for token in query.content.tokens
            if token.word.lower() not in en_stopwords
            for subword in token.word.lower().split("-")
            if subword.strip() != '' and subword not in en_stopwords
        ] 
        if query.semantic_constraint is not None:
#            sc = tn.normalize(query.semantic_constraint.text,
#                              False, False, False)
            #query_words += [x for x in sc.split() if x not in en_stopwords]
            query_words += [
                tn.normalize(subword.strip(), False, False, False)
                for token in query.semantic_constraint.tokens
                if token.word.lower() not in en_stopwords
                for subword in token.word.lower().split("-")
                if subword.strip() != '' and subword not in en_stopwords
            ]
        return {w: psq[w] for w in query_words if w in psq}

    def __call__(self, query, doc):

        #if query.example_of:
        #    print(query, "IS EXAMPLE")
        if "EXAMPLE_OF" in query.string:
            return
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
 
        #print(query.string)
        #print(" ".join(list(psq.keys())))

        scores = []
        for utt in doc.utterances:
            norm_tokens = [
                tn.normalize(t.word, False, False, False) 
                for t in utt["source"].tokens
            ]
            sentence_score = 0
            for t in norm_tokens:
                for q, translations in psq.items():
                    if translations is None:
                        from warnings import warn
                        warn("{} has empty psq translation.".format(q))
                        continue
                    if t in translations:
                        sentence_score += translations[t]
            scores.append(sentence_score)
