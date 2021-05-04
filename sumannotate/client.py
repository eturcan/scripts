import json
from pathlib import Path
import socket


class Client:
    def __init__(self, port):
        self.port = port

    def reload_annotators(self):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "reload_annotators",
        }
        client.sendall(json.dumps(request).encode())
        message = client.recv(1024).decode("utf8")
        return message 

    def reload_config(self, config_path):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "reload_config",
            "path": str(config_path),
        }
        client.sendall(json.dumps(request).encode())
        message = client.recv(1024).decode("utf8")
        return message 


    def annotate_material(self, query_id, doc_id, qcomp, output_path):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "annotate_material",
            "query_id": query_id,
            "doc_id": doc_id, 
            "component": qcomp,
            "output_path": str(output_path.resolve()),
        }
        client.sendall(json.dumps(request).encode())
        message = client.recv(1024).decode("utf8")
        return message 

    def annotate_doc(self, query_id, doc, qcomp, output_path):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "annotate_doc",
            "query_id": query_id,
            "doc": doc,
            "component": qcomp,
            "output_path": str(output_path.resolve()),
        }
        client.sendall(json.dumps(request).encode())
        message = client.recv(1024).decode("utf8")
        return message

def reload_annotators():
    import argparse
    parser = argparse.ArgumentParser(
        "Reload annotators on annotation server")
    parser.add_argument("port", type=int, help="Port of the annotation server")
    args = parser.parse_args()
    client = Client(args.port)
    print(client.reload_annotators())

def reload_config():
    import argparse
    parser = argparse.ArgumentParser(
        "Reload annotators on annotation server")
    parser.add_argument("port", type=int, help="Port of the annotation server")
    parser.add_argument("config", type=Path, help="config file to load")
    args = parser.parse_args()
    client = Client(args.port)
    print(client.reload_config(args.config.resolve()))


def annotate_material():
    import argparse
    parser = argparse.ArgumentParser(
        "Run annotators on MATERIAL query/doc pairs")
    parser.add_argument("port", type=int, help="Port of the annotation server")
    parser.add_argument("query_id", help="MATERIAL query id string") 
    parser.add_argument("doc_id", help="MATERIAL doc id string")
    parser.add_argument("qcomp", type=int, help="query component to annotate")
    parser.add_argument("output_path", type=Path, 
                        help="path to write annotations")
    args = parser.parse_args()
    client = Client(args.port)
    print(
        client.annotate_material(args.query_id, args.doc_id, args.qcomp - 1, 
                                 args.output_path))
