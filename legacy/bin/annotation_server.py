import argparse
from pathlib import Path
import sumannotate

ABOUT = (
    "Start an MATERIAL annotation server to support the SCRIPTS summarization "
    "component."
)

def main():
    parser = argparse.ArgumentParser(ABOUT)
    parser.add_argument("port", type=int, help="port to run server")
    parser.add_argument("query_port", type=int, help="query server port")
    parser.add_argument("doc_port", type=int, help="doc server port")
#    parser.add_argument("config", type=Path, help="path to config json")
    parser.add_argument("-t", "--threads", default=8, 
                        help="number of handler threads")
    args = parser.parse_args()
    server = sumdoc.Server(args.port, args.query_port, args.doc_port, None,
 #args.config,
                           threads=args.threads)
    server.start()

if __name__ == "__main__": 
    main() 
