from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChatMessageRead(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    sources: list[Any]
    confidence_score: float | None = None
    is_saved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageCreate(BaseModel):
    content: str


class ChatSessionCreate(BaseModel):
    repository_id: UUID


class ChatSessionUpdate(BaseModel):
    title: str | None = None
    is_pinned: bool | None = None


class ChatSessionRead(BaseModel):
    id: UUID
    repository_id: UUID
    user_id: UUID
    title: str | None
    is_pinned: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
