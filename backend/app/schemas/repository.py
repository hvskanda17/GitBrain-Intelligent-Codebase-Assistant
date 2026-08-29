import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RepositoryCreate(BaseModel):
    project_id: uuid.UUID
    remote_url: str = Field(min_length=1, max_length=1024)
    branch: str | None = Field(default=None, max_length=255)


class RepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    remote_url: str
    default_branch: str
    primary_language: str | None
    status: str
    last_indexed_at: datetime | None
    stats: dict[str, Any]
    created_at: datetime


class RepositoryStatus(BaseModel):
    status: str
    progress_pct: int | None = None
    current_stage: str | None = None


class RepositoryCreateResponse(BaseModel):
    repository_id: uuid.UUID
    status: str
