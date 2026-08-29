from uuid import UUID

from sqlalchemy import select

from app.db.models.repository import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def list_for_owner(self, owner_id: UUID) -> list[Project]:
        result = await self.session.execute(
            select(Project).where(Project.owner_id == owner_id).order_by(Project.created_at.desc())
        )
        return list(result.scalars().all())
