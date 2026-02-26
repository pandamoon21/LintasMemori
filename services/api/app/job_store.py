from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .models import Job, JobEvent


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_job(
    session: Session,
    *,
    account_id: str,
    provider: str,
    operation: str,
    params: dict[str, Any] | None = None,
    dry_run: bool = False,
    message: str = "Queued",
) -> Job:
    job = Job(
        account_id=account_id,
        provider=provider,
        operation=operation,
        params=params or {},
        dry_run=dry_run,
        status="queued",
        progress=0.0,
        message=message,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def add_job_event(session: Session, job: Job, message: str, progress: float | None = None, level: str = "info") -> JobEvent:
    event = JobEvent(job_id=job.id, level=level, message=message, progress=progress)
    session.add(event)
    job.updated_at = utc_now()
    return event
