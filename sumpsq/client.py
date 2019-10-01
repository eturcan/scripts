import socket
import json
import pickle
from io import BytesIO


class PSQClient:
    def __init__(self, port):
        self.port = port

    def _send(self, connection, some_bytes):
        message_size = str(len(some_bytes)).encode()
        size_length = len(message_size)
        connection.sendall(bytes([size_length]) + message_size)
        connection.sendall(some_bytes)

    def _receive(self, connection):
        sz_length = int.from_bytes(connection.recv(1), byteorder='little')
        message_size = int(connection.recv(sz_length).decode())
        
        input_buffer = BytesIO(b' ' * message_size)
        read = 0
        while read < message_size:
            some_bytes = connection.recv(16384)
            input_buffer.write(some_bytes)
            read += len(some_bytes)
        input_buffer.seek(0)
        return input_buffer.getvalue()



    def get_psq(self, query_id):
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect(("127.0.0.1", self.port))
        self._send(connection, pickle.dumps(query_id)) 
        result = pickle.loads(self._receive(connection))
        connection.close()
        return result


def get_psq():
    import argparse
    parser = argparse.ArgumentParser("Query psq server.")
    parser.add_argument("port", type=int)
    parser.add_argument("query_id", type=str)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    client = PSQClient(args.port)
    psq = client.get_psq(args.query_id)
    if args.pretty:
        from pprint import pprint
        pprint(psq)
    else:
        print(json.dumps(psq))
