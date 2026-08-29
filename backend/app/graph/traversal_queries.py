"""Bounded-depth graph traversal over knowledge_edges via a recursive CTE.

Verification note: this project's sandbox has no PostgreSQL instance (no `psql`,
no way to `initdb` one), so unlike almost everything else in this project, this SQL
was never executed. The confidence level here is different from app/parsers/'s
tree-sitter queries, though, and worth spelling out: recursive CTEs (`WITH
RECURSIVE`) have been stable, standard PostgreSQL since version 8.4 (2009) with no
material syntax changes since, so this isn't "written from a possibly-stale
snapshot of a fast-moving library" the way the tree-sitter API was -- it's applying
long-settled, well-documented SQL. Still: run
`EXPLAIN (WITH RECURSIVE traversal ...)` (or just the query itself) against a real
repository's data before trusting the results, particularly the cycle-guard
(`NOT (next_id = ANY(path))`) on a repository that actually contains a circular
import chain, since that's exactly the case most likely to expose a mistake here.

Returns SQLAlchemy `text()` constructs + bind params, not results -- callers
`session.execute(query, params)` (or `await` it, for the async API session) and get
back rows themselves, which is what lets this module stay usable from either the
sync worker path or the async API path without duplicating the SQL.
"""

from typing import Literal
from uuid import UUID

from sqlalchemy import TextClause, text

Direction = Literal["out", "in", "both"]

_JOIN_CONDITIONS: dict[Direction, str] = {
    "out": "e.source_node_id = t.node_id",
    "in": "e.target_node_id = t.node_id",
    "both": "(e.source_node_id = t.node_id OR e.target_node_id = t.node_id)",
}

_NEXT_NODE_EXPRESSIONS: dict[Direction, str] = {
    "out": "e.target_node_id",
    "in": "e.source_node_id",
    "both": "CASE WHEN e.source_node_id = t.node_id THEN e.target_node_id ELSE e.source_node_id END",
}


def build_neighbors_query(
    *,
    edge_types: list[str] | None,
    direction: Direction,
) -> TextClause:
    """Bind params expected at execution time: start_id (uuid), max_depth (int),
    and edge_types (list[str], only referenced if edge_types was non-None here --
    still safe to always pass an empty list when it's None since the ANY() clause
    is simply omitted from the query text in that case)."""
    if direction not in _JOIN_CONDITIONS:
        raise ValueError(f"invalid direction: {direction!r}")

    join_condition = _JOIN_CONDITIONS[direction]
    next_node = _NEXT_NODE_EXPRESSIONS[direction]
    edge_type_filter = "AND e.edge_type = ANY(:edge_types)" if edge_types else ""

    return text(f"""
        WITH RECURSIVE traversal(node_id, depth, path) AS (
            SELECT :start_id::uuid, 0, ARRAY[:start_id::uuid]

            UNION ALL

            SELECT {next_node}, t.depth + 1, t.path || {next_node}
            FROM traversal t
            JOIN knowledge_edges e ON {join_condition}
            WHERE e.repository_id = :repository_id
              AND t.depth < :max_depth
              AND NOT ({next_node} = ANY(t.path))
              {edge_type_filter}
        )
        SELECT DISTINCT ON (node_id) node_id, depth
        FROM traversal
        WHERE depth > 0
        ORDER BY node_id, depth ASC
    """)


def neighbors_query_params(
    repository_id: UUID,
    start_node_id: UUID,
    *,
    max_depth: int,
    edge_types: list[str] | None,
) -> dict:
    return {
        "repository_id": str(repository_id),
        "start_id": str(start_node_id),
        "max_depth": max_depth,
        "edge_types": edge_types or [],
    }
