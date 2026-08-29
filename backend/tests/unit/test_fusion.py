from app.retrieval.fusion import reciprocal_rank_fusion


def test_item_appearing_in_multiple_lists_outranks_single_appearance():
    lexical = ["a", "b", "c"]
    vector = ["b", "d", "e"]
    fused = reciprocal_rank_fusion([lexical, vector])
    fused_order = [item_id for item_id, _ in fused]
    # "b" is rank 2 in both lists; "a" is rank 1 in only one. Appearing in both
    # should let "b" win despite never being ranked first anywhere.
    assert fused_order[0] == "b"


def test_top_rank_in_a_single_list_still_matters():
    fused = reciprocal_rank_fusion([["a", "b", "c"]])
    scores = dict(fused)
    assert scores["a"] > scores["b"] > scores["c"]


def test_empty_lists_produce_empty_result():
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


def test_single_list_preserves_relative_order():
    fused = reciprocal_rank_fusion([["x", "y", "z"]])
    assert [item_id for item_id, _ in fused] == ["x", "y", "z"]


def test_three_way_agreement_outscores_two_way():
    lexical = ["a", "b"]
    vector = ["a", "c"]
    graph = ["a", "d"]
    fused = reciprocal_rank_fusion([lexical, vector, graph])
    scores = dict(fused)
    assert scores["a"] > scores["b"]
    assert scores["a"] > scores["c"]
    assert scores["a"] > scores["d"]


def test_scores_are_deterministic_and_symmetric_in_list_order():
    # The fusion score for an item shouldn't depend on which position its
    # containing list occupies in the outer list.
    fused_1 = reciprocal_rank_fusion([["a", "b"], ["c", "a"]])
    fused_2 = reciprocal_rank_fusion([["c", "a"], ["a", "b"]])
    assert dict(fused_1) == dict(fused_2)
