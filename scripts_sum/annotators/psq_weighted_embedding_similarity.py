import os
from sumpsq.client import PSQClient
from scripts_sum.text_normalizer import TextNormalizer
from scripts_sum.utils import unpack_masked_constant
from scripts_sum.lang import get_iso
from nltk.corpus import stopwords
en_stopwords = set(stopwords.words('english') + ["'s", "'ll", "'re"])
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class PSQWeightedEmbeddingSimilarity:

    def __init__(self, lang2emb_map, psq_port=None, embeddings=None):
    
        if psq_port is None:
            psq_port = int(os.getenv("PSQ_PORT"))
        self.psq_client = PSQClient(psq_port)

        self.lang2embeddings = {
            lang: embeddings[lang][name]
            for lang, name in lang2emb_map.items()
        }
        self.lang2emb_map = lang2emb_map



    def get_query_embeddings(self, query, lang):

        tn = TextNormalizer("en")
        psq = self.psq_client.get_psq(query.id) 
#        print(psq)
        query2emb = {}
 
#?        query_words = [
#?            tn.normalize(token.word, False, False, False)\
#?            for token in query.content.tokens
#?            if token.word.lower() not in en_stopwords
#?        ]
        query_words = [
            tn.normalize(subword.strip(), False, False, False)
            for token in query.content.tokens
            if token.word.lower() not in en_stopwords
            for subword in token.word.lower().split("-")
            if subword.strip() != '' and subword not in en_stopwords
        ]
#        if query.semantic_constraint is not None:
#            sc = tn.normalize(query.semantic_constraint.text,
#                           False, False, False)
#            query_words += [x for x in sc.split() if x not in en_stopwords]
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

        query_embs = []
        for q in query_words:

            found_words = []
            found_probs = []

            if q not in psq or psq[q] is None:
                from warnings import warn
                warn("{} has empty psq translation".format(q))
                continue

            for v, p in psq[q].items():
                if v in self.lang2embeddings[lang]:
                    found_words.append(v)
                    found_probs.append(p)

            found_embs = self.lang2embeddings[lang].lookup_sequence(
                found_words)
            query_word_emb = (np.array([found_probs]) @ found_embs)
            query_embs.append(query_word_emb)
            query2emb[q] = query_word_emb
        query_emb = np.mean(query_embs, axis=0)
        query2emb["AVG"] = query_emb
        return query2emb

    def embed_source(self, utterance, lang):
        tn = TextNormalizer(lang)
        tokens = [
            tn.normalize(x.word.lower(), False, False, False)
            for x in utterance["source"].tokens
        ]

        emb_dict = self.lang2embeddings[lang]

        source_embeddings = emb_dict.lookup_sequence(tokens)
        mask = np.array([x not in emb_dict for x in tokens])
        return source_embeddings, mask

    def __call__(self, query, doc):
        lang = get_iso(doc.source_lang)
        if lang not in self.lang2emb_map:
            from warnings import warn
            warn("No embeddings for {} loaded.".format(lang))
            return

        try:
            query_embeddings = self.get_query_embeddings(query, lang)
        except RuntimeError as e:
            if str(e) == "Bad query id: {}".format(query.id):
                from warnings import warn
                warn("No psq for {}.".format(lang))
                return
            else:
                raise e
            
        query_emb = query_embeddings["AVG"]

        annotations = []
        for utt in doc:
            utt_embs, utt_mask = self.embed_source(utt, lang)
            sims = cosine_similarity(utt_embs, query_emb).reshape(-1)
            sims = np.ma.masked_where(utt_mask, sims)
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
            "type": "PSQWeightedEmbeddingSimilarity", 
            "args": {"lang2emb_map": self.lang2emb_map,},
        }

        return {"annotation": annotations, "meta": meta}

