import json
import os
import socketserver
from pathlib import Path
import sumdoc.client
import sumquery.client
import pickle
import torch
from scripts_sum.embeddings import Embeddings
from multiprocessing import Pool, Manager, Process, Queue
from collections import defaultdict

class RequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        data = self.request.recv(4096)
        msg = json.loads(data.decode())
        if msg['type'] == "annotate_material":
            self.annotate_material(msg["query_id"], msg["doc_id"],
                                   msg['component'],
                                   Path(msg["output_path"]))
            self.request.sendall(b'annotation done')

        elif msg['type'] == "annotate_doc":
            self.annotate_doc(msg["query_id"],msg["doc"], msg["component"],Path(msg["output_path"]))

        elif msg['type'] == "reload_annotators":
            self.server.reload_annotators()
            self.request.send(b'reload ok')

        elif msg['type'] == "reload_config":
            self.server.config = json.loads(Path(msg["path"]).read_text())
            self.request.send(b'reload ok')

    def annotate_material(self, query_id, doc_id, component, output_path):

        if self.server.verbose:
            print("annotating query-id: {} component {} doc-id {}".format(
                query_id, component, doc_id))
        query = sumquery.client.Client(self.server.query_port).object(query_id)
        doc = sumdoc.client.Client(self.server.doc_port).object(doc_id)

        query_comp = query[component]
        for ann_name, ann in self.server.annotators.items():
            if self.server.verbose:
                print("Applying annotator: {}".format(ann_name))
            try:
                doc.annotate_utterances(ann_name, ann(query_comp, doc))
            except Exception as e:
                import sys
                print("Annotation error: {} {} {} {} {} {} {}".format(
                    query_id, component, query_comp.string, doc_id, doc.mode,
                    doc.source_lang, ann_name), file=sys.stderr)
                raise e

        doc.annotate_utterances("QUERY", query_comp)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        with output_path.open("wb") as fp:
            pickle.dump(doc, fp)

    def annotate_doc(self, query_id, doc, component, output_path):
        if self.server.verbose:
            print("annotating query-id: {} component {} doc {}".format(
                query_id, component, doc))
        query = sumquery.client.Client(self.server.query_port).object(query_id)

        with open(doc,"rb") as doc_fp:
            doc = pickle.load(doc_fp)

        query_comp = query[component]
        for ann_name, ann in self.server.annotators.items():
            if self.server.verbose:
                print("Applying annotator: {}".format(ann_name))
            try:
                doc.annotate_utterances(ann_name, ann(query_comp, doc))
            except Exception as e:
                import sys
                print("Annotation error: {} {} {} {} {} {} {}".format(
                    query_id, component, query_comp.string, doc, doc.mode,
                    doc.source_lang, ann_name), file=sys.stderr)
                raise e

        doc.annotate_utterances("QUERY", query_comp)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        with output_path.open("wb") as fp:
            pickle.dump(doc, fp)


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, port, query_port, doc_port, model_dir, config_path, 
                 threads=8, verbose=False):
        super(Server, self).__init__(("127.0.0.1", port), RequestHandler)
        self.verbose = verbose
        self.port = port
        self.query_port = query_port
        self.doc_port = doc_port
        self.threads = threads
        self.model_dir = model_dir
        self.config = json.loads(config_path.read_text())
        if os.path.isfile("/outputs/cache/annotators.pkl"):
            with open("/outputs/cache/annotators.pkl","rb") as f:
                annotators_d = pickle.load(f)
                self.embeddings = annotators_d["embeddings"]
                self.annotators = annotators_d["annotators"]
        else:
            self.embeddings = self.load_embeddings(self.config)
            self.annotators = self.load_annotators(self.config)
            with open("/outputs/cache/annotators.pkl","wb") as f:
                pickle.dump({"embeddings":self.embeddings,"annotators":self.annotators},f)

    def load_annotators(self, config):
        annotators = {}
        for ann_name, ann_config in config["annotators"].items():
            mod = __import__(ann_config['module'], 
                             fromlist=[ann_config['class']])
            cls = getattr(mod, ann_config['class'])
            if self.verbose:
                print("Loading annotator {} of type {}".format(ann_name, cls))
            annotators[ann_name] = cls(
                *ann_config.get("args", []), 
                **ann_config.get("kwargs", {}), embeddings=self.embeddings)
        return annotators
    
    def load_embeddings(self, config):
        embeddings = defaultdict(dict)
        for lang, embs in config["embeddings"].items():
            for name, path in embs.items():
                filename = os.path.join(self.model_dir, path)
                if filename.endswith(".pkl"):
                    with open(filename,"rb") as emb_pkl:
                        emb = pickle.load(emb_pkl)
                elif filename.endswith(".torch"):
                    emb = torch.load(filename, map_location=torch.device('cpu'))
                else:
                    raise Exception("Embeddings need to be in pkl and torch file type. Please create pkl if the file is .txt and use scripts_sum.Embeddings.from_path()")
                print("Embeddings loaded: {} {}".format(lang, name))
                embeddings[lang][name] = emb
        return embeddings

    def reload_annotators(self):
        import importlib
        import sys
        annotators = {}
        for ann_name, ann_config in self.config["annotators"].items():
            __import__(ann_config['module'])
            mod = sys.modules[ann_config['module']]
            mod = importlib.reload(mod) 
            cls = getattr(mod, ann_config['class'])
            annotators[ann_name] = cls(
                *ann_config.get("args", []), 
                **ann_config.get("kwargs", {}), embeddings=self.embeddings)
        self.annotators = annotators

    def start(self):
        with self:
            print("Waiting for client request on port {}..".format(
                self.port), flush=True)
            self.serve_forever()

ABOUT = (
    "Start an MATERIAL annotation server to support the SCRIPTS summarization "
    "component."
)

def main():
    import argparse
    parser = argparse.ArgumentParser(ABOUT)
    parser.add_argument("port", type=int, help="port to run server")
    parser.add_argument("query_port", type=int, help="query server port")
    parser.add_argument("doc_port", type=int, help="doc server port")
    parser.add_argument("model_dir", type=Path, help="path to model dir")
    parser.add_argument("config", type=Path, help="path to config json")
    parser.add_argument("-t", "--threads", default=8, 
                        help="number of handler threads")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    server = Server(args.port, args.query_port, args.doc_port, 
                    args.model_dir, args.config,
                    threads=args.threads, verbose=args.verbose)
    server.start()
