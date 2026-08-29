"""Cosine-similarity search over embeddings via pgvector's <=> operator. Requires
embeddings to actually exist for the repository -- unlike lexical_search.py and the
graph expansion, this one genuinely has nothing to return if no embedding API key
was ever configured, which is expected and handled by the caller
(app/services/retrieval_service.py) rather than treated as an error.

Verification note: same status as lexical_search.py and app/graph/
traversal_queries.py -- no Postgres in this sandbox, never executed. pgvector's
`<=>` operator has been stable since the extension's 2021 release.
"""

from sqlalchemy import TextClause, text


def build_vector_search_query() -> TextClause:
    return text("""
        SELECT source_id, source_type, 1 - (embedding <=> :query_vector::vector) AS similarity
        FROM embeddings
        WHERE repository_id = :repository_id
        ORDER BY embedding <=> :query_vector::vector
        LIMIT :limit
    """)


def vector_search_params(repository_id, query_vector: list[float], limit: int) -> dict:
    # pgvector's text input format is "[v1,v2,...]" with no whitespace -- Python's
    # default str(list) includes ", " between elements, which risks a parsing
    # mismatch, so this is built explicitly rather than relying on repr().
    vector_literal = "[" + ",".join(str(v) for v in query_vector) + "]"
    return {"repository_id": str(repository_id), "query_vector": vector_literal, "limit": limit}
