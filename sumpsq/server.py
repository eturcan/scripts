from pathlib import Path
import os
import json
import socketserver
import pickle
from io import BytesIO
from multiprocessing import Pool

PSQ_NAMES = set([
#    "PSQ_SMT-BUILD+ParaCrawl-en2lt-word-to-word-v1",
#    "PSQ_tokenized_normalized+berk_part_flat",
#    "PSQ_tokenized_normalized+berk_part_flat_keep_syn",   
#    "PSQ_tokenized_normalized+berk_part_flat_keep_exampleof",
#    "PSQ_tokenized-normalized+panlex+opus+berk_part_flat_CDF097",
     "PSQ_mbertcc_v3.5_pmf1e-5_stemEN_phrases_sdm_ptable_mbertcc_v3.5_pmf1e-5_stmEN_part_flat",
])

def import_data_from_json(inp):
    path, psq_names = inp

    data = json.loads(path.read_text())
    query_id = data["query_id"]
    idf_cache = data["english"]["idf"]
    found = 0
    cache = dict()
    for query in data["queries"]:
        if query["type"] in psq_names:
            for k, v in query["translations"].items():
                cache[k] = v
            found += 1
    if found < 1:
        from warnings import warn
        warn("No PSQ matches for path and psq names: {} {}. Try checking for path or psq_names".format(path, psq_names))
    return query_id, idf_cache, cache



class PSQServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, port, query_data_paths, psq_names):
        self.port = port
        self._cache = {}
        self._idf_cache = {}

        # cache for convenience
        if not os.path.exists("/outputs/cache"):
            os.makedirs("/outputs/cache")

        if os.path.isfile("/outputs/cache/psq.pkl"):
            with open("/outputs/cache/psq.pkl","rb") as f:
                psq_d = pickle.load(f)
                self._cache = psq_d["cache"]
                self._idf_cache = psq_d["idf_cache"]
        else:
            if query_data_paths is not None and psq_names is not None:
                with Pool() as pool:
                    for cache in pool.imap_unordered(import_data_from_json, [(qdp, psq_names) for qdp in query_data_paths]):
                        query_id, idf_cache, cache_d = cache

                        self._idf_cache[query_id] = idf_cache
                        if query_id not in self._cache:
                            self._cache[query_id] = dict()
                        self._cache[query_id].update(cache_d)

                    # save to cache
                    with open("/outputs/cache/psq.pkl","wb") as f:
                        pickle.dump({"cache":self._cache, "idf_cache":self._idf_cache}, f)
        super(PSQServer, self).__init__(("127.0.0.1", port), PSQRequestHandler)

    def import_data_from_json(self, path):
        data = json.loads(path.read_text())
        query_id = data["query_id"]
        self._idf_cache[query_id] = data["english"]["idf"]
        found = 0
        for query in data["queries"]:
            if query["type"] in PSQ_NAMES:
                if query_id not in self._cache:
                    self._cache[query_id] = {}
                for k, v in query["translations"].items():
                    self._cache[query_id][k] = v
                found += 1
        if found < 1:
            from warnings import warn
            warn("No PSQ for path: {}".format(path))

    def add_psq(self, query_id, psq_dict, idf_dict):
        self._cache[query_id] = psq_dict
        self._idf_cache[query_id] = idf_dict

class PSQRequestHandler(socketserver.BaseRequestHandler):

    def _send(self, some_bytes):
        message_size = str(len(some_bytes)).encode()
        size_length = len(message_size)
        self.request.sendall(bytes([size_length]) + message_size)
        self.request.sendall(some_bytes)

    def handle(self):
        data = self.request.recv(8192)
        msg = json.loads(data.decode())
        if msg['type'] == 'add_psq':
            self.server.add_psq(msg['query_id'], msg['psq_dict'],
                                msg['idf_dict'])
            self._send(pickle.dumps('SUCCESS'))
        elif msg['type'] == 'get_psq':
            query_id = msg['query_id']
            if query_id in self.server._cache:
                self._send(
                    pickle.dumps({
                        "psq": self.server._cache[query_id], 
                        "idf": self.server._idf_cache[query_id]
                    })
                )
            else:
                self._send(pickle.dumps(
                    RuntimeError("Bad query id: {}".format(query_id))))

def sumpsq_server():
    import argparse
    parser = argparse.ArgumentParser("Start PSQ server.")
    parser.add_argument("--port", type=int)
    parser.add_argument("--query_data", type=Path, default=None,  nargs="+")
    parser.add_argument("--psq_names", default=None, nargs='+')
    args = parser.parse_args()

    psq_names = set(args.psq_names) if args.psq_names is not None else None

    server = PSQServer(args.port, args.query_data, psq_names)

    try:
        with server:
            print("Waiting for client request on port {}..".format(args.port),
                  flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down!")


