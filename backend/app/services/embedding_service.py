"""Sync service used by Celery worker tasks (see workers/tasks/embeddings.py), same
reasoning as the rest of app/services/ for why it's sync.

Takes an EmbeddingClient by constructor injection so the parts of this that are
genuinely this project's own logic -- graceful skip when no client is configured,
and batching -- can be tested without a real API key or a real database (see
tests/unit/test_embedding_service.py). The DB-fetching in _build_chunks can't be
exercised the same way without a real SQLAlchemy session, same limitation as the
persist methods in AnalysisService/KnowledgeGraphService.
"""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.code_entities import Class, Function, Method
from app.db.models.embeddings import Embedding
from app.db.models.filesystem import File
from app.embeddings.chunker import ChunkInput, chunk_class, chunk_function
from app.embeddings.embedding_client import EmbeddingClient

logger = get_logger(__name__)
settings = get_settings()


class EmbeddingService:
    def __init__(self, session: Session, client: EmbeddingClient | None) -> None:
        self.session = session
        self.client = client

    def generate_embeddings(self, repository_id: UUID) -> int:
        """Returns the number of chunks embedded. 0 (not an error) if no
        EmbeddingClient was configured -- see workers/tasks/embeddings.py for why
        that's a deliberate, graceful skip rather than a failure: lexical and
        graph search still work without vector embeddings, so a repository
        missing an API key shouldn't be stuck unable to reach `ready`."""
        if self.client is None:
            logger.info("embeddings.skipped repository_id=%s reason=no_client_configured", repository_id)
            return 0

        chunks = self._build_chunks(repository_id)
        if not chunks:
            return 0

        self.session.execute(delete(Embedding).where(Embedding.repository_id == repository_id))
        self.session.flush()

        embedded_count = 0
        for batch in _batched(chunks, settings.EMBEDDING_BATCH_SIZE):
            vectors = self.client.embed([c.chunk_text for c in batch])
            for chunk, vector in zip(batch, vectors, strict=True):
                self.session.add(
                    Embedding(
                        repository_id=repository_id,
                        source_type=chunk.source_type,
                        source_id=UUID(chunk.source_id),
                        chunk_text=chunk.chunk_text,
                        chunk_index=0,
                        embedding=vector,
                        model_name=settings.EMBEDDING_MODEL,
                    )
                )
                embedded_count += 1

        self.session.flush()
        return embedded_count

    def _build_chunks(self, repository_id: UUID) -> list[ChunkInput]:
        chunks: list[ChunkInput] = []

        functions = self.session.scalars(
            select(Function).join(File, Function.file_id == File.id).where(File.repository_id == repository_id)
        ).all()
        for fn in functions:
            chunks.append(
                chunk_function(
                    source_id=str(fn.id),
                    name=fn.name,
                    qualified_name=fn.qualified_name,
                    signature=fn.signature,
                    docstring=fn.docstring,
                    is_async=fn.is_async,
                )
            )

        classes_with_methods = self.session.execute(
            select(Class).join(File, Class.file_id == File.id).where(File.repository_id == repository_id)
        ).scalars().all()
        for cls in classes_with_methods:
            method_names = list(
                self.session.scalars(select(Method.name).where(Method.class_id == cls.id))
            )
            chunks.append(
                chunk_class(
                    source_id=str(cls.id),
                    name=cls.name,
                    qualified_name=cls.qualified_name,
                    docstring=cls.docstring,
                    method_names=method_names,
                )
            )

        return chunks


def _batched(items: list, batch_size: int):
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]
