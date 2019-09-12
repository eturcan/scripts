import argparse
from pathlib import Path
import sumdoc

ABOUT = (
    "Start an MATERIAL document server to support the SCRIPTS summarization "
    "component."
)

def main():
    parser = argparse.ArgumentParser(ABOUT)
    parser.add_argument("port", type=int, help="port to run server")
    parser.add_argument("nist_data", type=Path, help="path to NIST-data dir")
    parser.add_argument("config", type=Path, help="path to config json")
    parser.add_argument("-t", "--threads", default=8, 
                        help="number of handler threads")
    args = parser.parse_args()
    server = sumdoc.Server(args.port, args.nist_data, args.config,
                           threads=args.threads)
    server.start()

if __name__ == "__main__": 
    main() 
