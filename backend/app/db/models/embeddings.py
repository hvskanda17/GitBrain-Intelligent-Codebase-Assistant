import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)  # "function" | "class" for now
    source_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)  # polymorphic, no FK -- see docs/04_DATABASE_SCHEMA.sql
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Dimension is read from settings at import time rather than hardcoded, so a
    # deployment that changes EMBEDDING_DIMENSIONS (a different model) gets a
    # matching column without a code edit -- just a migration, same as any other
    # settings-driven schema choice.
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
