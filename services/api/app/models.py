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

    gpmc_auth_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gptk_cookie_jar: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    gptk_session_state: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    jobs: Mapped[list["Job"]] = relationship(back_populates="account")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)

    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(120), nullable=False)
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
