import uuid
from typing import Any

from sqlalchemy import REAL, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    node_type: Mapped[str] = mapped_column(String(64), nullable=False)
    ref_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), default=None)  # polymorphic, no FK -- see docs/04_DATABASE_SCHEMA.sql
    label: Mapped[str] = mapped_column(String(512), nullable=False)
    # Python attribute deliberately isn't "metadata" -- that name is reserved on
    # every SQLAlchemy declarative model (Base.metadata is the schema registry
    # itself), so using it here would shadow that class attribute. `mapped_column`'s
    # first positional arg pins the actual DB column name back to "metadata",
    # matching the schema exactly; only the Python-side attribute differs.
    node_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False
    )
    edge_type: Mapped[str] = mapped_column(String(64), nullable=False)
    weight: Mapped[float] = mapped_column(REAL, nullable=False, default=1.0)
    node_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
