from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db import models as _models  # noqa: F401  -- registers all ORM classes on Base.metadata
from app.db.base import Base
from app.db.session import get_db
from app.main import app

settings = get_settings()

# Point tests at a dedicated database so `pytest` never touches dev data. Create it
# once locally: docker compose exec postgres createdb -U gitbrain gitbrain_test
TEST_DATABASE_URL = settings.DATABASE_URL.rsplit("/", 1)[0] + "/gitbrain_test"

from sqlalchemy.pool import NullPool

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema() -> AsyncGenerator[None, None]:
    async with test_engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm;'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(loop_scope="session")
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
