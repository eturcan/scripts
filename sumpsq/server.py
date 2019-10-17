from pathlib import Path
import json
import socketserver
import pickle
from io import BytesIO


PSQ_NAMES = set([
#    "PSQ_SMT-BUILD+ParaCrawl-en2lt-word-to-word-v1",
#    "PSQ_tokenized_normalized+berk_part_flat",
    "PSQ_tokenized_normalized+berk_part_flat_keep_syn",   
    "PSQ_tokenized_normalized+berk_part_flat_keep_exampleof",
])

class PSQServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, port, query_data_paths):
        self.port = port
        self._cache = {}
        self._idf_cache = {}
        for path in query_data_paths:
            self.import_data_from_json(path)
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
        if found < 2:
            from warnings import warn
            warn("No PSQ for path: {}".format(path.parent))

class PSQRequestHandler(socketserver.BaseRequestHandler):

    def _send(self, some_bytes):
        message_size = str(len(some_bytes)).encode()
        size_length = len(message_size)
        self.request.sendall(bytes([size_length]) + message_size)
        self.request.sendall(some_bytes)

    def _receive(self):

        sz_length = int.from_bytes(self.request.recv(1), byteorder='little')
        message_size = int(self.request.recv(sz_length).decode())
        
        input_buffer = BytesIO(b' ' * message_size)
        read = 0
        while read < message_size:
            some_bytes = self.request.recv(16384)
            input_buffer.write(some_bytes)
            read += len(some_bytes)
        input_buffer.seek(0)
        return input_buffer.getvalue()

    def handle(self):
        query_id = pickle.loads(self._receive())
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


