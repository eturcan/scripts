import numpy as np


def merge_scores(scores, return_points=False):
    """ 
    Converts lists of scores to list of ranks and then merges them using
    the borda count method. Result is an ordered list of items based on their
    merged rankings implied by their scores.
    """

    if any([len(scores[0]) != len(scores_i) for scores_i in scores]):
        raise ValueError("Inconsistent number of scores.")
    ranks = [convert_score_to_rank(scores_i) for scores_i in scores]
    points = [convert_rank_to_point(ranks_i) for ranks_i in ranks]
    total_points = np.array(points).sum(axis=0)
    result = list(np.argsort(total_points)[::-1])
    
    if return_points:
        return result, points
    else:
        return result


def convert_score_to_rank(scores):
    
    R = {}
    I = np.argsort(scores)
    for r, i in enumerate(I):
        if r > 0:
            if scores[i] == scores[I[r-1]]:
                r = R[I[r-1]]

        R[i] = r

    vals2canon = {x: y for y, x in enumerate(sorted(set(R.values())))}

    return [vals2canon[R[i]] for i in range(len(R))]

def convert_rank_to_point(ranks):
    return [sum([ri >= rj for rj in ranks]) for ri in ranks]

    return list(ranks)
    print(ranks_rev_un)
    
    ranks_un = []
    for i, r in enumerate(ranks_rev_un):
#        if i + 1 < len(scores):
#            rp1 = ranks_rev_un[i+1]
#            if scores[r] == scores[rp1]:
#                ranks_rev_un[i+1] = r
        ranks_un = [r] + ranks_un

    return ranks_un
    


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
