import socket
import json
import pickle
from io import BytesIO


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

    def validate(self, doc_id):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "validate",
            "doc_id": doc_id, 
        }
        client.sendall(json.dumps(request).encode())
        message = self._receive(client).decode("utf8")
        client.close()
        return message 

    def print(self, doc_id):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "print",
            "doc_id": doc_id, 
        }
        client.sendall(json.dumps(request).encode())
        message = self._receive(client).decode("utf8")
        client.close()
        print(message)
    
    def object(self, doc_id):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "object",
            "doc_id": doc_id, 
        }
        client.sendall(json.dumps(request).encode())
        doc = pickle.loads(self._receive(client))
        client.close()
        if isinstance(doc, RuntimeError):
            raise doc
        return doc

    def mode(self, doc_id):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "mode",
            "doc_id": doc_id, 
        }
        client.sendall(json.dumps(request).encode())
        mode = pickle.loads(self._receive(client))
        client.close()
        return mode

    def lang(self, doc_id):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "lang",
            "doc_id": doc_id, 
        }
        client.sendall(json.dumps(request).encode())
        lang = pickle.loads(self._receive(client))
        client.close()
        return lang
 
    def path(self, doc_id):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.port))
        request = {
            "type": "path",
            "doc_id": doc_id,
        }
        client.sendall(json.dumps(request).encode())
        path = pickle.loads(self._receive(client))
        client.close()
        return path



def main():
    import argparse
    parser = argparse.ArgumentParser("Lookup official MATERIAL documents.")
    parser.add_argument("port", type=int, help="port of running doc server")
    parser.add_argument(
        "action", choices=["validate", "print", "mode", "lang"])
    parser.add_argument("doc_id", help="doc id to lookup")
    args = parser.parse_args()

    client = Client(args.port)
    if args.action == "validate":
        print(client.validate(args.doc_id))
    elif args.action == "print":
        client.print(args.doc_id)
    elif args.action == "mode":
        print(client.mode(args.doc_id))
    elif args.action == "lang":
        print(client.lang(args.doc_id))


