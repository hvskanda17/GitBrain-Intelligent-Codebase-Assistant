from uuid import UUID

from app.db.sync_session import SyncSessionLocal
from app.services.analysis_service import AnalysisService
from workers.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, queue="ingestion")
def parse_repository_files(self, repository_id: str) -> str:
    with SyncSessionLocal() as session:
        try:
            AnalysisService(session).parse_repository_files(UUID(repository_id))
            session.commit()
        except Exception as exc:
            session.rollback()
            raise self.retry(exc=exc)
    return repository_id


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, queue="ingestion")
def build_repository_call_graph(self, repository_id: str) -> str:
    with SyncSessionLocal() as session:
        try:
            AnalysisService(session).build_repository_call_graph(UUID(repository_id))
            session.commit()
        except Exception as exc:
            session.rollback()
            raise self.retry(exc=exc)
    return repository_id
