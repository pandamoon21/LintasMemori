from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import engine, get_session
from ..models import Account, Job
from ..operation_safety import is_operation_destructive
from ..schemas import CancelJobResponse, JobCreate, JobOut
from ..serializers import job_to_out

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@router.post("", response_model=JobOut)
def create_job(payload: JobCreate, session: Session = Depends(get_session)) -> JobOut:
    account = session.get(Account, payload.account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    if is_operation_destructive(payload.operation) and not payload.dry_run:
        if not bool(payload.params.get("confirmed", False)):
            raise HTTPException(
                status_code=400,
                detail="Destructive operation requires params.confirmed=true after dry-run",
            )

    job = Job(
        account_id=payload.account_id,
        provider=payload.provider,
        operation=payload.operation,
        params=payload.params,
        dry_run=payload.dry_run,
        status="queued",
        progress=0.0,
        message="Queued",
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job_to_out(job)


@router.get("", response_model=list[JobOut])
def list_jobs(limit: int = Query(default=200, ge=1, le=1000), session: Session = Depends(get_session)) -> list[JobOut]:
    rows = session.execute(select(Job).order_by(Job.created_at.desc()).limit(limit)).scalars().all()
    return [job_to_out(row) for row in rows]


@router.get("/stream")
async def stream_jobs(
    since: Optional[str] = Query(default=None, description="ISO datetime to start stream window"),
    poll_seconds: float = Query(default=settings.poll_interval_seconds, ge=0.2, le=5.0),
):
    try:
        cursor = datetime.fromisoformat(since) if since else datetime.now(timezone.utc)
    except ValueError:
        cursor = datetime.now(timezone.utc)

    async def event_generator():
        nonlocal cursor
        while True:
            await asyncio.sleep(poll_seconds)
            with Session(engine) as db:
                rows = db.execute(
                    select(Job).where(Job.updated_at > cursor).order_by(Job.updated_at.asc()).limit(300)
                ).scalars().all()
                if not rows:
                    yield ": keepalive\n\n"
                    continue
                for row in rows:
                    cursor = row.updated_at
                    payload = job_to_out(row).model_dump(mode="json")
                    yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, session: Session = Depends(get_session)) -> JobOut:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_to_out(job)


@router.post("/{job_id}/cancel", response_model=CancelJobResponse)
def cancel_job(job_id: str, session: Session = Depends(get_session)) -> CancelJobResponse:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in {"succeeded", "failed", "cancelled"}:
        return CancelJobResponse(id=job.id, status=job.status, cancel_requested=job.cancel_requested)

    job.cancel_requested = True
    job.updated_at = utc_now()
    if job.status == "queued":
        job.status = "cancelled"
        job.message = "Cancelled before execution"
        job.finished_at = utc_now()

    session.commit()
    session.refresh(job)
    return CancelJobResponse(id=job.id, status=job.status, cancel_requested=job.cancel_requested)
