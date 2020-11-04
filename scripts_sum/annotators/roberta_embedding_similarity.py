from torch.nn.functional import cosine_similarity

class RobertaEmbeddingSimilarity:

    def __init__(self, translation_embedding_name, query_embedding_name, embeddings=None):

        self.translation_embedding_name = translation_embedding_name
        self.query_embedding_name = query_embedding_name
        self.translation_embeddings = embeddings['roberta'][translation_embedding_name]['corpus_embeddings']
        self.translation_sentences = embeddings['roberta'][translation_embedding_name]['corpus_sentences']
        self.query_embeddings = embeddings['roberta'][query_embedding_name]


    def _get_similarity_scores(self, query_emb, doc_emb, doc_sents, utterance_inds):
        scores = cosine_similarity(query_emb.view(1, -1), doc_emb)
        scores = scores.cpu()

        scores = [scores[idx].item() for idx in range(len(scores))]

        if utterance_inds is not None:
            scores = [scores[i] for i in utterance_inds]

        return scores

    def __call__(self, query, doc):

        query_id = query.id
        query_comp = query.num
        doc_id = doc.id
        utterance_inds = doc.utterance_inds
        print(len(utterance_inds))

        doc_emb = self.translation_embeddings[doc_id]
        doc_sents = self.translation_sentences[doc_id]

        # 0 is for entire query, so need to add 1 to query comp
        try:
            query_emb = self.query_embeddings[query_id][query_comp]
        except:
            query_emb = self.query_embeddings[query_id][0]

        scores = self._get_similarity_scores(query_emb, doc_emb, doc_sents, utterance_inds)

        #annotations = [
        #    {"score": score}
        #    for score in scores
        #]

        meta = {
            "query": query.string,
            "type": "RobertaEmbeddingSimilarity",
        }

        return {"annotation": scores, "meta": meta}
