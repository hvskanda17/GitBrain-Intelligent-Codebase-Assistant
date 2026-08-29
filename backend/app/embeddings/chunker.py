"""Builds the text that actually gets embedded, from data Phase 5 already extracted
-- signature and docstring, not the function body (Phase 5 stores metadata, not
source text, so pulling a body snippet would mean re-reading the file from disk;
signature+docstring carries most of a function's searchable meaning anyway, and
skipping the re-read keeps this pure and testable). Deliberately DB- and
API-agnostic -- app/services/embedding_service.py fetches the real rows and calls
this.
"""

from dataclasses import dataclass

# ~1500 tokens at a 4-chars/token heuristic (see app/retrieval/context_builder.py
# for the same heuristic used at the retrieval end) -- comfortably under
# text-embedding-3-small's 8191-token input limit even before accounting for the
# fact most chunks here are far shorter than that anyway.
MAX_CHUNK_CHARS = 6000


@dataclass(frozen=True)
class ChunkInput:
    source_type: str  # "function" | "class"
    source_id: str
    chunk_text: str


def chunk_function(
    source_id: str,
    name: str,
    qualified_name: str | None,
    signature: str | None,
    docstring: str | None,
    is_async: bool,
) -> ChunkInput:
    header = f"{'async ' if is_async else ''}function {qualified_name or name}"
    parts = [header]
    if signature:
        parts.append(signature.strip())
    if docstring:
        parts.append(docstring.strip())
    text = "\n\n".join(p for p in parts if p)
    return ChunkInput(source_type="function", source_id=source_id, chunk_text=text[:MAX_CHUNK_CHARS])


def chunk_class(
    source_id: str,
    name: str,
    qualified_name: str | None,
    docstring: str | None,
    method_names: list[str],
) -> ChunkInput:
    parts = [f"class {qualified_name or name}"]
    if docstring:
        parts.append(docstring.strip())
    if method_names:
        parts.append("methods: " + ", ".join(method_names))
    text = "\n\n".join(p for p in parts if p)
    return ChunkInput(source_type="class", source_id=source_id, chunk_text=text[:MAX_CHUNK_CHARS])
