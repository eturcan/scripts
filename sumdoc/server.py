import json
import socketserver
from pathlib import Path
import pickle
from scripts_sum.query_processor import process_query
from scripts_sum.text_document import TextDocument
from scripts_sum.audio_document import SpeechDocument
from scripts_sum.lang import get_iso


class RequestHandler(socketserver.BaseRequestHandler):

    def _send(self, some_bytes):
        message_size = str(len(some_bytes)).encode()
        size_length = len(message_size)
        self.request.sendall(bytes([size_length]) + message_size)
        self.request.sendall(some_bytes)

    def handle(self):
        data = self.request.recv(4096)
        msg = json.loads(data.decode())
        if msg["type"] == "validate":
            self._send(
                self.server.validate_doc(msg["doc_id"]).encode("utf8"))

        elif msg["type"] == "print": 
            doc = self.server.new_doc(msg["doc_id"])
            self._send(str(doc).encode("utf8"))

        elif msg["type"] == "object": 
            doc = self.server.new_doc(msg["doc_id"])
            self._send(pickle.dumps(doc))

        elif msg['type'] == 'mode':
            self._send(
                pickle.dumps(self.server.doc_cache[msg['doc_id']]['mode']))

        elif msg['type'] == 'lang':
            self._send(
                pickle.dumps(get_iso(
                    self.server.doc_cache[msg['doc_id']]['lang'])))

    def process_material_query(self, msg):
        lang, query_id = msg["language"], msg["query_id"]
        lang_query_id = (lang, query_id)

        if lang_query_id in self.server.cache:
            return self.server.cache[lang_query_id]

        query_string = self.server.material_queries[lang][query_id]
        query = process_query(query_string, self.server.morph_port)
        self.server.cache[lang_query_id] = query
        return query 

