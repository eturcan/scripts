from queryrel.client import QueryRelClient
import os
from scripts_sum.lang import get_iso


class QueryRel:

    def __init__(self, port=None, embeddings=None):
        if port is None:
            port = int(os.getenv("QUERYREL_PORT"))
        self.queryrel_client = QueryRelClient(port)

    def __call__(self, query, doc):
        if get_iso(doc.source_lang) not in ["lt", "ps", "fa", "kk","ka"]:
            return 

        query_content = query.content.text
        texts = [utt["source"].text.strip() for utt in doc.utterances]
        query_content_inputs = [
            {"src": text, "query": query_content}
            for text in texts
        ]
        
        try:
            query_content_scores = self.queryrel_client.get_relevance(
                query_content_inputs)
            query_content_scores = [
                x if x == x else 0.0
                for x in query_content_scores
            ]
        except ValueError as e:
                query_content_scores = [
                    0.0
                    for x in texts
                ]
        if query.semantic_constraint is not None:

            sc = query.semantic_constraint.text
            sc_inputs = [
                {"src": text, "query": sc}
                for text in texts
            ]
            try: 
                sc_scores = self.queryrel_client.get_relevance(
                    sc_inputs)
                sc_scores = [
                    x if x == x else 0.0
                    for x in sc_scores
                ]
            except ValueError as e:
                    sc_scores = [
                        0.0
                        for x in texts
                    ]

        else:
            sc_scores = [float("nan")] * len(texts)

        annotations = [
            {"query_content": s1, "semantic_constraint": s2}
            for s1, s2 in zip(query_content_scores, sc_scores)
        ]

        meta = {
            "query": query.string,
            "type": "QueryRel", 
        }

        return {"annotation": annotations, "meta": meta}
