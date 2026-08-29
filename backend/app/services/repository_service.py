from uuid import UUID

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.db.models.repository import IndexingStatus, Repository
from app.ingestion.dispatcher import IngestionDispatcher
from app.repositories.project_repository import ProjectRepository
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.repository import RepositoryCreate


class RepositoryService:
    def __init__(
        self,
        repo_repo: RepositoryRepository,
        project_repo: ProjectRepository,
        dispatcher: IngestionDispatcher,
    ) -> None:
        self.repo_repo = repo_repo
        self.project_repo = project_repo
        self.dispatcher = dispatcher

    async def create(self, owner_id: UUID, data: RepositoryCreate) -> Repository:
        project = await self.project_repo.get(data.project_id)
        if project is None:
            raise NotFoundError(f"no project {data.project_id}")
        if project.owner_id != owner_id:
            raise PermissionDeniedError("you do not own this project")

        repository = Repository(
            project_id=data.project_id,
            remote_url=data.remote_url,
            default_branch=data.branch or "main",
        )
        repository = await self.repo_repo.add(repository)
        await self.dispatcher.dispatch(repository.id)
        return repository

    async def get_owned(self, repository_id: UUID, owner_id: UUID) -> Repository:
        repository = await self.repo_repo.get(repository_id)
        if repository is None:
            raise NotFoundError(f"no repository {repository_id}")
        project = await self.project_repo.get(repository.project_id)
        if project is None or project.owner_id != owner_id:
            raise PermissionDeniedError("you do not have access to this repository")
        return repository

    async def list_for_project(self, project_id: UUID, owner_id: UUID) -> list[Repository]:
        project = await self.project_repo.get(project_id)
        if project is None:
            raise NotFoundError(f"no project {project_id}")
        if project.owner_id != owner_id:
            raise PermissionDeniedError("you do not own this project")
        return await self.repo_repo.list_for_project(project_id)

    async def reindex(self, repository_id: UUID, owner_id: UUID, *, full: bool) -> Repository:
        repository = await self.get_owned(repository_id, owner_id)
        repository.status = IndexingStatus.PENDING
        await self.repo_repo.add(repository)
        await self.dispatcher.dispatch(repository.id, full=full)
        return repository

    async def delete(self, repository_id: UUID, owner_id: UUID) -> None:
        repository = await self.get_owned(repository_id, owner_id)
        await self.repo_repo.delete(repository)
