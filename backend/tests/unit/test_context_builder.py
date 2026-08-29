from app.retrieval.context_builder import RetrievedChunk, build_context, estimate_tokens


def _chunk(source_id: str, text: str, score: float = 1.0) -> RetrievedChunk:
    return RetrievedChunk(
        source_type="function", source_id=source_id, label=source_id, file_path="app.py", chunk_text=text, score=score
    )


def test_estimate_tokens_uses_four_chars_per_token_heuristic():
    assert estimate_tokens("x" * 400) == 100
    assert estimate_tokens("") == 1  # never zero -- an empty string still costs something to include


def test_all_chunks_included_when_well_under_budget():
    chunks = [_chunk("a", "short text"), _chunk("b", "also short")]
    result = build_context(chunks, token_budget=1000)
    assert [c.source_id for c in result] == ["a", "b"]


def test_oversized_chunk_is_skipped_not_stopped_on():
    # budget=10 tokens (40 chars). chunk "a" alone exceeds it; chunk "b" is small
    # enough to fit on its own -- it should still be included, proving the builder
    # doesn't just stop at the first thing that doesn't fit.
    chunks = [_chunk("a", "x" * 400), _chunk("b", "small")]
    result = build_context(chunks, token_budget=10)
    assert [c.source_id for c in result] == ["b"]


def test_stops_accumulating_once_budget_is_exhausted():
    # Three chunks of 25 tokens each (100 chars), budget for exactly 2.
    chunks = [_chunk("a", "x" * 100), _chunk("b", "x" * 100), _chunk("c", "x" * 100)]
    result = build_context(chunks, token_budget=50)
    assert [c.source_id for c in result] == ["a", "b"]


def test_preserves_original_rank_order_among_selected_chunks():
    chunks = [_chunk("a", "x" * 40), _chunk("b", "x" * 40), _chunk("c", "x" * 40)]
    result = build_context(chunks, token_budget=100)
    assert [c.source_id for c in result] == ["a", "b", "c"]


def test_empty_input_returns_empty_output():
    assert build_context([], token_budget=1000) == []
