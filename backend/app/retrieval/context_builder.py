"""Fits ranked, retrieved chunks into a token budget for the eventual LLM call
(Phase 8). Pure and DB-agnostic -- app/services/retrieval_service.py loads the real
chunk rows in fused-rank order and calls this last.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedChunk:
    source_type: str  # "function" | "class"
    source_id: str
    label: str  # e.g. "function OrderService.create_order"
    file_path: str
    chunk_text: str
    score: float


def estimate_tokens(text: str) -> int:
    """~4 characters per token is a standard, widely-cited heuristic for English
    text and most programming languages -- close enough for budgeting without a
    real tokenizer (tiktoken) as a dependency. Systematically off by some margin is
    fine here; the consequence of a bad estimate is a context that's a bit smaller
    or larger than the target, not a correctness bug."""
    return max(1, len(text) // 4)


def build_context(chunks: list[RetrievedChunk], token_budget: int = 8000) -> list[RetrievedChunk]:
    """Greedily fills the budget in the given (already rank-ordered) order. A chunk
    that doesn't fit is skipped, not a stopping point -- a smaller, lower-ranked
    chunk later in the list may still fit in the remaining budget, and using that
    space beats leaving it empty. Selected chunks keep their original relative
    order (not resorted by size), so the highest-ranked material that did fit
    still reads first."""
    selected: list[RetrievedChunk] = []
    used = 0
    for chunk in chunks:
        cost = estimate_tokens(chunk.chunk_text)
        if used + cost > token_budget:
            continue
        selected.append(chunk)
        used += cost
    return selected
