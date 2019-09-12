import socket
import json
import pickle
from io import BytesIO
import argparse


class Client:
    def __init__(self, port):
        self.port = port

    def _receive(self, client):

        sz_length = int.from_bytes(client.recv(1), byteorder='little')
        message_size = int(client.recv(sz_length).decode())
        
        input_buffer = BytesIO(b' ' * message_size)
        read = 0
        while read < message_size:
            some_bytes = client.recv(16384)
            input_buffer.write(some_bytes)
            read += len(some_bytes)
        input_buffer.seek(0)
        return input_buffer.getvalue()

    def object(self, query_id):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "material_object",
            "query_id": query_id, 
        }
        client.sendall(json.dumps(request).encode())
        doc = pickle.loads(self._receive(client))
        client.close()
        return doc

    def queries(self, lang=None, group=None, tsv=False, phrase=False,
                no_phrase=False):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "list_queries",
            "lang": lang,
            "group": group, 
            "tsv": tsv,
            "phrase": phrase,
            "no_phrase": no_phrase,
        }
        client.sendall(json.dumps(request).encode())
        queries = pickle.loads(self._receive(client))
        client.close()
        return queries 

    def list_relevant(self, query_id):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "list_relevant",
            "query_id": query_id,
        }
        client.sendall(json.dumps(request).encode())
        docs = pickle.loads(self._receive(client))
        client.close()
        return docs

    def num_components(self, query_id):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "num_components",
            "query_id": query_id,
        }
        client.sendall(json.dumps(request).encode())
        num_components = pickle.loads(self._receive(client))
        client.close()
        return num_components

def list_queries():
    parser = argparse.ArgumentParser("List MATERIAL queries")
    parser.add_argument("port", type=int)
    parser.add_argument("--lang", default=None)
    parser.add_argument("--group", default=None)
    parser.add_argument("--tsv", action="store_true")
    parser.add_argument("--no-phrase", action="store_true")
    parser.add_argument("--phrase", action="store_true")
    args = parser.parse_args()

    client = Client(args.port)
    for q in client.queries(lang=args.lang, group=args.group, tsv=args.tsv,
                            no_phrase=args.no_phrase, phrase=args.phrase):
        print(q)

def list_relevant():
    parser = argparse.ArgumentParser(
        "List ground truth relevant docs for MATERIAL queries")
    parser.add_argument("port", type=int)
    parser.add_argument("query_id")
    args = parser.parse_args()

    client = Client(args.port)
    for d in client.list_relevant(args.query_id):
        print("{part}\t{id}".format(**d))

def num_components():
    parser = argparse.ArgumentParser("Get number of query components")
    parser.add_argument("port", type=int)
    parser.add_argument("query_id")
    args = parser.parse_args()
    client = Client(args.port)
    print(client.num_components(args.query_id))
