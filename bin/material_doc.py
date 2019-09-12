import argparse
import socket
import json


def main():
    parser = argparse.ArgumentParser("Lookup official MATERIAL documents.")
    parser.add_argument("port", type=int, help="port of running doc server")
    parser.add_argument("action", choices=["validate"])
    parser.add_argument("doc_id", help="doc id to lookup")
    args = parser.parse_args()

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", args.port))
    
    request = {
        "type": args.action, 
        "doc_id": args.doc_id, 
    }
    client.sendall(json.dumps(request).encode())
    msg = client.recv(16384).decode("utf8")
    print(msg)
    
if __name__ == "__main__":
    main()
