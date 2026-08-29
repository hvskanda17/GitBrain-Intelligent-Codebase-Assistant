from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.deps import CurrentUser, get_project_repo, get_repository_repo, get_retrieval_service
from app.ingestion.dispatcher import CeleryIngestionDispatcher
from app.repositories.project_repository import ProjectRepository
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.search import RetrievedChunkRead, SemanticSearchRequest, SemanticSearchResponse
from app.services.repository_service import RepositoryService
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/repositories/{repository_id}/search", tags=["search"])


def _repository_service(
    repo_repo: Annotated[RepositoryRepository, Depends(get_repository_repo)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
) -> RepositoryService:
    return RepositoryService(repo_repo, project_repo, CeleryIngestionDispatcher())


async def _verify_access(
    repository_id: UUID, user: CurrentUser, service: Annotated[RepositoryService, Depends(_repository_service)]
) -> None:
    await service.get_owned(repository_id, user.id)


@router.post(
    "/semantic",
    response_model=SemanticSearchResponse,
    dependencies=[Depends(_verify_access)],
)
async def semantic_search(
    repository_id: UUID,
    data: SemanticSearchRequest,
    retrieval: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> SemanticSearchResponse:
    chunks = await retrieval.retrieve(repository_id, data.question, k=data.k, token_budget=data.token_budget)
    return SemanticSearchResponse(
        chunks=[
            RetrievedChunkRead(
                source_type=c.source_type,
                source_id=c.source_id,
                label=c.label,
                file_path=c.file_path,
                chunk_text=c.chunk_text,
            )
            for c in chunks
        ]
    )
