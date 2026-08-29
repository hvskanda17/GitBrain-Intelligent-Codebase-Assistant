from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Workers use a plain sync engine/session. This is intentionally separate from
# app.db.session's async engine -- see the module docstring on IngestionService for
# why (Celery's execution model is fundamentally synchronous per task, and bridging
# into asyncio from inside a possibly-prefork'd worker process is a well-known
# source of subtle bugs around event-loop lifecycle and asyncpg's fork-unsafety).
_sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://")
sync_engine = create_engine(_sync_url, pool_pre_ping=True, echo=settings.DEBUG)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)
