from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDeniedError, TokenError
from app.core.security import decode_token
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.embeddings.embedding_client import EmbeddingClient, OpenAIEmbeddingClient
from app.repositories.project_repository import ProjectRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.user_repository import UserRepository
from app.services.graph_query_service import GraphQueryService
from app.services.retrieval_service import RetrievalService

# auto_error=False so a missing token raises our own TokenError (and its JSON error
# envelope) instead of FastAPI's default plain-text 403.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if token is None:
        raise TokenError("missing bearer token")
    try:
        payload = decode_token(token, expected_type="access")
    except InvalidTokenError as exc:
        raise TokenError("access token is invalid or expired") from exc

    user = await UserRepository(db).get(UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise TokenError("token no longer maps to an active user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed: UserRole):
    """Router-level RBAC gate. Usage: Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))."""

    async def _check(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise PermissionDeniedError(f"role '{user.role.value}' cannot perform this action")
        return user

    return _check


async def get_project_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> ProjectRepository:
    return ProjectRepository(db)


async def get_repository_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> RepositoryRepository:
    return RepositoryRepository(db)


async def get_user_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> UserRepository:
    return UserRepository(db)


async def get_graph_query_service(db: Annotated[AsyncSession, Depends(get_db)]) -> GraphQueryService:
    return GraphQueryService(db)


def _get_embedding_client() -> EmbeddingClient | None:
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.EMBEDDING_API_KEY:
        return None
    return OpenAIEmbeddingClient(
        api_key=settings.EMBEDDING_API_KEY,
        model=settings.EMBEDDING_MODEL,
        dimensions=settings.EMBEDDING_DIMENSIONS,
        base_url=settings.EMBEDDING_API_BASE_URL,
    )


def get_llm_client() -> "LLMClient | None":
    from app.core.config import get_settings
    from app.llm.llm_client import LLMClient, OpenAILLMClient, MockLLMClient
    from app.core.exceptions import ConfigurationError

    settings = get_settings()
    
    if settings.LLM_PROVIDER == "mock":
        return MockLLMClient()
    
    if settings.LLM_PROVIDER == "openai":
        if not settings.LLM_API_KEY:
            return None
        return OpenAILLMClient(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_API_BASE_URL,
        )

    raise ConfigurationError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")


async def get_retrieval_service(db: Annotated[AsyncSession, Depends(get_db)]) -> RetrievalService:
    return RetrievalService(db, _get_embedding_client())


async def get_chat_service(db: Annotated[AsyncSession, Depends(get_db)]) -> "ChatService":
    from app.services.chat_service import ChatService
    from app.repositories.chat_repository import ChatSessionRepository, ChatMessageRepository
    
    return ChatService(
        chat_session_repo=ChatSessionRepository(db),
        chat_message_repo=ChatMessageRepository(db),
        repo_repo=RepositoryRepository(db),
        project_repo=ProjectRepository(db),
    )


async def get_chat_orchestrator(
    chat_service: Annotated["ChatService", Depends(get_chat_service)],
    retrieval_service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> "ChatOrchestrator":
    from app.services.chat_orchestrator import ChatOrchestrator
    return ChatOrchestrator(
        chat_service=chat_service,
        retrieval_service=retrieval_service,
        llm_client=get_llm_client(),
    )
