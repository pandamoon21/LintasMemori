from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from .config import settings
from .job_store import create_job
from .models import Account, PreviewAction
from .operation_safety import is_operation_destructive
from .schemas import AdvancedPreviewRequest, AdvancedPreviewResult


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AdvancedService:
    def __init__(self, session: Session, account: Account) -> None:
        self.session = session
        self.account = account

    def cleanup_expired(self) -> None:
        self.session.execute(delete(PreviewAction).where(PreviewAction.expires_at < utc_now()))
        self.session.commit()

    def create_preview(self, payload: AdvancedPreviewRequest) -> AdvancedPreviewResult:
        self.cleanup_expired()
        operation = payload.operation if payload.operation.startswith(f"{payload.provider}.") else f"{payload.provider}.{payload.operation}"
        warnings: list[str] = []
        if is_operation_destructive(operation):
            warnings.append("Operation is destructive. Confirm explicitly before commit.")

        preview = PreviewAction(
            account_id=self.account.id,
            kind="advanced",
            action=operation,
            query_payload={},
            action_params=payload.params,
            matched_media_keys=[],
            sample_items=[],
            warnings=warnings,
            requires_confirm=True,
            status="previewed",
            expires_at=utc_now() + timedelta(minutes=settings.preview_ttl_minutes),
        )
        self.session.add(preview)
        self.session.commit()
        self.session.refresh(preview)

        return AdvancedPreviewResult(
            preview_id=preview.id,
            operation=operation,
            provider=payload.provider,
            warnings=warnings,
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

        operation = str(preview.action)
        provider = operation.split(".", 1)[0] if "." in operation else "gptk"
        params = dict(preview.action_params or {})
        params.setdefault("confirmed", True)

        job = create_job(
            self.session,
            account_id=self.account.id,
            provider=provider,
            operation=operation,
            params=params,
            dry_run=False,
            message=f"Queued advanced operation from preview {preview.id}",
        )
        preview.status = "committed"
        preview.committed_job_id = job.id
        preview.updated_at = utc_now()
        self.session.commit()
        return {"preview_id": preview.id, "job_id": job.id, "status": "queued"}
