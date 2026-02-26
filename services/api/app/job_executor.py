from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from .adapters import gp_disguise_adapter, gpmc_adapter, gptk_adapter
from .config import settings
from .models import Account, Job
from .operation_safety import is_operation_destructive


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _progress_update(session: Session, job: Job, progress: float, message: str) -> None:
    job.progress = max(0.0, min(progress, 1.0))
    job.message = message
    job.updated_at = utc_now()
    session.commit()


def execute_job(session: Session, job_id: str) -> None:
    job = session.get(Job, job_id)
    if job is None:
        return
    if job.status not in {"queued", "running"}:
        return

    account = session.get(Account, job.account_id)
    if account is None:
        job.status = "failed"
        job.error = {"message": "account not found"}
        job.finished_at = utc_now()
        session.commit()
        return

    if is_operation_destructive(job.operation) and not job.dry_run:
        if not bool((job.params or {}).get("confirmed", False)):
            job.status = "failed"
            job.error = {"message": "Destructive operation requires params.confirmed=true after dry-run"}
            job.finished_at = utc_now()
            session.commit()
            return

    job.status = "running"
    job.started_at = job.started_at or utc_now()
    job.message = "Job started"
    job.progress = max(job.progress, 0.01)
    session.commit()

    def progress(value: float, message: str) -> None:
        session.refresh(job)
        if job.cancel_requested:
            raise RuntimeError("Job cancelled by user")
        _progress_update(session, job, value, message)

    try:
        result: dict[str, Any]

        if job.provider == "gpmc":
            result = gpmc_adapter.run(
                operation=job.operation,
                params=job.params or {},
                auth_data=account.gpmc_auth_data,
                dry_run=job.dry_run,
                progress=progress,
            )
        elif job.provider == "gp_disguise":
            result = gp_disguise_adapter.run(
                operation=job.operation,
                params=job.params or {},
                dry_run=job.dry_run,
                progress=progress,
            )
        elif job.provider == "gptk":
            result = gptk_adapter.run(
                operation=job.operation,
                params=job.params or {},
                cookie_jar=account.gptk_cookie_jar,
                session_state=account.gptk_session_state,
                sidecar_base_url=settings.sidecar_base_url,
                dry_run=job.dry_run,
                progress=progress,
            )
            session.refresh(account)
            session.refresh(job)
            session_state = result.get("session_state")
            if isinstance(session_state, dict) and session_state:
                account.gptk_session_state = session_state
                session.commit()
        else:
            raise ValueError(f"Unknown provider: {job.provider}")

        session.refresh(job)
        if job.cancel_requested:
            job.status = "cancelled"
            job.message = "Job cancelled"
            job.progress = min(job.progress, 1.0)
        else:
            job.status = "succeeded"
            job.message = "Job completed"
            job.progress = 1.0
            job.result = result
        job.finished_at = utc_now()
        job.updated_at = utc_now()
        session.commit()
    except RuntimeError as exc:
        session.refresh(job)
        if str(exc) == "Job cancelled by user":
            job.status = "cancelled"
            job.message = "Job cancelled"
            job.error = {"message": "cancelled"}
        else:
            job.status = "failed"
            job.error = {"message": str(exc)}
        job.finished_at = utc_now()
        session.commit()
    except Exception as exc:  # noqa: BLE001
        session.refresh(job)
        message = str(exc)
        if "auth_data" in message.lower() or "cookie" in message.lower():
            job.status = "requires_credentials"
        else:
            job.status = "failed"
        job.error = {"message": message}
        job.finished_at = utc_now()
        job.updated_at = utc_now()
        session.commit()


def claim_next_job(session: Session) -> Job | None:
    queued = session.execute(
        select(Job).where(Job.status == "queued").order_by(Job.created_at.asc()).limit(1)
    ).scalar_one_or_none()
    if queued is None:
        return None

    queued.status = "running"
    queued.started_at = utc_now()
    queued.updated_at = utc_now()
    queued.message = "Worker claimed job"
    queued.progress = max(queued.progress, 0.01)
    session.commit()
    session.refresh(queued)
    return queued


def claim_jobs(session: Session, limit: int, max_per_account: int, in_flight_accounts: dict[str, int] | None = None) -> list[Job]:
    if limit <= 0:
        return []

    in_flight_accounts = in_flight_accounts or {}
    claimed: list[Job] = []

    query: Select[tuple[Job]] = select(Job).where(Job.status == "queued").order_by(Job.created_at.asc()).limit(500)
    queued_jobs = session.execute(query).scalars().all()

    local_account_counts: dict[str, int] = {}

    for queued in queued_jobs:
        if len(claimed) >= limit:
            break

        in_flight = in_flight_accounts.get(queued.account_id, 0)
        local = local_account_counts.get(queued.account_id, 0)
        if in_flight + local >= max_per_account:
            continue

        queued.status = "running"
        queued.started_at = queued.started_at or utc_now()
        queued.updated_at = utc_now()
        queued.message = "Worker claimed job"
        queued.progress = max(queued.progress, 0.01)
        local_account_counts[queued.account_id] = local + 1
        claimed.append(queued)

    if claimed:
        session.commit()
        for item in claimed:
            session.refresh(item)

    return claimed
