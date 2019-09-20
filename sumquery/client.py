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



    def queries(self, lang=None, group=None, tsv=False, 
                lexical=False, no_lexical=False, 
                conceptual=False, no_conceptual=False,
                example_of=False, no_example_of=False,
                simple=False, no_simple=False,
                multi_word=False, no_multi_word=False,
                morph=False, no_morph=False):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "list_queries",
            "lang": lang,
            "group": group, 
            "tsv": tsv,
            "lexical": lexical,
            "no_lexical": no_lexical,
            "conceptual": conceptual,
            "no_conceptual": no_conceptual,
            "example_of": example_of,
            "no_example_of": no_example_of,
            "simple": simple,
            "no_simple": no_simple,
            "multi_word": multi_word,
            "no_multi_word": no_multi_word,
            "morph": morph,
            "no_morph": no_morph,
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

    def query_type(self, query_id, component):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "query_type",
            "query_id": query_id,
            "component": component,
        }
        client.sendall(json.dumps(request).encode())
        query_type = pickle.loads(self._receive(client))
        client.close()
        return query_type


def list_queries():
    parser = argparse.ArgumentParser("List MATERIAL queries")
    parser.add_argument("port", type=int)
    parser.add_argument("--lang", default=None)
    parser.add_argument("--group", default=None)
    parser.add_argument("--tsv", action="store_true")
    parser.add_argument("--no-phrase", action="store_true")
    parser.add_argument("--phrase", action="store_true")
    parser.add_argument("--lexical", action="store_true")
    parser.add_argument("--no-lexical", action="store_true")
    parser.add_argument("--conceptual", action="store_true")
    parser.add_argument("--no-conceptual", action="store_true")
    parser.add_argument("--example-of", action="store_true")
    parser.add_argument("--no-example-of", action="store_true")
    parser.add_argument("--simple", action="store_true")
    parser.add_argument("--no-simple", action="store_true")
    parser.add_argument("--multi-word", action="store_true")
    parser.add_argument("--no-multi-word", action="store_true")
    parser.add_argument("--morph", action="store_true")
    parser.add_argument("--no-morph", action="store_true")
    args = parser.parse_args()

    client = Client(args.port)
    for q in client.queries(lang=args.lang, group=args.group, tsv=args.tsv,
                            lexical=args.lexical, no_lexical=args.no_lexical,
                            conceptual=args.conceptual, 
                            no_conceptual=args.no_conceptual,
                            example_of=args.example_of,
                            no_example_of=args.no_example_of,
                            simple=args.simple, no_simple=args.no_simple,
                            multi_word=args.multi_word,
                            no_multi_word=args.no_multi_word,
                            morph=args.morph, no_morph=args.no_morph):
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

def is_lexical():
    parser = argparse.ArgumentParser("Check if query is lexical")
    parser.add_argument("port", type=int)
    parser.add_argument("query_id")
    parser.add_argument("comp", type=int)
    args = parser.parse_args()
    client = Client(args.port)
    qt = client.query_type(args.query_id, args.comp - 1)
    print(qt["lexical"])

def is_conceptual():
    parser = argparse.ArgumentParser("Check if query is conceptual")
    parser.add_argument("port", type=int)
    parser.add_argument("query_id")
    parser.add_argument("comp", type=int)
    args = parser.parse_args()
    client = Client(args.port)
    qt = client.query_type(args.query_id, args.comp - 1)
    print(qt["conceptual"])


def is_simple():
    parser = argparse.ArgumentParser("Check if query is simple")
    parser.add_argument("port", type=int)
    parser.add_argument("query_id")
    parser.add_argument("comp", type=int)
    args = parser.parse_args()
    client = Client(args.port)
    qt = client.query_type(args.query_id, args.comp - 1)
    print(qt["simple"])

def is_morph():
    parser = argparse.ArgumentParser(
        "Check if query is morphologically constrained")
    parser.add_argument("port", type=int)
    parser.add_argument("query_id")
    parser.add_argument("comp", type=int)
    args = parser.parse_args()
    client = Client(args.port)
    qt = client.query_type(args.query_id, args.comp - 1)
    print(qt["morph"])

def is_example_of():
    parser = argparse.ArgumentParser(
        "Check if query is morphologically constrained")
    parser.add_argument("port", type=int)
    parser.add_argument("query_id")
    parser.add_argument("comp", type=int)
    args = parser.parse_args()
    client = Client(args.port)
    qt = client.query_type(args.query_id, args.comp - 1)
    print(qt["example_of"])


