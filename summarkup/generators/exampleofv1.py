import numpy as np
import re
import string
from summarkup.utils import make_relevant_header, detokenize

punc = set(string.punctuation)
translations = ["edi-nmt", "umd-nmt", "umd-smt"]
annotators = [
    ["exact_match", ["sentence", "sum"]], 
    ["stem_match", ["sentence", "sum"]],
    ["glove42Bsim.content_semcons", ["sentence", "mean"]],
    ["glove42Bsim.content_semcons", ["sentence", "max"]],
    ["glove6Bsim.content_semcons", ["sentence", "mean"]],
    ["glove6Bsim.content_semcons", ["sentence", "max"]],
]            

class ExampleOfV1:

    def __call__(self, doc, budget=100, make_header=True):
        query = doc.annotations["QUERY"]
#        print(query)
#        print([x.word for x in query.content.tokens])

        best_translations = []
        scores = []
        for i in range(len(doc.utterances)):
               
            trans, trans_score = self.get_best_translation(doc.annotations, i)
            best_translations.append(trans)
            scores.append(trans_score)

        scores = np.stack(scores).T
        ranks = np.argsort(scores, axis=1)[:,::-1]
        merged_ranks = merge_rankings(ranks)

        markup_lines = []
        if make_header:
            header, header_size = make_relevant_header(query)
            markup_lines.append(header)
            size = header_size
        else:
            size = 0

        ranked_utterances = []
        for i in merged_ranks:
            best_trans = best_translations[i]
            utt = doc.utterances[i]["translations"][best_trans]
            num_words = len(
                detokenize(" ".join([x.word for x in utt.tokens])).split())
            size += num_words
            ranked_utterances.append({"index": i, "utt": utt, 
                                      "trans": best_trans})
            if size > budget:
                break            
        ranked_utterances.sort(key=lambda x: x["index"])
        size = header_size if make_header else 0

        exact_matches = set()
        close_matches = set()
        t2s = {}
        for x in ranked_utterances:
            tokens = x["utt"].tokens
            x_matches = doc.annotations[x["trans"] + ".exact_match"]["annotation"][x['index']]["word"]["matches"]
            c_matches = doc.annotations[x["trans"] + ".glove42Bsim.content_semcons"]["annotation"][x['index']]["word"]["sims"]
            for t, m, sim in zip(tokens, x_matches, c_matches):
                if np.sum(m) > 0:
                    exact_matches.add(t)
                if t.pos in ["NN", "VB"]:
                    t2s[t] = sim[0]
        sim_toks = sorted(t2s, key=lambda x: t2s[x], reverse=True)
        for t in sim_toks:
            if t in exact_matches: continue
            close_matches.add(t)
            if len(close_matches) > 5:
                break

        for x in ranked_utterances:
            line, wc = self.make_utterance_markup(x["utt"], budget - size,
                                                  exact_matches, close_matches)
            size += wc
            markup_lines.append(line)
            if size >= budget:
                 break

        return "\n".join(markup_lines)

    def get_best_translation(self, annotations, utt_index):
        t2s = {}
        t2m = {}
        
        for trans in translations:
            scores = []
            for ann_name, ann_keys in annotators:
                tr_ann_name = "{}.{}".format(trans, ann_name)
                x = annotations[tr_ann_name]["annotation"][utt_index]
                for k in ann_keys:
                    x = x[k]
                scores.append(x)
            scores = np.array(scores)
            X = scores.copy()
            X[scores != scores] = -1
            mean = X.mean()
            scores[scores != scores] = float("-inf")
            t2m[trans] = mean
            t2s[trans] = scores
        srt_trans = sorted(translations, key=lambda x: t2m[x], reverse=True)
        best_trans = srt_trans[0]
        return best_trans, scores
        

    def make_utterance_markup(self, utt, budget, exact_matches, close_matches):

        line_items = []
        for token in utt.tokens:
            if token in exact_matches:
                line_items.append(
                    '<span_class="[EXACTREL]">' + token.word + '</span>')
            elif token in close_matches:
                line_items.append( 
                   '<span_class="[REL]">' + token.word + '</span>')
            else:
                line_items.append(token.word)

        line = detokenize(" ".join(line_items))
        wc = len(line.split())
        if wc > budget:
            wc = budget
            line = " ".join(line.split()[:wc]) + "..."

        line = re.sub(r"span_class", "span class", line)
        line = re.sub(r"\[EXACTREL\]", "rel_exact_match", line)
        line = re.sub(r"\[REL\]", "relevant", line)
        return "<p>{}</p>\n".format(line), wc

def merge_rankings(rankings):
    """
    Aggregates multiple rankings to produce a single overall ranking of a list
    of items.

    rankings: a list of lists, each sublist is a ranking (0 is best)

    For example, let's say we are ranking 4 items A, B, C, and D and we have
    4 sets of a rankings. The input rankings might look like this:
    rankings = [[0, 1, 2, 3],
                [3, 0, 1, 2],
                [3, 1, 0, 2],
                [3, 1, 2, 0]]

    where: 
    [0, 1, 2, 3] expresses a preference for A, B, C, D with A the best;
    [3, 0, 1, 2] expresses a preference for B, C, D, A with B the best;
    [3, 1, 0, 2] expresses a preference for C, B, D, A with C the best;
    [3, 1, 2, 0] expresses a preference for D, B, C, A with D the best.

    agg_ranking = borda_count_rank_merge(rankings) 

    print(agg_ranking)
    [3 0 1 2] which corresponds to the ranking B, C, D, A  
    """

    # trivial case
    if len(rankings) == 1: return rankings[0]

    all_points = [0 for _ in rankings[0]]
    max_rank = len(rankings[0]) - 1
    for ranking in rankings:
        for i, rank in enumerate(ranking):
            points = max_rank - rank
            all_points[i] += points
    order = np.argsort(all_points)[::-1].tolist()
    agg_rank = [order.index(i) for i in range(max_rank + 1)]
    return agg_rank
