import argparse
import os
import re
import pickle
import json
import string
import time
import sentencepiece as spm
from multiprocessing import Process, Queue
from collections import namedtuple, Counter, defaultdict
from pathlib import Path
from itertools import product
from nltk.corpus import stopwords
import numpy as np

from scripts_sum.morph_client import get_morphology
from scripts_sum.token import Token
from scripts_sum.utterance import Utterance
from scripts_sum.query_utils import parse_query

from sumdoc.client import Client as DocClient
from sumpsq.client import PSQClient
from sumquery.client import Client as QueryClient
from summarkup.cli import generate_markup

Request = namedtuple('Request', ['query_id','doc_id','c','f1_label','f1_score'])

class RequestProcessor(Process):
    def __init__(self, request_queue, doc_port, psq_port, output_dir, sp, stop_words, doc_strategy, sent_strategy, translation_strategy, f1_threshold=2.23454577):
        super(RequestProcessor, self).__init__()

        self.request_queue = request_queue
        self.output_dir = output_dir
        self.doc_client = DocClient(doc_port)
        self.psq_client = PSQClient(psq_port)
        self.sp = sp
        self.doc_strategy = doc_strategy
        self.sent_strategy = sent_strategy
        self.translation_strategy = translation_strategy
        self.stop_words = stop_words
        self.f1_threshold = f1_threshold

    def run(self):
        while not self.request_queue.empty():
            req = self.request_queue.get()
            self._process(req)
        return True

    def _process(self, req):
        query_id = req.query_id
        doc_id = req.doc_id
        c = req.c
        f1_label = req.f1_label
        f1_score = req.f1_score

        # load markup and annotations
        with open(os.path.join(self.output_dir, "markup", query_id, "{}.{}.{}.json".format(query_id, doc_id, c) ) ,"r") as markup_file:
            markup_data = json.load(markup_file)
        with open(os.path.join(self.output_dir, "annotations", query_id, "{}.{}.{}.pkl".format(query_id, doc_id, c)), "rb") as ann_file:
            ann_data = pickle.load(ann_file)
        
        # get relevant information
        query_str = parse_query(markup_data["query_string"])[0]["query"]
        doc_type = markup_data["meta"]["mode"]
        utt_ids = markup_data["meta"]["utterance_ids"]
        mts = markup_data["meta"]["translation"]
        src = [ann_data._utterances[ui]["source"]._text for ui,mt in zip(utt_ids, mts)]
        translations = [ann_data._utterances[ui]["translations"][mt]._text for ui, mt in zip(utt_ids, mts)]

        psq = self.psq_client.get_psq(query_id)["psq"]
        psq_matches = self.get_psq_matches(query_str, psq, src)

        nbest_matches = None
        if self.sp is not None:
            nbest_path = str(self.doc_client.path(doc_id)["translations"]["umd-nmt"]) + ".nbest-words"
        
            query_bpe = self.sp[doc_type].EncodeAsPieces(query_str.lower())
            nbest_matches = self.get_nbest_matches(query_bpe, nbest_path, utt_ids)
        
        query = ann_data.annotations["QUERY"]
         
        if self.doc_selection(query, ann_data, utt_ids, mts, translations, nbest_matches, psq_matches, f1_label, f1_score):
            best_nbest_match = self.get_best_nbest_match(nbest_matches)
            best_psq_match = self.get_best_psq_match(psq_matches, query_str)
            
            sent_match = self.sent_selection(query_str, ann_data, best_nbest_match, best_psq_match)

            # given sum_id fill in other information
            sum_id = sent_match["sum_id"]
            sent_match["utt_id"] = utt_ids[sum_id]
            sent_match["src"] = src[sum_id]
            sent_match["mt"] = mts[sum_id]
            sent_match["translation"] = translations[sum_id]

            ape_no_match = True
            translation_strategy = None
            
            if "ape" in self.translation_strategy:
                # try to use ape if possible
                if sent_match["src_word"] is not None:
                    translation_strategy = "ape"
                    with open(os.path.join(self.output_dir,"retranslation","src","ape","{}.{}.{}.txt".format(query_id, doc_id, c)),"w") as sf:
                        json.dump(sent_match, sf)
                    ape_no_match = False
                elif "_" not in self.translation_strategy: # if ape is not possible and no fallback
                    return
            
            if ape_no_match:
                if "edinmt" in self.translation_strategy or ("split" in self.translation_strategy and "edi-nmt" in sent_match["mt"]):
                    translation_strategy = "edinmt"
                    doc_type_dir = "audio" if doc_type == "speech" else doc_type
                    with open(os.path.join(self.output_dir, "retranslation","src", "edinmt", doc_type_dir, "{}.{}.{}.txt".format(query_id, doc_id, c)), "w") as sf:
                        sf.write("{}\t{}\n".format(sent_match["src"], sent_match["tgt_word"]))
                elif "umdnmt" in self.translation_strategy or ("split" in self.translation_strategy and "umd-nmt" in sent_match["mt"]): 
                    translation_strategy = "umdnmt"
                    with open(os.path.join(self.output_dir, "retranslation","src", "umdnmt", "{}.{}.{}.json".format(query_id, doc_id, c)), "w") as sf:
                        json.dump({"text":sent_match["src"], "query":sent_match["tgt_word"]},sf)
            
            sent_match["translation_strategy"] = translation_strategy
            with open(os.path.join(self.output_dir, "retranslation", "config", "{}.{}.{}.config".format(query_id, doc_id, c)), "w") as match_fp:
                json.dump(sent_match, match_fp)

    def doc_selection(self, query, ann_data, utt_ids, mts, translations, nbest_matches=None, psq_matches=None, f1_label=None, f1_score=None):
        
        # helper function
        def is_invalid_word(w):
            if w.lower() in self.stop_words:
                return True
            if all([c in string.punctuation for c in w]):
                return True
            return False
        
        if self.doc_strategy == "regressor":
            # feature: ir score + ir label + query_rel score and must be >= f1_threshold
            queryrel_score = max([ann_data.annotations["queryrel"]["annotation"][utt_id]["query_content"] for utt_id in utt_ids])
            score = queryrel_score + f1_score + f1_label
            if score < self.f1_threshold:
                return False
             
        if self.doc_strategy == "f1" and f1_label == 0:
            return False
        if self.doc_strategy == "nbest" and len(nbest_matches) ==  0:
            return False
        if self.doc_strategy == "psq" and len(psq_matches) == 0:
            return False
        # only translate documents that do not contain query words
        contains_query_words = False
        for utt_id, mt, trans in zip(utt_ids, mts,translations):
            
            exact_ann = mt + ".exact_match"
            stem_ann = mt + ".stem_match"

            # load exact_match and stem_match ,but ignore words that are stopwords
            tokens_is_stop = [is_invalid_word(token.word) for token in ann_data._utterances[utt_id]["translations"][mt].tokens]
            exact_match = [em for i,em in enumerate(ann_data.annotations[exact_ann]["annotation"][utt_id]["word"]["matches"]) if not tokens_is_stop[i]]
            stem_match = [sm for i,sm in enumerate(ann_data.annotations[stem_ann]["annotation"][utt_id]["word"]["matches"]) if not tokens_is_stop[i]]

            # this assumes the same filter strategy for annotation
            n = len([tok.word for tok in query.content.tokens if not is_invalid_word(tok.word)])

            # if there is any exact or stem matches for all words, then return true
            consecutive_match = [False for _ in range(len(exact_match))]
            for i,(em, sm) in enumerate(zip(exact_match, stem_match)):
                # turn consecutive_match for 0th as True
                if len(exact_match) - i >= n: 
                    consecutive_match[i] = em[0] or sm[0]
                if i >= n-1:
                    for j in range(1,n):
                        consecutive_match[i-j] &= em[j] or sm[j]

            if any(consecutive_match):
                contains_query_words = True
                break
        return not contains_query_words

    def sent_selection(self, query_str, ann_data, nbest_match=None, psq_match=None):
        # returns sentence to retranslate and corresponding idx with constraits information if possible
        
        # by default the first sentence
        sum_id = 0
        src_word = None
        tgt_word = query_str
        src_word_idx = None

        if self.sent_strategy == "nbest":
            if nbest_match:
                sum_id = nbest_match

                if psq_match and psq_match[0] == nbest_match:
                    _, src_word, tgt_word, src_word_idx = psq_match
        
        if self.sent_strategy == "psq":
            if psq_match:
                sum_id, src_word, tgt_word, src_word_idx = psq_match
        
        # base case still check for psq
        if psq_match and psq_match[0] == 0:
            _, src_word, tgt_word, src_word_idx = psq_match

        return {"sum_id": sum_id, "src_word": src_word, "tgt_word":tgt_word, "src_word_idx":src_word_idx}
    
    def get_nbest_matches(self, query_bpe, nbest_file, utt_ids ):
        matches = []
        utt_ids_set = set(utt_ids)
        with open(nbest_file, "r") as f:
            nbest_file = [json.loads(line.strip())["nbest_words"] for i,line in enumerate(f) if i in utt_ids_set]
        for i, nbest in enumerate(nbest_file):
            for j in range(len(nbest) - len(query_bpe) + 1):
                match = []
                for k, query in enumerate(query_bpe):
                    if query in nbest[j+k]:
                        match.append( (j,k, nbest[j+k]) )
                if len(match) == len(query_bpe):
                    matches.append((i))
        return matches
    
    def get_best_nbest_match(self, nbest_matches):
        if not nbest_matches:
            return None
        counter = Counter(nbest_matches)
        idx,_ = counter.most_common(1)[0]
        return idx

    
    def get_psq_matches(self, query_str, psq, src):
        # Returns matches in the format of tuple (utt_id, list(src_id), list(word), score)
        query_str = [query for query in query_str.lower().split() if query in psq]
        matches = []
        for i, s in enumerate(src):
            cur_match = {query:[] for query in query_str}
            for j,word in enumerate(s.split()):
                for query in query_str:
                    if psq[query] is not None and word in psq[query]:
                        cur_match[query].append( (j, word, psq[query][word] ) )
            # generate possible candidates, need all words in query str to be present
            vals = list(cur_match.values())
            if all(vals):
                possible_candidates = list(product(*vals))
                for candidate in possible_candidates:
                    # need all src indices to be unique
                    src_idx = [can[0] for can in candidate]
                    if len(set(src_idx)) == len(src_idx):
                        # combine tuples into one ( utt_id, [src_idx], [words], score )
                        match = ( i, tuple(src_idx), tuple([can[1] for can in candidate]), sum(can[2] for can in candidate)  )
                        matches.append(match)
        return matches
    
    def get_best_psq_match(self, psq_matches, query_str):
        if not psq_matches:
            return None
        # Prefer psq_match that is consecutive. If not prefer score then distance

        distance_candidates = defaultdict(set) # sort by distance
        for candidate in psq_matches:
            sorted_indices = sorted(candidate[1])
            distance = sum([sorted_indices[i+1]-sorted_indices[i] for i in range(len(sorted_indices)-1)])
            distance_candidates[distance].add(candidate)
        
        consecutive_dist = len(query_str.split()) -1
        if consecutive_dist in distance_candidates:
            best_candidate = sorted(distance_candidates[consecutive_dist], key= lambda x:x[-1], reverse=True )[0]
        else:
            # sort by score, then distance. To do so expand dict to list with scores and distance
            expanded_candidates = []
            for dis in distance_candidates:
                for candidate in distance_candidates[dis]:
                    expanded_candidates.append( candidate + (dis,)  )
            best_candidate = sorted(expanded_candidates, key= lambda x: (x[-2], -x[-1]), reverse=True )[0]
        
        # Greedily combine

        # sort the three lists by src_idx
        src_idx, src_words, tgt_words = zip(*sorted(zip(best_candidate[1], best_candidate[2], query_str.split())))

        comb_idx, comb_src_words, comb_tgt_words = [], [], []
        cur_id = [src_idx[0]]
        cur_src_words = [src_words[0]]
        cur_tgt_words = set([tgt_words[0]])
        
        for i, sw, tw in zip(src_idx[1:], src_words[1:], tgt_words[1:]):
            if cur_id[-1]+1 == i: # is adjacent
                cur_id.append(i)
                cur_src_words.append(sw)
                cur_tgt_words.add(tw)
            else:
                # combine everything
                comb_idx.append(cur_id[0])
                comb_src_words.append(" ".join(cur_src_words))
                comb_tgt_words.append(" ".join([qs for qs in query_str.split() if qs in cur_tgt_words])) # tgt order needs to be in English
                # reset
                cur_id = [i]
                cur_src_words = [sw]
                cur_tgt_words = set([tw])

        # dont forget the last
        comb_idx.append(cur_id[0])
        comb_src_words.append(" ".join(cur_src_words))
        comb_tgt_words.append(" ".join([qs for qs in query_str.split() if qs in cur_tgt_words]))

        # remove singletons that are stopwords
        is_stopwords = [w in self.stop_words for w in comb_tgt_words]
        comb_idx = [w for i,w in enumerate(comb_idx) if not is_stopwords[i]]
        comb_src_words = [w for i,w in enumerate(comb_src_words) if not is_stopwords[i]]
        comb_tgt_words = [w for i,w in enumerate(comb_tgt_words) if not is_stopwords[i]]
        
        return (best_candidate[0], comb_src_words, comb_tgt_words, comb_idx)

