from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import CurrentUser, get_project_repo, get_repository_repo, require_role
from app.db.models.user import User, UserRole
from app.ingestion.dispatcher import CeleryIngestionDispatcher
from app.repositories.project_repository import ProjectRepository
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryCreateResponse,
    RepositoryRead,
    RepositoryStatus,
)
from app.services.repository_service import RepositoryService

router = APIRouter(prefix="/repositories", tags=["repositories"])

# viewers can read and chat but not trigger ingestion, reindex, or deletion
CanIngest = Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))]


def _service(
    repo_repo: Annotated[RepositoryRepository, Depends(get_repository_repo)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
) -> RepositoryService:
    return RepositoryService(repo_repo, project_repo, CeleryIngestionDispatcher())


@router.post("", response_model=RepositoryCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_repository(
    data: RepositoryCreate,
    user: CanIngest,
    service: Annotated[RepositoryService, Depends(_service)],
) -> RepositoryCreateResponse:
    repository = await service.create(user.id, data)
    return RepositoryCreateResponse(repository_id=repository.id, status=repository.status.value)


@router.get("", response_model=list[RepositoryRead])
async def list_repositories(
    user: CurrentUser,
    service: Annotated[RepositoryService, Depends(_service)],
    project_id: UUID,
) -> list[RepositoryRead]:
    repositories = await service.list_for_project(project_id, user.id)
    return [RepositoryRead.model_validate(r) for r in repositories]


@router.get("/{repository_id}", response_model=RepositoryRead)
async def get_repository(
    repository_id: UUID,
    user: CurrentUser,
    service: Annotated[RepositoryService, Depends(_service)],
) -> RepositoryRead:
    repository = await service.get_owned(repository_id, user.id)
    return RepositoryRead.model_validate(repository)


@router.get("/{repository_id}/status", response_model=RepositoryStatus)
async def get_repository_status(
    repository_id: UUID,
    user: CurrentUser,
    service: Annotated[RepositoryService, Depends(_service)],
) -> RepositoryStatus:
    repository = await service.get_owned(repository_id, user.id)
    return RepositoryStatus(status=repository.status.value)


@router.post("/{repository_id}/reindex", response_model=RepositoryStatus, status_code=status.HTTP_202_ACCEPTED)
async def reindex_repository(
    repository_id: UUID,
    user: CanIngest,
    service: Annotated[RepositoryService, Depends(_service)],
    full: bool = False,
) -> RepositoryStatus:
    repository = await service.reindex(repository_id, user.id, full=full)
    return RepositoryStatus(status=repository.status.value)


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repository_id: UUID,
    user: CanIngest,
    service: Annotated[RepositoryService, Depends(_service)],
) -> None:
    await service.delete(repository_id, user.id)
