from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.db.models.chat import ChatMessage, ChatSession
from app.repositories.base import BaseRepository


class ChatSessionRepository(BaseRepository[ChatSession]):
    model = ChatSession

    async def list_for_repository_and_user(self, repository_id: UUID, user_id: UUID) -> Sequence[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(
                ChatSession.repository_id == repository_id,
                ChatSession.user_id == user_id,
            )
            .order_by(ChatSession.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class ChatMessageRepository(BaseRepository[ChatMessage]):
    model = ChatMessage

    async def list_for_session(self, session_id: UUID) -> Sequence[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
