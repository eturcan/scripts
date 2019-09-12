import argparse
import socket
import json


LANG_CODES = {
    "2b": "2B",
    "lt": "2B",
    "2s": "2S",
    "bg": "2S",
}

PERIOD_CODES = {
    "2b": "OP1",
    "lt": "OP1",
    "2s": "OP1",
    "bg": "OP1",
}

def lang_code(lang):
    return LANG_CODES[lang.lower()]

def period_code(lang):
    return PERIOD_CODES[lang.lower()]

def main():
    parser = argparse.ArgumentParser("Lookup official MATERIAL queries.")
    parser.add_argument("port", type=int, help="port of running query server")
    parser.add_argument("lang", help="iso or MATERIAL language id")
    parser.add_argument("query_id", help="query id to lookup")
    args = parser.parse_args()

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", args.port))
    request = {
        "type": "material", 
        "query_id": args.query_id, 
        "language": lang_code(args.lang),
    }
    client.sendall(json.dumps(request).encode())
    
if __name__ == "__main__":
    main()
