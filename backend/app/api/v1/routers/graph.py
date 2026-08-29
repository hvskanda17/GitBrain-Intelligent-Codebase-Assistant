from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import CurrentUser, get_graph_query_service, get_project_repo, get_repository_repo
from app.ingestion.dispatcher import CeleryIngestionDispatcher
from app.repositories.project_repository import ProjectRepository
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.graph import CircularDependencyResponse, KnowledgeEdgeRead, KnowledgeGraphResponse, KnowledgeNodeRead
from app.services.graph_query_service import GraphQueryService
from app.services.repository_service import RepositoryService

router = APIRouter(prefix="/repositories/{repository_id}/graph", tags=["graph"])


def _repository_service(
    repo_repo: Annotated[RepositoryRepository, Depends(get_repository_repo)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
) -> RepositoryService:
    return RepositoryService(repo_repo, project_repo, CeleryIngestionDispatcher())


async def _verify_access(
    repository_id: UUID, user: CurrentUser, service: Annotated[RepositoryService, Depends(_repository_service)]
) -> None:
    # Every route below needs the same ownership check the rest of the API already
    # enforces (RepositoryService.get_owned raises NotFoundError/PermissionDeniedError,
    # both mapped to proper responses by the global GitBrainError handler) --
    # centralized here instead of repeated in each handler.
    await service.get_owned(repository_id, user.id)


def _to_response(nodes, edges) -> KnowledgeGraphResponse:
    return KnowledgeGraphResponse(
        nodes=[
            KnowledgeNodeRead(id=n.id, node_type=n.node_type, label=n.label, metadata=n.node_metadata) for n in nodes
        ],
        edges=[
            KnowledgeEdgeRead(
                source_node_id=e.source_node_id, target_node_id=e.target_node_id, edge_type=e.edge_type, weight=e.weight
            )
            for e in edges
        ],
    )


@router.get(
    "/knowledge",
    response_model=KnowledgeGraphResponse,
    dependencies=[Depends(_verify_access)],
)
async def get_knowledge_graph(
    repository_id: UUID,
    graph: Annotated[GraphQueryService, Depends(get_graph_query_service)],
    node_type: str | None = None,
) -> KnowledgeGraphResponse:
    nodes, edges = await graph.get_subgraph(repository_id, node_type)
    return _to_response(nodes, edges)


@router.get(
    "/call-graph",
    response_model=KnowledgeGraphResponse,
    dependencies=[Depends(_verify_access)],
)
async def get_call_graph(
    repository_id: UUID,
    graph: Annotated[GraphQueryService, Depends(get_graph_query_service)],
    node_id: UUID = Query(..., description="knowledge_nodes.id of the function or method to center on"),
    direction: Literal["callers", "callees"] = "callees",
    depth: int = Query(default=2, ge=1, le=10),
) -> KnowledgeGraphResponse:
    nodes, edges = await graph.get_call_graph(repository_id, node_id, direction, depth)
    return _to_response(nodes, edges)


@router.get(
    "/dependencies",
    response_model=KnowledgeGraphResponse,
    dependencies=[Depends(_verify_access)],
)
async def get_dependencies(
    repository_id: UUID,
    graph: Annotated[GraphQueryService, Depends(get_graph_query_service)],
) -> KnowledgeGraphResponse:
    nodes, edges = await graph.get_dependencies(repository_id)
    return _to_response(nodes, edges)


@router.get(
    "/circular-dependencies",
    response_model=CircularDependencyResponse,
    dependencies=[Depends(_verify_access)],
)
async def get_circular_dependencies(
    repository_id: UUID,
    graph: Annotated[GraphQueryService, Depends(get_graph_query_service)],
) -> CircularDependencyResponse:
    cycles = await graph.get_circular_dependencies(repository_id)
    return CircularDependencyResponse(cycles=cycles)
