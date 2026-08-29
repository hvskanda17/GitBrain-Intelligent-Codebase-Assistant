from uuid import UUID

from app.db.sync_session import SyncSessionLocal
from app.services.knowledge_graph_service import KnowledgeGraphService
from workers.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, queue="ingestion")
def build_knowledge_graph(self, repository_id: str) -> str:
    with SyncSessionLocal() as session:
        try:
            service = KnowledgeGraphService(session)
            service.resolve_imports(UUID(repository_id))
            service.build_graph(UUID(repository_id))
            session.commit()
        except Exception as exc:
            session.rollback()
            raise self.retry(exc=exc)
    return repository_id
