"""Async, API-side hybrid retrieval. Reading (this) is a normal request-path
concern using the API's regular async session, same split as
app/services/graph_query_service.py vs. the sync worker services -- only building
things (ingestion, parsing, the knowledge graph, embeddings) happens in workers.

The actual "hybrid" happens here: lexical search, vector search, and a knowledge-
graph expansion each produce their own ranked list of (function/class) ids, fused
by app/retrieval/fusion.py's Reciprocal Rank Fusion, then loaded and packed into a
token budget by app/retrieval/context_builder.py. Vector search is skipped
entirely (not an error) when no embedding client is configured -- see
EmbeddingService's docstring for why that's a deliberate degrade-gracefully
choice rather than a failure; lexical and graph search alone still answer a
meaningful slice of questions.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.code_entities import Class, Function
from app.db.models.filesystem import File
from app.db.models.graph import KnowledgeNode
from app.embeddings.embedding_client import EmbeddingClient
from app.graph.traversal_queries import build_neighbors_query, neighbors_query_params
from app.retrieval.context_builder import RetrievedChunk, build_context
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.lexical_search import build_lexical_search_query, lexical_search_params
from app.retrieval.vector_search import build_vector_search_query, vector_search_params


class RetrievalService:
    def __init__(self, session: AsyncSession, embedding_client: EmbeddingClient | None) -> None:
        self.session = session
        self.embedding_client = embedding_client

    async def retrieve(self, repository_id: UUID, question: str, k: int = 40, token_budget: int = 8000) -> list[RetrievedChunk]:
        lexical_ids = await self._lexical_search(repository_id, question, k)
        vector_ids = await self._vector_search(repository_id, question, k)
        graph_ids = await self._graph_expand(repository_id, lexical_ids[:5] + vector_ids[:5])

        fused = reciprocal_rank_fusion([lexical_ids, vector_ids, graph_ids])
        top_ids = [source_id for source_id, _score in fused[:k]]

        chunks = await self._load_chunks(repository_id, top_ids)
        return build_context(chunks, token_budget=token_budget)

    async def _lexical_search(self, repository_id: UUID, question: str, limit: int) -> list[str]:
        query = build_lexical_search_query()
        params = lexical_search_params(repository_id, question, limit)
        rows = (await self.session.execute(query, params)).all()
        return [str(row.source_id) for row in rows]

    async def _vector_search(self, repository_id: UUID, question: str, limit: int) -> list[str]:
        if self.embedding_client is None:
            return []
        query_vector = self.embedding_client.embed([question])[0]
        query = build_vector_search_query()
        params = vector_search_params(repository_id, query_vector, limit)
        rows = (await self.session.execute(query, params)).all()
        return [str(row.source_id) for row in rows]

    async def _graph_expand(self, repository_id: UUID, seed_source_ids: list[str]) -> list[str]:
        """One-hop expansion (callers + callees) from the top lexical/vector
        candidates, via the knowledge graph -- this is the "structural" signal in
        hybrid retrieval, surfacing related code the other two methods wouldn't
        find on wording alone."""
        if not seed_source_ids:
            return []

        seed_uuids = {UUID(sid) for sid in seed_source_ids}
        seed_nodes = (
            await self.session.scalars(
                select(KnowledgeNode).where(
                    KnowledgeNode.repository_id == repository_id, KnowledgeNode.ref_id.in_(seed_uuids)
                )
            )
        ).all()

        expanded: list[str] = []
        for node in seed_nodes:
            query = build_neighbors_query(edge_types=["calls"], direction="both")
            params = neighbors_query_params(repository_id, node.id, max_depth=1, edge_types=["calls"])
            rows = (await self.session.execute(query, params)).all()
            neighbor_node_ids = [row.node_id for row in rows]
            if neighbor_node_ids:
                neighbor_nodes = (
                    await self.session.scalars(
                        select(KnowledgeNode).where(KnowledgeNode.id.in_(neighbor_node_ids))
                    )
                ).all()
                expanded.extend(str(n.ref_id) for n in neighbor_nodes if n.ref_id)
        return expanded

    async def _load_chunks(self, repository_id: UUID, source_ids: list[str]) -> list[RetrievedChunk]:
        if not source_ids:
            return []
        ids = [UUID(sid) for sid in source_ids]

        # Functions and classes are fetched separately (their id spaces don't
        # overlap, but a single query across two unrelated tables needs a UNION,
        # which is more complexity than this needs) and then re-assembled in the
        # caller's fused rank order, not query order. The repository_id filter
        # here is defense in depth, not the primary scoping -- every id in
        # source_ids already came from a repository-scoped query, but a bug
        # upstream (fusion, graph expansion) shouldn't be able to leak another
        # repository's function into a result set just by returning its id.
        function_rows = (
            await self.session.execute(
                select(Function, File.path)
                .join(File, Function.file_id == File.id)
                .where(Function.id.in_(ids), File.repository_id == repository_id)
            )
        ).all()
        class_rows = (
            await self.session.execute(
                select(Class, File.path)
                .join(File, Class.file_id == File.id)
                .where(Class.id.in_(ids), File.repository_id == repository_id)
            )
        ).all()

        chunks_by_id: dict[str, RetrievedChunk] = {}
        for fn, file_path in function_rows:
            text = "\n\n".join(p for p in [fn.signature, fn.docstring] if p) or fn.name
            chunks_by_id[str(fn.id)] = RetrievedChunk(
                source_type="function",
                source_id=str(fn.id),
                label=f"function {fn.qualified_name or fn.name}",
                file_path=file_path,
                chunk_text=text,
                score=0.0,
            )
        for cls, file_path in class_rows:
            text = cls.docstring or cls.name
            chunks_by_id[str(cls.id)] = RetrievedChunk(
                source_type="class",
                source_id=str(cls.id),
                label=f"class {cls.qualified_name or cls.name}",
                file_path=file_path,
                chunk_text=text,
                score=0.0,
            )

        # Re-order to match the caller's fused rank, not whatever order the two
        # SELECTs happened to return.
        return [chunks_by_id[sid] for sid in source_ids if sid in chunks_by_id]
