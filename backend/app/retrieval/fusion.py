"""Reciprocal Rank Fusion: combines multiple ranked lists into one fused ranking
without needing their scores to be on comparable scales -- exactly the problem
hybrid retrieval has (a BM25 score, a cosine similarity, and a graph-hop distance
aren't directly comparable, so averaging or summing them directly would be
meaningless). This is the actual "hybrid" in hybrid RAG: app/retrieval/
lexical_search.py, vector_search.py, and a graph expansion each produce their own
ranked list of chunk ids, and this is what merges them into one.
"""

# The standard damping constant from the original RRF paper (Cormack, Clarke &
# Buettcher, 2009) -- large enough that rank 1 vs rank 2 in a single list doesn't
# completely dominate the fused result, small enough that rank still matters more
# than merely appearing in more lists.
DEFAULT_K = 60


def reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = DEFAULT_K) -> list[tuple[str, float]]:
    """Each inner list is item ids in rank order, best first. Returns (id, score)
    pairs sorted by fused score descending. An id that appears in more than one
    list accumulates a higher score than one that only appears once -- agreement
    across retrieval methods is itself a signal."""
    scores: dict[str, float] = {}
    for ranked_list in ranked_lists:
        for rank, item_id in enumerate(ranked_list, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
