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
from ..models import Job, JobEvent
from ..schemas import CancelJobResponse, JobOut
from ..serializers import job_to_out

router = APIRouter(prefix="/api/v2/jobs", tags=["v2-jobs"])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("", response_model=list[JobOut])
def list_jobs(
    account_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    include_events: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=1000),
    session: Session = Depends(get_session),
) -> list[JobOut]:
    stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
    if account_id:
        stmt = stmt.where(Job.account_id == account_id)
    if status:
        stmt = stmt.where(Job.status == status)
    rows = session.execute(stmt).scalars().all()
    return [job_to_out(item, include_events=include_events) for item in rows]


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
                    select(JobEvent, Job)
                    .join(Job, Job.id == JobEvent.job_id)
                    .where(JobEvent.created_at > cursor)
                    .order_by(JobEvent.created_at.asc(), JobEvent.id.asc())
                    .limit(300)
                ).all()
                if not rows:
                    yield ": keepalive\n\n"
                    continue

                for event, job in rows:
                    cursor = event.created_at
                    payload = {
                        "event_id": event.id,
                        "type": "job_event",
                        "job_id": job.id,
                        "payload": {
                            "level": event.level,
                            "message": event.message,
                            "progress": event.progress,
                            "job": job_to_out(job).model_dump(mode="json"),
                        },
                        "created_at": event.created_at.isoformat(),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, include_events: bool = Query(default=True), session: Session = Depends(get_session)) -> JobOut:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_to_out(job, include_events=include_events)


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
