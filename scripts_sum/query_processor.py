import logging
import json

from .query import QueryComponent, SemanticConstraint

def process_query(query_string, morph_port, query_id=None, morph_path=None):

    logging.info("Processing {}: {}".format(query_id, query_string))
    if "," in query_string:
        c1, c2 = query_string.split(",")
        qc1 = QueryComponent.parse(c1, query_id, 1, 2, 
                                   morph_path,
                                   morph_port)
        logging.info("Processing query component: {}".format(qc1))
        qc2 = QueryComponent.parse(c2, query_id, 2, 2,
                                   morph_path,
                                   morph_port)
        logging.info("Processing query component: {}".format(qc2))
        return [qc1, qc2]
    else:
        qc1 = QueryComponent.parse(query_string, query_id, 1, 1,
                                   morph_path,
                                   morph_port)
        logging.info("Processing query component: {}".format(qc1))
        return [qc1]

