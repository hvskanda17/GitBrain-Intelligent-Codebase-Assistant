from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.db.models.chat import ChatMessage, ChatSession
from app.repositories.chat_repository import ChatMessageRepository, ChatSessionRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.chat import ChatSessionCreate, ChatSessionUpdate


class ChatService:
    def __init__(
        self,
        chat_session_repo: ChatSessionRepository,
        chat_message_repo: ChatMessageRepository,
        repo_repo: RepositoryRepository,
        project_repo: ProjectRepository,
    ) -> None:
        self.chat_session_repo = chat_session_repo
        self.chat_message_repo = chat_message_repo
        self.repo_repo = repo_repo
        self.project_repo = project_repo

    async def _verify_repo_access(self, repository_id: UUID, user_id: UUID) -> None:
        repository = await self.repo_repo.get(repository_id)
        if repository is None:
            raise NotFoundError(f"no repository {repository_id}")
        project = await self.project_repo.get(repository.project_id)
        if project is None or project.owner_id != user_id:
            raise PermissionDeniedError("you do not have access to this repository")

    async def create_session(self, user_id: UUID, data: ChatSessionCreate) -> ChatSession:
        await self._verify_repo_access(data.repository_id, user_id)
        chat_session = ChatSession(
            repository_id=data.repository_id,
            user_id=user_id,
        )
        return await self.chat_session_repo.add(chat_session)

    async def get_session(self, session_id: UUID, user_id: UUID) -> ChatSession:
        chat_session = await self.chat_session_repo.get(session_id)
        if chat_session is None:
            raise NotFoundError(f"no chat session {session_id}")
        if chat_session.user_id != user_id:
            raise PermissionDeniedError("you do not own this chat session")
        return chat_session

    async def list_sessions(self, repository_id: UUID, user_id: UUID) -> Sequence[ChatSession]:
        await self._verify_repo_access(repository_id, user_id)
        return await self.chat_session_repo.list_for_repository_and_user(repository_id, user_id)

    async def rename_session(self, session_id: UUID, user_id: UUID, data: ChatSessionUpdate) -> ChatSession:
        chat_session = await self.get_session(session_id, user_id)
        if data.title is not None:
            chat_session.title = data.title
        if data.is_pinned is not None:
            chat_session.is_pinned = data.is_pinned
        return await self.chat_session_repo.add(chat_session)

    async def delete_session(self, session_id: UUID, user_id: UUID) -> None:
        chat_session = await self.get_session(session_id, user_id)
        await self.chat_session_repo.delete(chat_session)

    async def add_message(
        self,
        session_id: UUID,
        user_id: UUID,
        role: str,
        content: str,
        sources: list[Any] | None = None,
        confidence_score: float | None = None,
    ) -> ChatMessage:
        chat_session = await self.get_session(session_id, user_id)
        message = ChatMessage(
            session_id=chat_session.id,
            role=role,
            content=content,
            sources=sources or [],
            confidence_score=confidence_score,
        )
        return await self.chat_message_repo.add(message)

    async def list_messages(self, session_id: UUID, user_id: UUID) -> Sequence[ChatMessage]:
        await self.get_session(session_id, user_id)
        return await self.chat_message_repo.list_for_session(session_id)
