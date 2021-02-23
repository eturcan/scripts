from pathlib import Path
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
     "PSQ_comb_v3.1_pmf1e-5_part_flat"
])

class PSQServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, port, query_data_paths):
        self.port = port
        self._cache = {}
        self._idf_cache = {}
        #for path in query_data_paths:
        #    self.import_data_from_json(path)
        with Pool() as pool:
            pool.map(self.import_data_from_json, query_data_paths)
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
        data = self.request.recv(4096)
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
    parser.add_argument("port", type=int)
    parser.add_argument("query_data", type=Path, nargs="+")
    args = parser.parse_args()

    server = PSQServer(args.port, args.query_data)

    try:
        with server:
            print("Waiting for client request on port {}..".format(args.port),
                  flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down!")


