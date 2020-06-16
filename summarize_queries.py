import argparse
import os
from multiprocessing import Process, Queue
from collections import namedtuple
from pathlib import Path

from sumdoc.client import Client as DocClient
from sumquery.client import Client as QueryClient
from sumannotate.client import Client as AnnotationClient
from summarkup.cli import generate_markup

Request = namedtuple('Request', ['query_id', 'doc_id', 'score'])

class RequestProcessor(Process):
    def __init__(self, request_queue, doc_port, query_port, annotation_port, output_dir):
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
        if markup_gen == 'summarkup.generators.conceptv2.ConceptV2':
            return '/app/scripts/configs/concept.v2.{}.config.json'.format(lang)
        elif markup_gen == 'summarkup.generators.lexicalv2.LexicalV2':
            return '/app/scripts/configs/lexical.v2.{}.config.json'.format(lang)
        elif markup_gen == 'summarkup.generators.morphv1.MorphV1':
            return '/app/scripts/configs/morph.v1.{}.config.json'.format(lang)
        else:
            return None

    def _process(self, req):
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
                args_str = '{} {} {} --args {} --quiet'.format(markup_gen,
                                                               Path(ann_file),
                                                               Path(markup_file),
                                                               markup_config)
                generate_markup(args_str)


def main(args):
    request_queue = Queue()

    for query in args.queries:
        clir_file = os.path.join(args.clir_dir, '{}.tsv'.format(query))
        with open(clir_file) as fin:
            for line in fin:
                doc_id, rel, score = line.strip().split('\t')
                if rel == 'N':
                    continue
                request_queue.put(Request(query_id=query, doc_id=doc_id,
                                          score=score))

    processes = []
    for i in range(args.num_procs):
        p = RequestProcessor(request_queue, args.doc_port, args.query_port,
                             args.annotation_port, args.output_dir)
        processes.append(p)
        p.start()

    for p in processes:
        p.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--queries', nargs='+', required=True, help='query ids to summarize')
    parser.add_argument('--clir_dir', default='/clir', help='clir, output dir')
    parser.add_argument('--output_dir', default='/outputs', help='output dir')
    parser.add_argument('--doc_port', type=int, required=True, help='document server port')
    parser.add_argument('--query_port', type=int, required=True, help='query server port')
    parser.add_argument('--annotation_port', type=int, required=True, help='annotation server port')
    parser.add_argument('--num_procs', type=int, default='32', help='number of workers to use')

    args = parser.parse_args()
    main(args)
