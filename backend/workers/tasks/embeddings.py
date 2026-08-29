from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.repository import IndexingStatus, Repository
from app.db.sync_session import SyncSessionLocal
from app.embeddings.embedding_client import OpenAIEmbeddingClient
from app.services.embedding_service import EmbeddingService
from workers.celery_app import celery_app

logger = get_logger(__name__)
settings = get_settings()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, queue="ingestion")
def generate_embeddings(self, repository_id: str) -> str:
    """The pipeline's last stage: embed every function/class (if an embedding API
    key is configured -- see EmbeddingService.generate_embeddings for the
    deliberate graceful skip if not), then mark the repository ready regardless.
    A repository without embeddings still has working lexical and graph search;
    it just doesn't have vector search until embeddings are added later (a
    reindex, once EMBEDDING_API_KEY is set, would pick them up)."""
    client = (
        OpenAIEmbeddingClient(
            api_key=settings.EMBEDDING_API_KEY,
            model=settings.EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIMENSIONS,
            base_url=settings.EMBEDDING_API_BASE_URL,
        )
        if settings.EMBEDDING_API_KEY
        else None
    )

    with SyncSessionLocal() as session:
        try:
            count = EmbeddingService(session, client).generate_embeddings(UUID(repository_id))
            repository = session.get(Repository, UUID(repository_id))
            if repository is not None:
                repository.status = IndexingStatus.READY
            session.commit()
            logger.info("embeddings.done repository_id=%s embedded=%d", repository_id, count)
        except Exception as exc:
            session.rollback()
            raise self.retry(exc=exc)
    return repository_id
