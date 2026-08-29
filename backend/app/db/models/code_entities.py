import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Class(Base):
    __tablename__ = "classes"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    qualified_name: Mapped[str | None] = mapped_column(String(1024), default=None)
    docstring: Mapped[str | None] = mapped_column(Text, default=None)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_class_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("classes.id"), default=None
    )
    is_abstract: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Method(Base):
    __tablename__ = "methods"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, default=None)
    return_type: Mapped[str | None] = mapped_column(String(255), default=None)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="public")
    is_static: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_async: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    docstring: Mapped[str | None] = mapped_column(Text, default=None)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Function(Base):
    __tablename__ = "functions"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    qualified_name: Mapped[str | None] = mapped_column(String(1024), default=None)
    signature: Mapped[str | None] = mapped_column(Text, default=None)
    return_type: Mapped[str | None] = mapped_column(String(255), default=None)
    parameters: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    docstring: Mapped[str | None] = mapped_column(Text, default=None)
    is_async: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_exported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    complexity_score: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Import(Base):
    __tablename__ = "imports"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )
    imported_symbol: Mapped[str] = mapped_column(String(512), nullable=False)
    source_module: Mapped[str] = mapped_column(String(1024), nullable=False)
    resolved_file_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("files.id", ondelete="SET NULL"), default=None
    )
    is_external: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    alias: Mapped[str | None] = mapped_column(String(255), default=None)
    line_number: Mapped[int | None] = mapped_column(Integer, default=None)


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )
    symbol_name: Mapped[str] = mapped_column(String(512), nullable=False)
    symbol_type: Mapped[str | None] = mapped_column(String(64), default=None)
    line_number: Mapped[int | None] = mapped_column(Integer, default=None)


class CallGraph(Base):
    __tablename__ = "call_graph"
    __table_args__ = (
        CheckConstraint(
            "caller_function_id IS NOT NULL OR caller_method_id IS NOT NULL", name="caller_present"
        ),
        CheckConstraint(
            "callee_function_id IS NOT NULL OR callee_method_id IS NOT NULL OR callee_raw_name IS NOT NULL",
            name="callee_present",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    caller_function_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("functions.id", ondelete="CASCADE"), default=None
    )
    caller_method_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("methods.id", ondelete="CASCADE"), default=None
    )
    callee_function_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("functions.id", ondelete="CASCADE"), default=None
    )
    callee_method_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("methods.id", ondelete="CASCADE"), default=None
    )
    callee_raw_name: Mapped[str | None] = mapped_column(String(512), default=None)
    call_line: Mapped[int | None] = mapped_column(Integer, default=None)
