from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from .config import settings
from .file_utils import collect_media_files
from .job_store import create_job
from .models import Account, PreviewAction
from .schemas import UploadPreviewRequest, UploadPreviewResult


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UploadService:
    def __init__(self, session: Session, account: Account) -> None:
        self.session = session
        self.account = account

    def cleanup_expired(self) -> None:
        self.session.execute(delete(PreviewAction).where(PreviewAction.expires_at < utc_now()))
        self.session.commit()

    def create_preview(self, payload: UploadPreviewRequest) -> UploadPreviewResult:
        self.cleanup_expired()
        files = collect_media_files(payload.target, recursive=payload.recursive)
        if not files:
            raise RuntimeError("No media files found in target")

        preview = PreviewAction(
            account_id=self.account.id,
            kind="upload",
            action="gpmc.upload",
            query_payload={
                "target": payload.target,
                "recursive": payload.recursive,
            },
            action_params={
                "gpmc_upload_options": payload.gpmc_upload_options,
            },
            matched_media_keys=[item.as_posix() for item in files],
            sample_items=[{"path": item.as_posix()} for item in files[:20]],
            warnings=[],
            requires_confirm=True,
            status="previewed",
            expires_at=utc_now() + timedelta(minutes=settings.preview_ttl_minutes),
        )
        self.session.add(preview)
        self.session.commit()
        self.session.refresh(preview)

        return UploadPreviewResult(
            preview_id=preview.id,
            target_count=len(files),
            sample_files=[item.as_posix() for item in files[:20]],
            warnings=[],
            requires_confirm=True,
        )

    def commit_preview(self, preview_id: str, confirm: bool) -> dict[str, Any]:
        preview = self.session.get(PreviewAction, preview_id)
        if preview is None or preview.account_id != self.account.id:
            raise RuntimeError("Preview not found")
        if preview.expires_at < utc_now():
            preview.status = "expired"
            self.session.commit()
            raise RuntimeError("Preview expired")
        if preview.status != "previewed":
            raise RuntimeError("Preview already committed or invalid")
        if preview.requires_confirm and not confirm:
            raise RuntimeError("Commit requires explicit confirm=true")

        target_files = list(preview.matched_media_keys or [])
        if not target_files:
            raise RuntimeError("Upload preview has no files")

        options = dict((preview.action_params or {}).get("gpmc_upload_options") or {})
        params: dict[str, Any] = {"target": target_files, "recursive": False, "confirmed": True}
        params.update(options)

        job = create_job(
            self.session,
            account_id=self.account.id,
            provider="gpmc",
            operation="gpmc.upload",
            params=params,
            dry_run=False,
            message=f"Queued upload from preview {preview.id}",
        )

        preview.status = "committed"
        preview.committed_job_id = job.id
        preview.updated_at = utc_now()
        self.session.commit()

        return {"preview_id": preview.id, "job_id": job.id, "status": "queued"}
