from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import CurrentUser, get_project_repo
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    user: CurrentUser,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
) -> ProjectRead:
    project = await ProjectService(project_repo).create(user.id, data)
    return ProjectRead.model_validate(project)


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    user: CurrentUser,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
) -> list[ProjectRead]:
    projects = await ProjectService(project_repo).list_for_owner(user.id)
    return [ProjectRead.model_validate(p) for p in projects]
