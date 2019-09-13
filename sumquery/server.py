import json
import socketserver
import pickle
from pathlib import Path
from scripts_sum.query_processor import process_query
from scripts_sum.lang import get_material
from collections import defaultdict


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
                group=msg["group"], tsv=msg["tsv"], no_phrase=msg['no_phrase'],
                phrase=msg['phrase'])
            self._send(pickle.dumps(queries))
        elif msg["type"] == "num_components":
            nc = self.server.num_components(msg["query_id"])
            self._send(pickle.dumps(nc))
        elif msg["type"] == "list_relevant":
            self._send(
                pickle.dumps(
                    self.server.list_relevant_docs(msg["query_id"])))
        

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
    def __init__(self, port, nist_data, morph_port, threads=8):
        super(Server, self).__init__(("127.0.0.1", port), RequestHandler)
        self.port = port
        self.nist_data = nist_data
        self.threads = threads
        self.cache = {}
        self._M_queries, self._M_q2lang, self._M_q2period, \
            self._M_q2group, self._M_q2rel = \
            self.read_material_query_manifests()
        self.morph_port = morph_port

    def read_material_query_manifests(self):
        all_queries = {}
        query2lang = {}
        query2period = {}
        query2group = {}
        query2rel = defaultdict(list)
        for lang, period, rel_docs in [
                    ("1A", "BASE", ()), 
                    ("1B", "BASE", ()), 
                    ("1S", "BASE", ()),
                    ("2S", "OP1", ()),
                    ("2B", "OP1", (("DEV", "DEV_ANNOTATION"),
                                   ("ANALYSIS", "ANALYSIS_ANNOTATION")))]:
            lang_dir = (
                self.nist_data / lang / 
                "IARPA_MATERIAL_{}-{}".format(period, lang)
            )

            for query_group in lang_dir.glob("QUERY*"):
                query_list = lang_dir / query_group / "query_list.tsv"
                with query_list.open("r") as fp:
                    fp.readline()
                    for line in fp:
                        items = line.strip().split("\t")
                        assert items[0] not in all_queries
                        all_queries[items[0]] = items[1]
                        query2lang[items[0]] = lang
                        query2period[items[0]] = period
                        query2group[items[0]] = str(query_group.name)
            
            
            for part, annotation_dir in rel_docs:
                ann_path = lang_dir / annotation_dir / "query_annotation.tsv"
                with ann_path.open("r") as fp:
                    fp.readline()
                    for line in fp:
                        qid, docid = line.strip().split("\t")
                        query2rel[qid].append({'part': part, 'id': docid})
                        

        return all_queries, query2lang, query2period, query2group, query2rel

    def lookup_material(self, query_id):
        if query_id in self.cache:
            return self.cache[query_id]

        query_string = self._M_queries[query_id]
        query = process_query(query_string, self.morph_port, query_id=query_id)
        self.cache[query_id] = query
        return query 

    def list_queries(self, lang=None, group=None, tsv=False, phrase=False,
                     no_phrase=False):
        queries = []
        for query in sorted(self._M_queries.keys()):
            if lang is not None:
                if lang != self._M_q2lang[query]:
                    continue
            if group is not None:
                if group != self._M_q2group[query]:
                    continue

            if tsv:
                tmp = "{id:12s}\t{lang:2s}\t{group:12s}\t{num}\t{str:25s}\t{cls:25s}\t{phrase}"
                qobj = self.lookup_material(query)
                for i, c in enumerate(qobj, 1):
                    qfields = {
                        "id": qobj[0].id, 
                        "lang": self._M_q2lang[query],
                        "group": self._M_q2group[query],
                    }

                    if no_phrase and c.phrasal:
                        continue

                    if phrase and not c.phrasal:
                        continue
                    
                    qfields['str'] = c.string
                    qfields['cls'] = c.classification
                    qfields['num'] = "{}/{}".format(i, len(qobj))
                    qfields['phrase'] = c.phrasal
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
        return 2 if "," in self._M_queries[query_id] else 1

    def start(self):
        with self:
            print("Server started on port", self.port)
            print("Waiting for client request..")
            self.serve_forever()

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
    parser.add_argument("-t", "--threads", default=8, 
                        help="number of handler threads")
    args = parser.parse_args()
    server = Server(args.port, args.nist_data, args.morph_port, 
                    threads=args.threads)
    server.start()