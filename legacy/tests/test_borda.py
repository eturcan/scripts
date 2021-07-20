from scripts_sum.borda import merge_scores, convert_score_to_rank, convert_rank_to_point


def test_convert_scores_to_rank():

    inputsA = [0.5, -1, .999]
    outputsA = [1, 0, 2]
    assert outputsA == convert_score_to_rank(inputsA)

    inputsB = [0, 1, 0, 1, 1]
    outputsB = [0, 1, 0,1, 1]
    assert outputsB == convert_score_to_rank(inputsB)
    
    inputsC = [0,]
    outputsC = [0]
    assert outputsC == convert_score_to_rank(inputsC)
    
    inputsD = [4, 2, 5, 3, 2, 0]
    outputsD = [3, 1, 4, 2, 1, 0]
    assert outputsD == convert_score_to_rank(inputsD)

def test_convert_ranks_to_points():
    inputsA = [1, 0, 2]
    outputsA = [2, 1, 3]
    assert outputsA == convert_rank_to_point(inputsA)

    inputsB = [0, 1, 0, 1, 1]
    outputsB = [2, 5, 2, 5, 5]
    assert outputsB == convert_rank_to_point(inputsB)

    inputsC = [0,]
    outputsC = [1]
    assert outputsC == convert_rank_to_point(inputsC)
    
    inputsD = [3, 1, 4, 2, 1, 0]
    outputsD = [5, 3, 6, 4, 3, 1]
    assert outputsD == convert_rank_to_point(inputsD)

def test_merge_scores():

    scoresA = [
        [0.0, 1.0, 0.0, 1.0],
        [0.1, 0.3, 0.0, 0.4],
        [0.0, 0.0, 0.0, 0.0],
    ]
    outputA = [3,1,0,2]
    assert outputA == merge_scores(scoresA)
