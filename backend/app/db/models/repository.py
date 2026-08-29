import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class IndexingStatus(str, enum.Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    remote_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), default="main")
    local_path: Mapped[str | None] = mapped_column(String(1024), default=None)
    primary_language: Mapped[str | None] = mapped_column(String(64), default=None)
    status: Mapped[IndexingStatus] = mapped_column(
        Enum(IndexingStatus, name="indexing_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=IndexingStatus.PENDING,
    )
    last_indexed_commit_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="repositories")
