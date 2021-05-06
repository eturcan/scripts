import json
import socketserver
import pickle
from pathlib import Path
from scripts_sum.query_processor import process_query
from scripts_sum.lang import get_material
from collections import defaultdict
import re


class RequestHandler(socketserver.BaseRequestHandler):

    def _send(self, some_bytes):
        message_size = str(len(some_bytes)).encode()
        size_length = len(message_size)
        self.request.sendall(bytes([size_length]) + message_size)
        self.request.sendall(some_bytes)

    def handle(self):
        data = self.request.recv(4096)
        msg = json.loads(data.decode())
        if msg["type"] == "material_object":
            query = self.server.lookup_material(msg["query_id"])
            self._send(pickle.dumps(query))
        elif msg["type"] == "list_queries":
            queries = self.server.list_queries(
                lang=get_material(msg["lang"]) if msg["lang"] else None,
                group=msg["group"], tsv=msg["tsv"], 
                lexical=msg["lexical"],
                no_lexical=msg["no_lexical"],
                conceptual=msg["conceptual"],
                no_conceptual=msg["no_conceptual"],
                example_of=msg["example_of"],
                no_example_of=msg["no_example_of"],
                simple=msg["simple"],
                no_simple=msg["no_simple"],
                multi_word=msg["multi_word"],
                no_multi_word=msg["no_multi_word"],
                morph=msg["morph"],
                no_morph=msg["no_morph"])

            self._send(pickle.dumps(queries))
        elif msg["type"] == "num_components":
            nc = self.server.num_components(msg["query_id"])
            self._send(pickle.dumps(nc))
        elif msg["type"] == "list_relevant":
            self._send(
                pickle.dumps(
                    self.server.list_relevant_docs(msg["query_id"])))

        elif msg["type"] == "query_type":
            self._send(
                pickle.dumps(
                    self.server.query_type_from_id(msg["query_id"],
                                                   msg["component"])))

        elif msg['type'] == 'add_query_str':
            print('Adding query: {}'.format(msg['query_str']))
            self.server.add_query_str(msg['query_id'], msg['query_str'])

    def process_material_query(self, msg):
        lang, query_id = msg["language"], msg["query_id"]
        lang_query_id = (lang, query_id)

        if lang_query_id in self.server.cache:
            return self.server.cache[lang_query_id]

        query_string = self.server.material_queries[lang][query_id]
        query = process_query(query_string, self.server.morph_port)
        self.server.cache[lang_query_id] = query
        return query 

class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, port, nist_data, morph_port, config, 
                 query_proc_dir, threads=8):
        super(Server, self).__init__(("127.0.0.1", port), RequestHandler)
        self.port = port
        self.nist_data = nist_data
        self.threads = threads
        self.cache = {}
        self._M_queries, self._M_q2lang, self._M_q2period, \
            self._M_q2group, self._M_q2rel = \
            dict(), dict(), dict(), dict(), dict() 
            #self.read_material_query_manifests(config)
        self.morph_port = morph_port
        self.query_proc_dir = query_proc_dir

    def read_material_query_manifests(self, configs):
        all_queries = {}
        query2lang = {}
        query2period = {}
        query2group = {}
        query2rel = defaultdict(list)

        for config in configs["query_lists"]:
            lang = config["lang"]
            period = config["period"]
            query_group = config["group"]
            rel_docs = ()
#?        for lang, period, rel_docs in [
#?                    ("1A", "BASE", ()), 
#?                    ("1B", "BASE", ()), 
#?                    ("1S", "BASE", ()),
#?                    ("2S", "OP1", ()),
#?                    ("2B", "OP1", ())]:
#("DEV", "DEV_ANNOTATION"),
#                                   ("ANALYSIS", "ANALYSIS_ANNOTATION")))]:
#            lang_dir = (
#                self.nist_data / lang / 
#                "IARPA_MATERIAL_{}-{}".format(period, lang)
#            )

