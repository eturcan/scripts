import argparse
from pathlib import Path
import sumquery

ABOUT = (
    "Start an MATERIAL query server to support the SCRIPTS summarization "
    "component."
)

def main():
    parser = argparse.ArgumentParser(ABOUT)
    parser.add_argument("port", type=int, help="port to run server")
    parser.add_argument("morph_port", type=int, help="morph server port")
    parser.add_argument("nist_data", type=Path, help="path to NIST-data dir")
    parser.add_argument("-t", "--threads", default=8, 
                        help="number of handler threads")
    args = parser.parse_args()
    server = sumquery.Server(args.port, args.nist_data, args.morph_port, 
                             threads=args.threads)
    server.start()

if __name__ == "__main__": 
    main()


