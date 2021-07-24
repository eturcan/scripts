import numpy as np
import logging


def get_translation_embedding_similarity(query_component, doc, embeddings):
    for emb_name, emb_info in embeddings.items():
        emb_model = emb_info["model"]
        try:
            query_emb = query_component.embed(emb_model, content_words=True,
                                              constraint_words=True) 
        except Exception as e:
            if "No query embeddings." == str(e):
                for tr in doc.translations:
                    doc.annotate_utterances("{}_en_tr({})".format(emb_name, tr), 
                                            (tr, None))
                continue
            else:
                raise e

        for tr in doc.translations:
            logging.debug(
                "Scoring english query/{} sent emb {} sim for doc {}".format(
                    tr, emb_name, doc.id))
            doc_emb = doc.translation_sentence_embeddings(tr, emb_model)

            scores = doc_emb.dot(query_emb)
            scores[np.isnan(scores)] = float("-inf")
            argsort = np.argsort(scores)
            ann = [{"score": s} for s in scores]

            for r, i in enumerate(argsort[::-1]):
                assert ann[i]["score"] == scores[i]
                ann[i]["rank"] = r   
          
            doc.annotate_utterances("{}_en_tr({})".format(emb_name, tr), 
                                    (tr, ann))

def get_clir_source_evidence(query_component, doc, source_evidence):
    fn = "{}.txt".format(doc.id)
    if fn not in source_evidence[doc.mode]["source_evidence"]:
        logging.warn("{} not in {} source evidence".format(
            doc.id, query_component.id))
        return
    clir_matches = source_evidence[doc.mode]["source_evidence"][fn]

    for token in query_component.all_token_iter():
        if token.word in clir_matches:
            for term in clir_matches[token.word]["translations"]:
                term = dict(term)
                term["query_string"] = query_component.string
                doc.annotate_source_term(term["term"], term)                    