#            for query_group in lang_dir.glob("QUERY*"):
            query_list = self.nist_data / config["path"]
            with query_list.open("r") as fp:
                fp.readline()
                for line in fp:
                    items = line.strip().split("\t")
                    assert items[0] not in all_queries
                    all_queries[items[0]] = items[1]
                    query2lang[items[0]] = lang
                    query2period[items[0]] = period
                    query2group[items[0]] = query_group
        
        
            for part, annotation_dir in rel_docs:
                ann_path = lang_dir / annotation_dir / "query_annotation.tsv"
                with ann_path.open("r") as fp:
                    fp.readline()
                    for line in fp:
                        qid, docid = line.strip().split("\t")
                        query2rel[qid].append({'part': part, 'id': docid})
        for qrel_list in configs["annotations"]:
            with (self.nist_data / qrel_list).open("r") as fp:
                fp.readline()
                for line in fp:
                    q,d = line.strip().split("\t")
                    query2rel[q].append(d)

        return all_queries, query2lang, query2period, query2group, query2rel

    def lookup_material(self, query_id):
        if query_id in self.cache:
            return self.cache[query_id]

        if query_id in self._M_queries:
            query_string = self._M_queries[query_id]
            query = process_query(query_string, self.morph_port, 
                                  query_id=query_id)
            self.cache[query_id] = query
        else:
            query_data = json.loads(
                (self.query_proc_dir / query_id).read_text())
            query_string = query_data["IARPA_query"]
            query = process_query(query_string, self.morph_port, 
                                  query_id=query_id)
            self.cache[query_id] = query
        return query 

    def list_queries(self, lang=None, group=None, tsv=False, 
                     lexical=False, no_lexical=False, 
                     conceptual=False, no_conceptual=False,
                     example_of=False, no_example_of=False,
                     simple=False, no_simple=False,
                     multi_word=False, no_multi_word=False,
                     morph=False, no_morph=False):
        tmp = (
            "{id:10s} {lang:2s} {group:16s} {num} {str:25s}"
        )
        queries = []
        for query in sorted(self._M_queries.keys()):
            if lang is not None:
                if lang != self._M_q2lang[query]:
                    continue
            if group is not None:
                if group != self._M_q2group[query]:
                    continue

            if tsv:

                query_strings = self._M_queries[query].split(",")
                query_types = [self.get_query_type(x) for x in query_strings]

                #qobj = self.lookup_material(query)
                for i, qtype in enumerate(query_types, 1):

                    qfields = {
                        "id": query,
                        "lang": self._M_q2lang[query],
                        "group": self._M_q2group[query],
                    }

                    if conceptual and not qtype["conceptual"]:
                        continue
                    if no_conceptual and qtype["conceptual"]:
                        continue
                    if lexical and not qtype["lexical"]:
                        continue
                    if no_lexical and qtype["lexical"]:
                        continue
                    if example_of and not qtype["example_of"]:
                        continue
                    if no_example_of and qtype["example_of"]:
                        continue
                    if simple and not qtype["simple"]:
                        continue
                    if no_simple and not qtype["simple"]:
                        continue
                    if multi_word and not qtype["multi-word"]:
                        continue
                    if no_multi_word and qtype["multi-word"]:
                        continue
                    if morph and not qtype["morph"]:
                        continue
                    if no_morph and qtype["morph"]:
                        continue
#                    if no_phrase and c.phrasal:
#                        continue
#
#                    if phrase and not c.phrasal:
#                        continue
#                    
                    qfields['str'] = query_strings[i-1]
                    #qfields['cls'] = c.classification
                    qfields['num'] = "{}/{}".format(i, len(query_types))
                    #qfields['phrase'] = c.phrasal
                    l = tmp.format(**qfields)
                    queries.append(l)
            else:
                queries.append(query)
                
        return queries

    def list_relevant_docs(self, query_id):
        rel = []
        for doc in self._M_q2rel[query_id]:
             rel.append(doc)
        return rel

    def num_components(self, query_id):
        if query_id in self._M_queries:
            return 2 if "," in self._M_queries[query_id] else 1
        query_data = json.loads((self.query_proc_dir / query_id).read_text())
        return 2 if "," in query_data["IARPA_query"] else 1

    def start(self):
        with self:
            print("Waiting for client request on port {}..".format(
                self.port), flush=True)
            self.serve_forever()

    def add_query_str(self, query_id, query_str):
        self._M_queries[query_id] = query_str

    def query_type_from_id(self, query_id, component):
        if query_id in self._M_queries:
            query_string = self._M_queries[query_id].split(",")[component]
        else:
            query_string = json.loads(
                (self.query_proc_dir / query_id).read_text())["IARPA_query"]\
                .split(",")[component]
        return self.get_query_type(query_string)

    def get_query_type(self, query_string):

        if "[syn" in query_string:
            semantic_constraint = "syn"
        elif "[hyp" in query_string:
            semantic_constraint = "hyp"
        elif "[evf" in query_string:
            semantic_constraint = "evf"
        else:
            semantic_constraint = None
        
        query_string = re.sub(r"\[.*?\]", "", query_string)
        
        if "+" in query_string:
            conceptual = True
            lexical = False
            example_of = False
        elif "EXAMPLE_OF" in query_string:
            conceptual = False
            lexical = False
            example_of = True
        else:            
            conceptual = False
            lexical = True
            example_of = False

        if '"' in query_string:
            multiword = True
            simple = False
        else:
            multiword = False
            simple = True
        
        if "<" in query_string:
            morph = True
        else:
            morph = False

        return {
            "conceptual": conceptual, 
            "lexical": lexical, 
            "example_of": example_of, 
            "semantic_constraint": semantic_constraint,
            "multi-word": multiword,
            "simple": simple,
            "morph": morph,
        }

ABOUT = (
    "Start an MATERIAL query server to support the SCRIPTS summarization "
    "component."
)

def main():
    import argparse
    parser = argparse.ArgumentParser(ABOUT)
    parser.add_argument("port", type=int, help="port to run server")
    parser.add_argument("morph_port", type=int, help="morph server port")
    parser.add_argument("nist_data", type=Path, help="path to NIST-data dir")
    parser.add_argument("config", type=Path, help="config path")
    parser.add_argument("query_processor", type=Path, 
                        help="path to query processor directory")
    parser.add_argument("-t", "--threads", default=8, 
                        help="number of handler threads")
    args = parser.parse_args()
    server = Server(args.port, args.nist_data, args.morph_port, 
                    json.loads(args.config.read_text()),
                    args.query_processor,
                    threads=args.threads)
    server.start()
