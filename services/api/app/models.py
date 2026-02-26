from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    email_hint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Legacy fallback fields (kept for compatibility with existing data)
    gpmc_auth_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gptk_cookie_jar: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    gptk_session_state: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    jobs: Mapped[list["Job"]] = relationship(back_populates="account")
    gpmc_credential: Mapped[Optional["CredentialGpmc"]] = relationship(back_populates="account", uselist=False)
    cookie_credential: Mapped[Optional["CredentialCookies"]] = relationship(back_populates="account", uselist=False)
    gphotos_session: Mapped[Optional["GPhotosSessionState"]] = relationship(back_populates="account", uselist=False)


class CredentialGpmc(Base):
    __tablename__ = "credentials_gpmc"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=False, unique=True, index=True)
    auth_data: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    account: Mapped[Account] = relationship(back_populates="gpmc_credential")


class CredentialCookies(Base):
    __tablename__ = "credentials_cookies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=False, unique=True, index=True)
    cookie_jar: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    account: Mapped[Account] = relationship(back_populates="cookie_credential")


class GPhotosSessionState(Base):
    __tablename__ = "gphotos_session_state"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=False, unique=True, index=True)
    session_state: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    account: Mapped[Account] = relationship(back_populates="gphotos_session")


class AlbumIndex(Base):
    __tablename__ = "album_index"

    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), primary_key=True)
    media_key: Mapped[str] = mapped_column(String(255), primary_key=True)

    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_actor_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    item_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    creation_timestamp: Mapped[Optional[int]] = mapped_column(nullable=True)
    modified_timestamp: Mapped[Optional[int]] = mapped_column(nullable=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    thumb: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False, index=True)


class MediaIndex(Base):
    __tablename__ = "media_index"

    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), primary_key=True)
    media_key: Mapped[str] = mapped_column(String(255), primary_key=True)

    dedup_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    timestamp_taken: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    timestamp_uploaded: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    timezone_offset: Mapped[Optional[int]] = mapped_column(nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    size: Mapped[Optional[int]] = mapped_column(nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_trashed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    album_ids: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    thumb_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    space_flags: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="library", nullable=False, index=True)

    raw_item: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False, index=True)


class PreviewAction(Base):
    __tablename__ = "preview_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)

    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)

    query_payload: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    action_params: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    matched_media_keys: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    sample_items: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    warnings: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    requires_confirm: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="previewed", nullable=False, index=True)

    committed_job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)

    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False, index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    account: Mapped[Account] = relationship(back_populates="jobs")
    events: Mapped[list["JobEvent"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobEvent(Base):
    __tablename__ = "job_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False, index=True)

    level: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    progress: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    job: Mapped[Job] = relationship(back_populates="events")


class PipelineProfile(Base):
    __tablename__ = "pipeline_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    config: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
