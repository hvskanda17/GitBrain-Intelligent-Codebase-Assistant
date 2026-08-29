import uuid
from datetime import datetime

from sqlalchemy import CHAR, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Directory(Base):
    __tablename__ = "directories"
    __table_args__ = (UniqueConstraint("repository_id", "path", name="uq_directories_repo_path"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("directories.id", ondelete="CASCADE"), default=None
    )
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class File(Base):
    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("repository_id", "path", name="uq_files_repo_path"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    directory_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("directories.id", ondelete="CASCADE"), default=None
    )
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str | None] = mapped_column(String(32), default=None)
    language: Mapped[str | None] = mapped_column(String(64), default=None)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)  # sha256 hex digest
    loc: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_test_file: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
