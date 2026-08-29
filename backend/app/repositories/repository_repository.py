from uuid import UUID

from sqlalchemy import select

from app.db.models.repository import IndexingStatus, Repository
from app.repositories.base import BaseRepository


class RepositoryRepository(BaseRepository[Repository]):
    model = Repository

    async def list_for_project(
        self, project_id: UUID, status: IndexingStatus | None = None
    ) -> list[Repository]:
        stmt = select(Repository).where(Repository.project_id == project_id)
        if status is not None:
            stmt = stmt.where(Repository.status == status)
        result = await self.session.execute(stmt.order_by(Repository.created_at.desc()))
        return list(result.scalars().all())
