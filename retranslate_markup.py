import argparse
import os
import re
import copy
import pickle
import json
from multiprocessing import Process, Queue
from collections import namedtuple
from pathlib import Path

from scripts_sum.morph_client import get_morphology
from scripts_sum.token import Token
from scripts_sum.utterance import Utterance

from sumdoc.client import Client as DocClient
from sumquery.client import Client as QueryClient
from sumannotate.client import Client as AnnotationClient
from summarkup.cli import generate_markup

#Request = namedtuple('Request', ['retranslation_config'])
Request = namedtuple('Request', ["query_id","doc_id","c"])

class RequestProcessor(Process):
    def __init__(self, request_queue, doc_port, query_port, annotation_port, morph_port, morph_path, output_dir):
        super(RequestProcessor, self).__init__()

        self.request_queue = request_queue
        self.output_dir = output_dir
        self.doc_client = DocClient(doc_port)
        self.query_client = QueryClient(query_port)
        self.annotation_client = AnnotationClient(annotation_port)
        self.morph_port = morph_port
        self.morph_path = morph_path

    def run(self):
        while not self.request_queue.empty():
            req = self.request_queue.get()
            self._process(req)
        return True

    def _get_markup_gen(self, qtype):
        if qtype['example_of']:
            return 'summarkup.generators.conceptv2.ConceptV2'
        elif qtype['morph']:
            return 'summarkup.generators.morphv1.MorphV1'
        elif qtype['conceptual']:
            return 'summarkup.generators.conceptv2.ConceptV2'
        elif qtype['lexical']:
            return 'summarkup.generators.lexicalv2.LexicalV2'
        else:
            return None

    def _get_markup_config(self, markup_gen, lang):
        if markup_gen == 'summarkup.generators.conceptv2.ConceptV2':
            return '/app/scripts/configs/concept.v2.{}.config.json'.format(lang)
        elif markup_gen == 'summarkup.generators.lexicalv2.LexicalV2':
            return '/app/scripts/configs/lexical.v2.{}.config.json'.format(lang)
        elif markup_gen == 'summarkup.generators.morphv1.MorphV1':
            return '/app/scripts/configs/morph.v1.{}.config.json'.format(lang)
        else:
            return None

    def _process(self, req):
        with open(os.path.join(self.output_dir, "retranslation","config","{}.{}.{}.config".format(req.query_id, req.doc_id, req.c)) ,"r") as retranslation_config_file:
            # config is a dictionary with keys ["query_id","doc_id", "component", "retranslation","translation_strategy"]
            retranslation_config = json.load(retranslation_config_file)

        translation_strategy = retranslation_config["translation_strategy"]
        if translation_strategy == "ape":
            with open(os.path.join(self.output_dir, "retranslation","mt","ape","{}.{}.{}.txt".format(req.query_id, req.doc_id, req.c)), "r") as translation_file:
                retranslations = [translation_file.readlines()[0].strip()]
        elif translation_strategy == "edinmt":
            with open(os.path.join(self.output_dir, "retranslation","mt","edinmt","{}.{}.{}.txt".format(req.query_id, req.doc_id, req.c)), "r") as translation_file:
                lines = [line.strip() for line in translation_file.readlines()]
                lines = [json.loads(line)["translation"] for line in lines]
                if "edi-nmt" in retranslation_config["mt"]: # use 5best
                    lines = lines[:5]
                else:
                    lines = [lines[0]]
                retranslations = lines
        else: # umd-nmt
            with open(os.path.join(self.output_dir, "retranslation","mt","umdnmt","{}.{}.{}.json").format(req.query_id, req.doc_id, req.c),"r") as translation_file:
                retranslations = [json.load(translation_file)["translation"]]
        
        query_id = req.query_id
        doc_id = req.doc_id
        c = int(req.c[-1])-1
        lang = self.doc_client.lang(doc_id)
        
        qtype = self.query_client.query_type(query_id, c)

        markup_gen = self._get_markup_gen(qtype)
        markup_config = self._get_markup_config(markup_gen, lang)
        
        ann_file = os.path.join(self.output_dir,'annotations', query_id,'{}.{}.c{}.pkl'.format(query_id,doc_id, c + 1))
        ann_file_retranslation = os.path.join(self.output_dir, "retranslation", "annotations", "{}.{}.c{}.pkl".format(query_id,doc_id, c + 1))
        if not os.path.isfile(ann_file_retranslation):
           
            with open(ann_file,"rb") as ann_fp:
                doc_orig = pickle.load(ann_fp)
            
            doc_retranslation = copy.deepcopy(doc_orig)

            # Prepare Utterances
            utt_id, mt = retranslation_config["utt_id"], retranslation_config["mt"]
            mts = ["edi-nmt" if i == 0 else "edi-nmt-{}".format(i+1) for i in range(5)] if translation_strategy == "edinmt"  and "edi-nmt" in mt else [mt]
            morphs = [get_morphology(line, self.morph_port, "EN", self.morph_path) for line in retranslations]
            new_utterances = [Utterance(line, Token.tokens_from_morphology(morph)) for line, morph in zip(retranslations,morphs)]
            
            utterance = doc_retranslation._utterances[utt_id] 
            utterance["translations"] = {mt_name:line for mt_name, line in zip(mts, new_utterances)}
            
            doc_retranslation._utterances = [utterance]
            doc_retranslation._annotations = {}
            doc_retranslation._token_annotations = {}
            
            # Prepare Annotations
            doc_retranslation_file = os.path.join(self.output_dir, "retranslation", "annotations", "{}.{}.c{}_retranslation.pkl".format(query_id, doc_id, c+1))
            with open(doc_retranslation_file, "wb") as retranslation_fp:
                pickle.dump(doc_retranslation, retranslation_fp)
            self.annotation_client.annotate_doc(query_id, doc_retranslation_file, c, Path(doc_retranslation_file))
            
            # change original annotation

            with open(doc_retranslation_file, "rb") as retranslation_fp:
                doc_retranslation = pickle.load(retranslation_fp)

            utterances = list(doc_orig._utterances)
            for mt_name in mts:
                #print(utterances[utt_id]["translations"].keys(), doc_retranslation._utterances[0]["translations"].keys())
                utterances[utt_id]["translations"][mt_name] = doc_retranslation._utterances[0]["translations"][mt_name]
            doc_orig._utterances = tuple(utterances)
            
            for ann in doc_orig._annotations:
                ann_name = ann.split(".")[0]
                if ann_name in mts:
                    if doc_orig._annotations[ann] is not None and doc_retranslation._annotations[ann] is not None:
                        doc_orig._annotations[ann]["annotation"][utt_id] = doc_retranslation._annotations[ann]["annotation"][0]

            with open(ann_file_retranslation, "wb") as ann_fp:
                pickle.dump(doc_orig, ann_fp)

            markup_file = os.path.join(self.output_dir, 'markup', query_id,'{}.{}.c{}.json'.format(query_id,doc_id,c+1))
        
            args_str = '{} {} {} --args {} --quiet'.format(markup_gen,Path(ann_file_retranslation),Path(markup_file), markup_config)
            generate_markup(args_str)
    

def main(args):
    request_queue = Queue()
    
    for retranslation_file in os.listdir(os.path.join(args.output_dir,"retranslation","config")):
        if retranslation_file.endswith(".config"):
            query_id, doc_id, c, _ = retranslation_file.split(".")
            request_queue.put(Request(query_id=query_id, doc_id=doc_id, c=c))

    processes = []
    for i in range(args.num_procs):
        p = RequestProcessor(request_queue, args.doc_port, args.query_port,
                             args.annotation_port, args.morph_port, args.morph_path, args.output_dir)
        p.start()
        processes.append(p)

    for p in processes:
        p.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_dir', default='/outputs', help='output dir')
    parser.add_argument('--doc_port', type=int, required=True, help='document server port')
    parser.add_argument('--query_port', type=int, required=True, help='query server port')
    parser.add_argument('--annotation_port', type=int, required=True, help='annotation server port')
    parser.add_argument('--morph_port', type=int, required=True, help='morphology server port')
    parser.add_argument('--morph_path', type=str, required=True, help='morphology jar path')
    parser.add_argument('--num_procs', type=int, default='32', help='number of workers to use')

    args = parser.parse_args()
    main(args)