def main(args):
    sp = None
    if args.doc_strategy == "nbest" or args.sent_strategy == "nbest":
        sp_text = spm.SentencePieceProcessor()
        sp_text.load(os.path.join(args.spm_path,"text.spm"))
        sp_speech = spm.SentencePieceProcessor()
        sp_speech.load(os.path.join(args.spm_path,"speech.spm"))
        sp = {"text":sp_text, "speech":sp_speech}

    stop_words = stopwords.words("english")

    request_queue = Queue()
    
    # change f1 dir into a dict
    f1_cutoff = dict()
    for query_file in os.listdir(args.f1_dir):
        if re.match("query[0-9]+.tsv", query_file):
            for line in open(os.path.join(args.f1_dir, query_file)):
                line = line.strip().split("\t")
                f1_label = 1.0 if line[1] == "Y" else 0.0
                f1_score = float(line[2])
                f1_cutoff[(query_file[:-4],line[0])] = (f1_label, f1_score)

    for query in os.listdir(os.path.join(args.output_dir, "markup")):
        for markup_file in os.listdir(os.path.join(args.output_dir,"markup",query)):
            query_id, doc_id, c, _ = markup_file.split(".")
            f1_label, f1_score = f1_cutoff[(query_id,doc_id)]
            request_queue.put(Request(query_id=query_id, doc_id=doc_id, c = c, f1_label=f1_label, f1_score=f1_score))

    processes = []
    for i in range(args.num_procs):
        p = RequestProcessor(request_queue, args.doc_port,
                             args.psq_port, args.output_dir, sp, stop_words,
                             args.doc_strategy, args.sent_strategy, args.translation_strategy)
        p.start()
        processes.append(p)

    for p in processes:
        p.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--f1_dir', default='/experiment/UMD-CLIR-workECDir-f1')
    parser.add_argument('--output_dir', default='/outputs', help='output dir')
    parser.add_argument('--doc_port', type=int, required=True, help='document server port')
    parser.add_argument('--psq_port', type=int, required=True, help='psq server port')
    parser.add_argument('--num_procs', type=int, default='32', help='number of workers to use')
    parser.add_argument('--spm_path', type=str, required=True, help='SentencePiece Model to be loaded')
    
    parser.add_argument('--doc_strategy', type=str, default='none', choices=['none','psq','nbest','f1','regressor'])
    parser.add_argument('--sent_strategy', type=str, default='psq', choices=['none','psq','nbest'])
    parser.add_argument('--translation_strategy', type=str, default='ape_edinmt', choices=['edinmt','umdnmt','split', 'ape','ape_edinmt','ape_umdnmt','ape_split'])
    
    args = parser.parse_args()
    main(args)
