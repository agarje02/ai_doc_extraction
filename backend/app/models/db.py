"""SQLAlchemy models and session management.

Works with SQLite (default, zero-setup) or PostgreSQL / Supabase - just point
``DATABASE_URL`` at the target. JSON columns use ``JSONB`` on PostgreSQL and
plain ``JSON`` elsewhere.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

from app.config import get_settings

# JSONB on PostgreSQL (indexable, faster), generic JSON everywhere else.
JSONType = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_db_url(url: str) -> str:
    """Upgrade bare ``postgres(ql)://`` URLs to the psycopg (v3) driver.

    Supabase copy-paste strings look like ``postgresql://...`` which SQLAlchemy
    would route to psycopg2; we standardize on psycopg3 which is what we depend
    on.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    # Owner/workspace id used to scope which documents a user can see.
    owner_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    filename: Mapped[str] = mapped_column(String(512))
    kind: Mapped[str] = mapped_column(String(32))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    stored_path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    runs: Mapped[list["ExtractionRun"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    doc_type: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    model: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="completed")
    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    result: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    document: Mapped[Document] = relationship(back_populates="runs")
    field_results: Mapped[list["FieldResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    corrections: Mapped[list["Correction"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class FieldResult(Base):
    __tablename__ = "field_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("extraction_runs.id"))
    name: Mapped[str] = mapped_column(String(128))
    value: Mapped[dict] = mapped_column(JSONType, default=dict)  # {"value": ...}
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    issues: Mapped[list] = mapped_column(JSONType, default=list)

    run: Mapped[ExtractionRun] = relationship(back_populates="field_results")


class Correction(Base):
    __tablename__ = "corrections"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("extraction_runs.id"))
    field_name: Mapped[str] = mapped_column(String(128))
    corrected_value: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    run: Mapped[ExtractionRun] = relationship(back_populates="corrections")


_settings = get_settings()
_db_url = _normalize_db_url(_settings.database_url)
_is_sqlite = _db_url.startswith("sqlite")

if _is_sqlite:
    _connect_args: dict = {"check_same_thread": False}
else:
    # Disable psycopg auto prepared-statements so the app also works behind the
    # Supabase transaction pooler (Supavisor/pgbouncer on port 6543), which does
    # not support server-side prepared statements. Harmless in session mode.
    _connect_args = {"prepare_threshold": None}

engine = create_engine(
    _db_url,
    connect_args=_connect_args,
    # pool_pre_ping avoids stale-connection errors against hosted DBs
    # (Supabase/pgbouncer drop idle connections).
    pool_pre_ping=not _is_sqlite,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_owner_id_column()


def _ensure_owner_id_column() -> None:
    """Lightweight migration: add ``documents.owner_id`` to pre-existing DBs.

    ``create_all`` never alters existing tables, so databases created before
    this column was introduced would be missing it. Add it if absent.
    """
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("documents")}
    if "owner_id" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE documents ADD COLUMN owner_id VARCHAR(128) DEFAULT ''")
            )


def get_session():
    """FastAPI dependency that yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
