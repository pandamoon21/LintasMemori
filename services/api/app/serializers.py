from __future__ import annotations

from .models import Account, Job
from .schemas import AccountOut, JobOut


def account_to_out(account: Account) -> AccountOut:
    return AccountOut(
        id=account.id,
        label=account.label,
        email_hint=account.email_hint,
        is_active=account.is_active,
        has_gpmc_auth_data=bool(account.gpmc_auth_data),
        has_gptk_cookie_jar=bool(account.gptk_cookie_jar),
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def job_to_out(job: Job) -> JobOut:
    return JobOut(
        id=job.id,
        account_id=job.account_id,
        provider=job.provider,
        operation=job.operation,
        dry_run=job.dry_run,
        params=job.params or {},
        status=job.status,
        progress=job.progress,
        message=job.message,
        result=job.result,
        error=job.error,
        cancel_requested=job.cancel_requested,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )
