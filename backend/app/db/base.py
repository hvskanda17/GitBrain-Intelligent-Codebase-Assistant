from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. alembic/env.py imports every module under
    app.db.models before touching Base.metadata, so autogenerate (for migrations
    after Phase 2's hand-authored baseline) sees the full schema."""

    pass
