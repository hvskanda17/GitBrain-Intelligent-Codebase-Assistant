"""Async, API-side graph reads. Building the graph (KnowledgeGraphService) is sync
and worker-only, per the rest of this project's sync-worker/async-api split; reading
it back out for the frontend is a normal request-path concern and uses the API's
regular async session like everything else in app/api/v1/routers/.
"""

from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.circular_dependency_detector import find_circular_dependencies
from app.db.models.graph import KnowledgeEdge, KnowledgeNode
from app.graph.traversal_queries import build_neighbors_query, neighbors_query_params


class GraphQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_subgraph(
        self, repository_id: UUID, node_type: str | None
    ) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:
        node_stmt = select(KnowledgeNode).where(KnowledgeNode.repository_id == repository_id)
        if node_type:
            node_stmt = node_stmt.where(KnowledgeNode.node_type == node_type)
        nodes = list((await self.session.scalars(node_stmt)).all())
        node_ids = {n.id for n in nodes}

        edge_stmt = select(KnowledgeEdge).where(KnowledgeEdge.repository_id == repository_id)
        all_edges = (await self.session.scalars(edge_stmt)).all()
        # Only edges where BOTH endpoints survived the node_type filter -- an edge
        # to a node the caller didn't ask to see would be a dangling reference in
        # the response.
        edges = [e for e in all_edges if e.source_node_id in node_ids and e.target_node_id in node_ids]
        return nodes, edges

    async def get_call_graph(
        self,
        repository_id: UUID,
        start_node_id: UUID,
        direction: Literal["callers", "callees"],
        depth: int,
    ) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:
        # "callers" = who calls this = walk incoming edges; "callees" = what this
        # calls = walk outgoing edges.
        internal_direction = "in" if direction == "callers" else "out"
        query = build_neighbors_query(edge_types=["calls"], direction=internal_direction)
        params = neighbors_query_params(repository_id, start_node_id, max_depth=depth, edge_types=["calls"])
        rows = (await self.session.execute(query, params)).all()

        reached_ids = {row.node_id for row in rows} | {start_node_id}
        nodes = list(
            (await self.session.scalars(select(KnowledgeNode).where(KnowledgeNode.id.in_(reached_ids)))).all()
        )
        edges = list(
            (
                await self.session.scalars(
                    select(KnowledgeEdge).where(
                        KnowledgeEdge.repository_id == repository_id,
                        KnowledgeEdge.edge_type == "calls",
                        KnowledgeEdge.source_node_id.in_(reached_ids),
                        KnowledgeEdge.target_node_id.in_(reached_ids),
                    )
                )
            ).all()
        )
        return nodes, edges

    async def get_dependencies(self, repository_id: UUID) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:
        edges = list(
            (
                await self.session.scalars(
                    select(KnowledgeEdge).where(
                        KnowledgeEdge.repository_id == repository_id, KnowledgeEdge.edge_type == "imports"
                    )
                )
            ).all()
        )
        node_ids = {e.source_node_id for e in edges} | {e.target_node_id for e in edges}
        nodes = list(
            (await self.session.scalars(select(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids)))).all()
        )
        return nodes, edges

    async def get_circular_dependencies(self, repository_id: UUID) -> list[list[str]]:
        # Reuses Phase 5's iterative-Tarjan's cycle detector against the
        # already-materialized "imports" edges, rather than a new recursive-CTE
        # cycle query -- proven code over new unverified SQL. See
        # backend/README.md's Phase 5 section for how that implementation was
        # verified.
        edges = list(
            (
                await self.session.scalars(
                    select(KnowledgeEdge).where(
                        KnowledgeEdge.repository_id == repository_id, KnowledgeEdge.edge_type == "imports"
                    )
                )
            ).all()
        )
        node_ids = {e.source_node_id for e in edges} | {e.target_node_id for e in edges}
        nodes = (await self.session.scalars(select(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids)))).all()
        label_by_id = {n.id: n.label for n in nodes}

        adjacency: dict[str, set[str]] = {}
        for e in edges:
            adjacency.setdefault(str(e.source_node_id), set()).add(str(e.target_node_id))

        cycles = find_circular_dependencies(adjacency)
        return [[label_by_id.get(UUID(node_id), node_id) for node_id in cycle] for cycle in cycles]
