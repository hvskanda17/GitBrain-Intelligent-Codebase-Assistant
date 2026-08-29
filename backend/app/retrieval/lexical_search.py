"""Lexical search over function/class name, signature, and docstring text, via
Postgres full-text search (tsvector/ts_rank_cd) -- not true BM25, but the same
purpose: catching exact identifier matches ("OrderService") that vector similarity
can miss on short, jargon-heavy queries. Deliberately queries the `functions`/
`classes` tables directly rather than `embeddings.chunk_text`, so lexical search
still works even when no embedding API key is configured and the embeddings table
is empty -- only vector_search.py actually needs embeddings to exist.

Verification note: same status as app/graph/traversal_queries.py -- no Postgres in
this sandbox, so never executed. Standard, long-stable Postgres full-text search
syntax, not a fast-moving API.
"""

from sqlalchemy import TextClause, text


def build_lexical_search_query() -> TextClause:
    return text("""
        WITH searchable AS (
            SELECT
                f.id AS source_id,
                'function' AS source_type,
                f.name || ' ' || COALESCE(f.qualified_name, '') || ' ' ||
                    COALESCE(f.signature, '') || ' ' || COALESCE(f.docstring, '') AS search_text
            FROM functions f
            JOIN files fl ON f.file_id = fl.id
            WHERE fl.repository_id = :repository_id

            UNION ALL

            SELECT
                c.id AS source_id,
                'class' AS source_type,
                c.name || ' ' || COALESCE(c.qualified_name, '') || ' ' || COALESCE(c.docstring, '') AS search_text
            FROM classes c
            JOIN files fl ON c.file_id = fl.id
            WHERE fl.repository_id = :repository_id
        )
        SELECT source_id, source_type,
               ts_rank_cd(to_tsvector('english', search_text), plainto_tsquery('english', :query)) AS rank
        FROM searchable
        WHERE to_tsvector('english', search_text) @@ plainto_tsquery('english', :query)
        ORDER BY rank DESC
        LIMIT :limit
    """)


def lexical_search_params(repository_id, query: str, limit: int) -> dict:
    return {"repository_id": str(repository_id), "query": query, "limit": limit}
