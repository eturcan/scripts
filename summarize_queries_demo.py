import argparse
import os
import json
import pickle
from multiprocessing import Process, Queue
from collections import namedtuple
from pathlib import Path
from timeit import default_timer as timer

from sumdoc.client import Client as DocClient
from sumquery.client import Client as QueryClient
from sumannotate.client import Client as AnnotationClient
from sumpsq.client import PSQClient
from summarkup.cli import generate_markup

Request = namedtuple('Request', ['query_id', 'doc_id', 'score'])

class RequestProcessor(Process):
    def __init__(self, request_queue, doc_port, query_port, 
                 annotation_port, output_dir):
        super(RequestProcessor, self).__init__()

        self.request_queue = request_queue
        self.output_dir = output_dir
        self.doc_client = DocClient(doc_port)
        self.query_client = QueryClient(query_port)
        self.annotation_client = AnnotationClient(annotation_port)

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
        prefix = Path("/", "app", "scripts", "configs")
        if markup_gen == 'summarkup.generators.conceptv2.ConceptV2':
            return prefix / f'concept.v2.{lang}.config.demo.json'
        elif markup_gen == 'summarkup.generators.lexicalv2.LexicalV2':
            return prefix / f'lexical.v2.{lang}.config.demo.json'
        elif markup_gen == 'summarkup.generators.morphv1.MorphV1':
            return prefix / f'morph.v1.{lang}.config.demo.json'
        else:
            return None

    def _process(self, req):
        start = timer()
        nc = self.query_client.num_components(req.query_id)
        lang = self.doc_client.lang(req.doc_id)

        for c in range(nc):
            qtype = self.query_client.query_type(req.query_id, c)
            markup_gen = self._get_markup_gen(qtype)
            markup_config = self._get_markup_config(markup_gen, lang)

            ann_file = (
                self.output_dir / 'annotations' / req.query_id /
                f'{req.query_id}.{req.doc_id}.c{c+1}.pkl'
            )

            if not ann_file.exists():
                self.annotation_client.annotate_material(
                    req.query_id,
                    req.doc_id, c,
                    ann_file)

            markup_file = (
                self.output_dir / 'markup' / req.query_id /
                f'{req.query_id}.{req.doc_id}.c{c+1}.json'
            )

            if not markup_file.exists():
                args_str = " ".join([
                    markup_gen, str(ann_file), str(markup_file),
                    '--args', str(markup_config), '--quiet',
                    "--evidence"
                ])
                generate_markup(args_str)

        print('done processing {}: {}'.format(req.doc_id, timer()-start))

def main(args):
    start = timer()

    summary_queue = Queue()

    query_client = QueryClient(args.query_port)
    #psq_client = PSQClient(args.psq_port)

    with open(os.path.join(args.input_dir, args.clir_output_file)) as fin:
        clir_output = json.load(fin)

    query_id = args.clir_output_file.replace('.json', '')
    query_str = clir_output['query']['raw']
    query_client.add_query_str(query_id, query_str)
    

    print('Num relevant docs: {}'.format(len(clir_output['results'])))
    for result in clir_output['results']:
        summary_queue.put(Request(query_id=query_id, doc_id=result['id'],
                                  score=result['score']))

    processes = []
    for i in range(args.num_procs):
        p = RequestProcessor(summary_queue,
                             args.doc_port, args.query_port,
                             args.annotation_port, args.output_dir)
        processes.append(p)
        p.start()

    print('Summarizer setup time: {}'.format(timer()-start))

    for p in processes:
        p.join()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--clir_output_file', required=True, help='query ids to summarize')
    parser.add_argument('--input_dir', default='/outputs/clir_output/', help='output dir')
    parser.add_argument('--output_dir', default=Path('/outputs'), 
                        type=Path,
                        help='output dir')
    parser.add_argument('--doc_port', type=int, required=True, help='document server port')
    parser.add_argument('--query_port', type=int, required=True, help='query server port')
    parser.add_argument('--annotation_port', type=int, required=True, help='annotation server port')
    parser.add_argument('--psq_port', type=int, required=True, help='psq server port')
    parser.add_argument('--num_procs', type=int, default='32', help='number of workers to use')

    args = parser.parse_args()
    main(args)
