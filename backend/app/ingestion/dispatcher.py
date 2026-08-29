from typing import Protocol
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


class IngestionDispatcher(Protocol):
    """Port that RepositoryService calls after a repository row is created or a
    reindex is requested. Phase 4 supplies a CeleryIngestionDispatcher that enqueues
    the real clone -> parse -> graph -> embed task chain; nothing above this
    interface (service, router, schemas) changes when that lands."""

    async def dispatch(self, repository_id: UUID, *, full: bool = False) -> None: ...


class NoOpIngestionDispatcher:
    """Kept for tests and as a reference for what the interface requires -- the API
    itself now wires CeleryIngestionDispatcher (see repositories.py's _service()),
    since Phase 4's pipeline exists."""

    async def dispatch(self, repository_id: UUID, *, full: bool = False) -> None:
        logger.info(
            "ingestion.dispatch.noop repository_id=%s full=%s",
            repository_id,
            full,
        )


class CeleryIngestionDispatcher:
    """Real implementation. Enqueues the Phase 4 clone -> detect/walk chain; Phase 5
    onward appends more stages to the same chain (see
    workers/tasks/ingestion.py:build_ingestion_chain) without this class changing."""

    async def dispatch(self, repository_id: UUID, *, full: bool = False) -> None:
        from workers.tasks.ingestion import build_ingestion_chain

        build_ingestion_chain(str(repository_id), full=full).apply_async()
