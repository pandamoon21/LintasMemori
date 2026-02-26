from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from .adapters import gp_disguise_adapter, gpmc_adapter, gptk_adapter
from .auth_store import get_cookie_jar, get_gpmc_auth, get_session_state, set_session_state
from .explorer_service import ExplorerService
from .job_store import add_job_event
from .models import Account, Job
from .operation_safety import is_operation_destructive
from .pipeline_service import run_disguise_upload_pipeline


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _progress_update(session: Session, job: Job, progress: float, message: str) -> None:
    job.progress = max(0.0, min(progress, 1.0))
    job.message = message
    job.updated_at = utc_now()
    add_job_event(session, job, message=message, progress=job.progress)
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
            add_job_event(session, job, message="Blocked: destructive operation missing confirmed=true", level="error")
            session.commit()
            return

    job.status = "running"
    job.started_at = job.started_at or utc_now()
    job.message = "Job started"
    job.progress = max(job.progress, 0.01)
    add_job_event(session, job, message="Job started", progress=job.progress)
    session.commit()

    def progress(value: float, message: str) -> None:
        session.refresh(job)
        if job.cancel_requested:
            raise RuntimeError("Job cancelled by user")
        _progress_update(session, job, value, message)

    try:
        result: dict[str, Any]
        provider = job.provider
        operation = job.operation
        params = job.params or {}

        if provider == "advanced":
            provider = operation.split(".", 1)[0] if "." in operation else "gptk"

        if provider == "gpmc":
            auth_data = get_gpmc_auth(session, account)
            result = gpmc_adapter.run(
                operation=operation,
                params=params,
                auth_data=auth_data,
                dry_run=job.dry_run,
                progress=progress,
            )
        elif provider == "gp_disguise":
            result = gp_disguise_adapter.run(
                operation=operation,
                params=params,
                dry_run=job.dry_run,
                progress=progress,
            )
        elif provider == "gptk":
            cookie_jar = get_cookie_jar(session, account)
            current_state = get_session_state(session, account)
            result = gptk_adapter.run(
                operation=operation,
                params=params,
                cookie_jar=cookie_jar,
                session_state=current_state,
                _sidecar_base_url=None,
                dry_run=job.dry_run,
                progress=progress,
            )
            session_state = result.get("session_state")
            if isinstance(session_state, dict) and session_state:
                set_session_state(session, account, session_state)
                account.updated_at = utc_now()
                session.commit()
        elif provider == "indexer":
            explorer = ExplorerService(session, account)
            result = explorer.refresh_index(
                max_items=int(params.get("max_items", 3000)),
                include_album_members=bool(params.get("include_album_members", False)),
                force_full=bool(params.get("force_full", False)),
                progress=progress,
            )
        elif provider == "pipeline":
            auth_data = get_gpmc_auth(session, account)
            result = run_disguise_upload_pipeline(params=params, auth_data=auth_data, progress=progress)
        else:
            raise ValueError(f"Unknown provider: {job.provider}")

        session.refresh(job)
        if job.cancel_requested:
            job.status = "cancelled"
            job.message = "Job cancelled"
            job.progress = min(job.progress, 1.0)
            add_job_event(session, job, message="Job cancelled", progress=job.progress, level="warn")
        else:
            job.status = "succeeded"
            job.message = "Job completed"
            job.progress = 1.0
            job.result = result
            add_job_event(session, job, message="Job completed", progress=1.0)
        job.finished_at = utc_now()
        job.updated_at = utc_now()
        session.commit()
    except RuntimeError as exc:
        session.refresh(job)
        if str(exc) == "Job cancelled by user":
            job.status = "cancelled"
            job.message = "Job cancelled"
            job.error = {"message": "cancelled"}
            add_job_event(session, job, message="Job cancelled by user", level="warn")
        else:
            job.status = "failed"
            job.error = {"message": str(exc)}
            add_job_event(session, job, message=str(exc), level="error")
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
        add_job_event(session, job, message=message, level="error")
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
    add_job_event(session, queued, message="Worker claimed job", progress=queued.progress)
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
        add_job_event(session, queued, message="Worker claimed job", progress=queued.progress)
        local_account_counts[queued.account_id] = local + 1
        claimed.append(queued)

    if claimed:
        session.commit()
        for item in claimed:
            session.refresh(item)

    return claimed
