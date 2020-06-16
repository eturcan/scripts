import argparse
import os
import json
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
    def __init__(self, request_queue, doc_port, query_port, annotation_port, output_dir):
        super(RequestProcessor, self).__init__()

        init = timer()
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
        if markup_gen == 'summarkup.generators.conceptv2.ConceptV2':
            return '/app/scripts/configs/concept.v2.{}.config.demo.json'.format(lang)
        elif markup_gen == 'summarkup.generators.lexicalv2.LexicalV2':
            return '/app/scripts/configs/lexical.v2.{}.config.demo.json'.format(lang)
        elif markup_gen == 'summarkup.generators.morphv1.MorphV1':
            return '/app/scripts/configs/morph.v1.{}.config.demo.json'.format(lang)
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

            ann_file = os.path.join(self.output_dir, 'annotations', req.query_id,
                                    '{}.{}.c{}.pkl'.format(req.query_id,
                                                           req.doc_id, c+1))

            if not os.path.exists(ann_file):
                self.annotation_client.annotate_material(req.query_id,
                                                         req.doc_id, c,
                                                         Path(ann_file))

            markup_file = os.path.join(self.output_dir, 'markup', req.query_id,
                                       '{}.{}.c{}.json'.format(req.query_id,
                                                               req.doc_id,
                                                               c+1))

            if not os.path.exists(markup_file):
                #command = 'generate_markup {} {} {} --args {} --quiet'.format(markup_gen,
                #                                                              Path(ann_file),
                #                                                              Path(markup_file),
                #                                                              markup_config)
                #os.system(command)
                args_str = '{} {} {} --args {} --quiet'.format(markup_gen,
                                                               Path(ann_file),
                                                               Path(markup_file),
                                                               markup_config)
                generate_markup(args_str)

        print('done processing {}: {}'.format(req.doc_id, timer()-start))


def main(args):
    start = timer()
    request_queue = Queue()
    query_client = QueryClient(args.query_port)
    #psq_client = PSQClient(args.psq_port)

    with open(os.path.join(args.input_dir, args.clir_output_file)) as fin:
        clir_output = json.load(fin)

    query_id = args.clir_output_file.replace('.json', '')
    query_str = clir_output['query']['raw']
    query_client.add_query_str(query_id, query_str)
    #psq_dict = clir_output['query']['psq']

    #if 'idf' in clir_output:
    #    idf_dict = clir_output['idf']
    #else:
    #    idf_dict = {k: 1.0 for k in psq_dict.keys()}

    #psq_client.add_psq(query_id, psq_dict, idf_dict)

    print('Num relevant docs: {}'.format(len(clir_output['results'])))
    for result in clir_output['results']:
        request_queue.put(Request(query_id=query_id, doc_id=result['id'],
                                  score=result['score']))

    processes = []
    for i in range(args.num_procs):
        p = RequestProcessor(request_queue, args.doc_port, args.query_port,
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
    parser.add_argument('--output_dir', default='/outputs', help='output dir')
    parser.add_argument('--doc_port', type=int, required=True, help='document server port')
    parser.add_argument('--query_port', type=int, required=True, help='query server port')
    parser.add_argument('--annotation_port', type=int, required=True, help='annotation server port')
    parser.add_argument('--psq_port', type=int, required=True, help='psq server port')
    parser.add_argument('--num_procs', type=int, default='32', help='number of workers to use')

    args = parser.parse_args()
    main(args)
