from uuid import UUID

from celery import chain

from app.db.sync_session import SyncSessionLocal
from app.services.ingestion_service import IngestionService
from workers.celery_app import celery_app
from workers.tasks.embeddings import generate_embeddings
from workers.tasks.graph import build_knowledge_graph
from workers.tasks.parsing import build_repository_call_graph, parse_repository_files


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, queue="ingestion")
def clone_repository(self, repository_id: str) -> str:
    with SyncSessionLocal() as session:
        try:
            IngestionService(session).clone(UUID(repository_id))
            session.commit()
        except Exception as exc:
            session.rollback()
            raise self.retry(exc=exc)
    return repository_id


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, queue="ingestion")
def detect_and_walk_files(self, repository_id: str, full: bool = False) -> str:
    with SyncSessionLocal() as session:
        try:
            IngestionService(session).detect_and_walk(UUID(repository_id), force_full=full)
            session.commit()
        except Exception as exc:
            session.rollback()
            raise self.retry(exc=exc)
    return repository_id


def build_ingestion_chain(repository_id: str, *, full: bool = False):
    """clone -> detect/walk -> parse every file -> resolve the cross-file call
    graph -> resolve imports and materialize the knowledge graph -> embed and mark
    ready. This is the full pipeline from the Phase 1 design -- the first phase
    where a repository actually reaches status=ready, whether or not an embedding
    API key is configured (see generate_embeddings' docstring for the graceful
    skip). Real per-file parsing parallelism (a Celery group/chord fanning
    parse_repository_files out per-file rather than one task looping over all of a
    repository's files) remains a reasonable future optimization, deliberately not
    attempted here -- see backend/README.md's Phase 5 section for why."""
    return chain(
        clone_repository.s(repository_id),
        detect_and_walk_files.s(full=full),
        parse_repository_files.s(),
        build_repository_call_graph.s(),
        build_knowledge_graph.s(),
        generate_embeddings.s(),
    )

