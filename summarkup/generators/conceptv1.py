import numpy as np
import re
import string

punc = set(string.punctuation)
translations = ["edi-nmt", "umd-nmt", "umd-smt"]

class ConceptV1:

    def __call__(self, doc, budget=100):
        query = list(doc.annotations.values())[0]["meta"]["query"]
        scores = []
        for trans in ["edi-nmt", "umd-nmt", "umd-smt"]:
            scores_t = []
            for x in doc.annotations[trans + '.exact_match']["annotation"]:
                scores_t.append(x['sentence']['sum'])
            scores.append(scores_t)
                                    
            scores_t = []
            for x in doc.annotations[trans + '.glove42Bsim.content_semcons']["annotation"]:
                scores_t.append(x['sentence']['mean'])
            scores.append(scores_t)

            scores_t = []
            for x in doc.annotations[trans + '.glove42Bsim.content_semcons']["annotation"]:
                scores_t.append(x['sentence']['max'])
            scores.append(scores_t)

        ranks = np.stack([np.argsort(x)[::-1] for x in scores])
        scores = np.array(scores)
#        print(ranks)
#        print(merge_rankings(ranks))

        size = 0
        ranked_utterances = []
        for i in merge_rankings(ranks):
            x = np.argsort([r.mean() for r in np.split(ranks[:,i], 3)])[0]
            best_trans = translations[x]
            utt = doc.utterances[i]["translations"][best_trans]
            num_words = len(utt.text.split(" "))
            size += num_words
#            print(size, i)
#            for t in translations:
#                print(t, doc.utterances[i]["translations"][t].text)
#                print(t, len(doc.utterances[i]["translations"][t].tokens))
 
#            print()
            ranked_utterances.append({"index": i, "utt": utt, 
                                      "trans": best_trans})
             
            if size > budget:
                break            

        ranked_utterances.sort(key=lambda x: x["index"])
        size = 0
        markup = "<h1> Sentences related to {}</h1>\n".format(query)

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
             tokens = x["utt"].tokens
             line = ''
             for token in tokens:
                 if token.word[0] not in punc:
                     size += 1
#                 print(size, token.word)
                 if token in exact_matches:
                     line += ' <span class="relevant exact">' + token.word \
                        + '</span>'
                 elif token in close_matches:
                     line += ' <span class="relevant">' + token.word \
                        + '</span>'
                 else:
                     line += " " + token.word
                 if size == budget: 
                     line += "..."
                     break
             markup += "<p>"+ line + "</p>\n"
             if size == budget: 
                 break
        markup = re.sub(r" `` ", ' "', markup)
        markup = re.sub(r" '' ", '" ', markup)
        markup = re.sub(r" ''", '" ', markup)
        markup = re.sub(r" ,", ',', markup)
        markup = re.sub(r" \.", '.', markup)
        markup = re.sub(r" n't", "n't", markup)
        markup = re.sub(r" 's", "'s", markup)
        markup = re.sub(r" % ", "% ", markup)
        markup = re.sub(r" \?", "?", markup)
        markup = re.sub(r" \!", "!", markup)
        markup = re.sub(r"-LRB- ", "(", markup)
        markup = re.sub(r" -RRB-", ")", markup)

        print(markup) 
        return markup 

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