class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, port, nist_data, config_path, threads=8):
        super(Server, self).__init__(("127.0.0.1", port), RequestHandler)
        self.port = port
        self.nist_data = nist_data
        self.threads = threads
        self.doc_cache = {}
        self.ds_cache = {}
        self.read_config(config_path)

    def read_config(self, config_path):
        config = json.loads(config_path.read_text())
        for ds in config:
            self.load_dataset(ds)
            self.ds_cache[ds["name"]] = ds         
        
    def load_dataset(self, config):
        index_path = self.nist_data / config["index"]
        if "text" in config:
            text_source_dir = self.nist_data / config["text"]["source"]  
        else:
            text_source_dir = None
        if "audio" in config:
            audio_source_dir = self.nist_data / config["audio"]["source"]  
            audio_metadata = self.nist_data / config["audio_metadata"]
            with audio_metadata.open("r") as fp:
                did2audtype = {}
                for line in fp:
                    if line.strip() == "":
                        continue
                    wav, audtype = line.strip().split("\t")[:2]
                    did2audtype[wav[:-4]] = audtype
                    
        else:
            audio_source_dir = None
        with index_path.open("r") as fp:
            fp.readline() # consume header
            for line in fp:
                doc_id = line.strip()
                if text_source_dir and \
                        (text_source_dir / "{}.txt".format(doc_id)).exists():
                    mode = "text"
                elif audio_source_dir and \
                        (audio_source_dir / "{}.wav".format(doc_id)).exists():
                    mode = "audio"
                else:
                    raise Exception(
                        "Could not find source for doc id: {}".format(doc_id))
                assert doc_id not in self.doc_cache
                self.doc_cache[doc_id] = {"ds": config["name"], "mode": mode,
                                          "lang": config["lang"]}
                if mode == "audio":
                    self.doc_cache[doc_id]["audio_type"] = did2audtype[doc_id]

    def validate_doc(self, doc_id):
        if doc_id not in self.doc_cache:
            return "Document {} not in cache!".format(doc_id)
        mode = self.doc_cache[doc_id]["mode"]
        ds = self.doc_cache[doc_id]["ds"]
        if mode == "audio":
           return self.validate_audio(ds, doc_id)
        else:
            return self.validate_text(ds, doc_id)

    def retrieve_text_paths(self, ds_id, doc_id):
        ds = self.ds_cache[ds_id]["text"]
        return {
            "source": self.nist_data / ds["source"] / "{}.txt".format(doc_id),
            "sentence_segmentation": (
                self.nist_data / ds["sentence_segmentation"] 
                / "{}.txt".format(doc_id)
            ),
            "translations": {
                x["name"]: self.nist_data / x["path"] / "{}.txt".format(doc_id)
                for x in ds["translations"]
            },
            "translation_morphology": {
                x["name"]: (
                    self.nist_data / x["morph"] / "{}.txt".format(doc_id))
                for x in ds["translations"]
            },
            "source_morphology": (
                self.nist_data / ds["source_morphology"] 
                / "{}.txt".format(doc_id)
            ),
        }

    def retrieve_audio_paths(self, ds_id, doc_id):
        at = self.doc_cache[doc_id]["audio_type"]
        ds = self.ds_cache[ds_id]["audio"]
        return {
            "source": self.nist_data / ds["source"] / "{}.wav".format(doc_id),
            "asr": {
                "utterances": (
                    self.nist_data / ds[at]["asr"] / "{}.utt".format(doc_id)
                ),
                "tokens": (
                    self.nist_data / ds[at]["asr"] / "{}.ctm".format(doc_id)
                ),
            },
            "translations": {
                x["name"]: self.nist_data / x["path"] / "{}.txt".format(doc_id)
                for x in ds[at]["translations"]
            },
            "translation_morphology": {
                x["name"]: (
                    self.nist_data / x["morph"] / "{}.txt".format(doc_id))
                for x in ds[at]["translations"]
            },
            "asr_morphology": (
                self.nist_data / ds[at]["asr_morphology"] 
                / "{}.txt".format(doc_id)
            ),
        }


    def new_doc(self, doc_id): 
        if doc_id not in self.doc_cache:
            return RuntimeError("bad doc id: {}".format(doc_id))

        mode = self.doc_cache[doc_id]["mode"]
        ds = self.doc_cache[doc_id]["ds"]
        lang = self.doc_cache[doc_id]["lang"]

        if mode == "audio":
            try:
                paths = self.retrieve_audio_paths(ds, doc_id)
                return SpeechDocument.new(paths["source"],
                                           paths["asr"],
                                           paths["asr_morphology"], 
                                           paths["translations"],
                                           paths["translation_morphology"],
                                           doc_id=doc_id, lang=lang)
            except RuntimeError as e:
                return e
  
        else:
            try:
                paths = self.retrieve_text_paths(ds, doc_id)
                return TextDocument.new(paths["source"],
                                        paths["sentence_segmentation"],
                                        paths["source_morphology"], 
                                        paths["translations"],
                                        paths["translation_morphology"],
                                        doc_id=doc_id, lang=lang)
            except RuntimeError as e:
                return e

    def validate_text(self, ds, doc_id):
        paths = self.retrieve_text_paths(ds, doc_id)

        if not paths["source"].exists():
            return "source {} does not exist".format( 
                paths["source"])

        elif not paths["sentence_segmentation"].exists():
            return "sent seg {} does not exist".format( 
                paths["sentence_segmentation"])

        for tr_name, tr_path in paths["translations"].items():
            if not tr_path.exists():
                return "translation {} does not exist".format(tr_path)

        for tr_name, tr_path in paths["translation_morphology"].items():
            if not tr_path.exists():
                return "translation morphology {} does not exist".format(
                    tr_path)

        if not paths["source_morphology"].exists():
            return "source morphology {} does not exist".format(
                paths["source_morphology"])

        try:
            doc = TextDocument.new(paths["source"],
                                   paths["sentence_segmentation"],
                                   paths["source_morphology"], 
                                   paths["translations"],
                                   paths["translation_morphology"],
                                   doc_id=doc_id)
        except RuntimeError as e:
            return str(e)

        return "{} ok!".format(doc_id)

    def validate_audio(self, ds, doc_id):
        paths = self.retrieve_audio_paths(ds, doc_id)

        if not paths["source"].exists():
            return "source {} does not exist".format( 
                paths["source"])

        elif not paths["asr"]["utterances"].exists():
            return "asr utt {} does not exist".format( 
                paths["asr"]["utterances"])

        elif not paths["asr"]["tokens"].exists():
            return "asr ctm {} does not exist".format( 
                paths["asr"]["tokens"])

        for tr_name, tr_path in paths["translations"].items():
            if not tr_path.exists():
                return "translation {} does not exist".format(tr_path)

        for tr_name, tr_path in paths["translation_morphology"].items():
            if not tr_path.exists():
                return "translation morphology {} does not exist".format(
                    tr_path)

        if not paths["asr_morphology"].exists():
            return "asr morphology {} does not exist".format(
                paths["asr_morphology"])

        try:
            audio = SpeechDocument.new(paths["source"],
                                       paths["asr"],
                                       paths["asr_morphology"], 
                                       paths["translations"],
                                       paths["translation_morphology"],
                                       doc_id=doc_id)
        except RuntimeError as e:
            return str(e)

        return "{} ok!".format(doc_id)


    def start(self):
        with self:
            print("Waiting for client request on port {}..".format(
                self.port), flush=True)
            self.serve_forever()

ABOUT = (
    "Start an MATERIAL document server to support the SCRIPTS summarization "
    "component."
)

def main():
    import argparse
    parser = argparse.ArgumentParser(ABOUT)
    parser.add_argument("port", type=int, help="port to run server")
    parser.add_argument("nist_data", type=Path, help="path to NIST-data dir")
    parser.add_argument("config", type=Path, help="path to config json")
    parser.add_argument("-t", "--threads", default=8, 
                        help="number of handler threads")
    args = parser.parse_args()
    server = Server(args.port, args.nist_data, args.config,
                    threads=args.threads)
    server.start()
