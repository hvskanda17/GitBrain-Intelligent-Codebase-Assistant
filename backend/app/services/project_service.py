from uuid import UUID

from app.db.models.repository import Project
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate


class ProjectService:
    def __init__(self, project_repo: ProjectRepository) -> None:
        self.project_repo = project_repo

    async def create(self, owner_id: UUID, data: ProjectCreate) -> Project:
        project = Project(name=data.name, owner_id=owner_id)
        return await self.project_repo.add(project)

    async def list_for_owner(self, owner_id: UUID) -> list[Project]:
        return await self.project_repo.list_for_owner(owner_id)
