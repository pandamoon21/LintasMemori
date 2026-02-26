from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import delete
from sqlalchemy.orm import Session

from .adapters import gp_disguise_adapter, gpmc_adapter
from .config import settings
from .file_utils import expand_patterns
from .job_store import create_job
from .models import Account, PreviewAction
from .schemas import DisguiseUploadRequest, PipelinePreviewResult

ProgressFn = Callable[[float, str], None]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PipelineService:
    def __init__(self, session: Session, account: Account) -> None:
        self.session = session
        self.account = account

    def cleanup_expired(self) -> None:
        self.session.execute(delete(PreviewAction).where(PreviewAction.expires_at < utc_now()))
        self.session.commit()

    def create_preview(self, payload: DisguiseUploadRequest) -> PipelinePreviewResult:
        self.cleanup_expired()
        files = expand_patterns(payload.input_files)
        if not files:
            raise RuntimeError("No input files found for pipeline")

        preview = PreviewAction(
            account_id=self.account.id,
            kind="pipeline_disguise_upload",
            action="pipeline.disguise_upload",
            query_payload={
                "input_files": payload.input_files,
                "disguise_type": payload.disguise_type,
                "separator": payload.separator,
            },
            action_params={
                "output_policy": payload.output_policy,
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

        return PipelinePreviewResult(
            preview_id=preview.id,
            input_count=len(files),
            estimated_outputs=len(files),
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

        params: dict[str, Any] = {
            "input_files": list(preview.matched_media_keys or []),
            "disguise_type": (preview.query_payload or {}).get("disguise_type", "image"),
            "separator": (preview.query_payload or {}).get("separator", "FILE_DATA_BEGIN"),
            "output_policy": dict((preview.action_params or {}).get("output_policy") or {}),
            "gpmc_upload_options": dict((preview.action_params or {}).get("gpmc_upload_options") or {}),
            "confirmed": True,
        }

        job = create_job(
            self.session,
            account_id=self.account.id,
            provider="pipeline",
            operation="pipeline.disguise_upload",
            params=params,
            dry_run=False,
            message=f"Queued pipeline from preview {preview.id}",
        )

        preview.status = "committed"
        preview.committed_job_id = job.id
        preview.updated_at = utc_now()
        self.session.commit()

        return {"preview_id": preview.id, "job_id": job.id, "status": "queued"}


def run_disguise_upload_pipeline(
    *,
    params: dict[str, Any],
    auth_data: str | None,
    progress: ProgressFn,
) -> dict[str, Any]:
    input_files = params.get("input_files")
    if not isinstance(input_files, list) or not input_files:
        raise RuntimeError("pipeline.disguise_upload requires params.input_files[]")

    disguise_type = str(params.get("disguise_type", "image"))
    separator = str(params.get("separator", "FILE_DATA_BEGIN"))
    output_policy = dict(params.get("output_policy") or {})
    upload_options = dict(params.get("gpmc_upload_options") or {})

    keep_artifacts = bool(output_policy.get("keep_artifacts", False))
    configured_output = output_policy.get("output_dir")

    temp_dir: str | None = None
    output_dir: str | None = None
    if configured_output:
        output_dir = str(configured_output)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    else:
        temp_dir = tempfile.mkdtemp(prefix="lm_disguise_")
        output_dir = temp_dir

    progress(0.08, "Running gp_disguise hide step")
    disguise_result = gp_disguise_adapter.run(
        operation="gp_disguise.hide",
        params={"files": input_files, "type": disguise_type, "separator": separator, "output": output_dir},
        dry_run=False,
        progress=lambda value, message: progress(0.08 + value * 0.42, f"disguise: {message}"),
    )
    created = [str(item) for item in (disguise_result.get("created") or [])]
    if not created:
        raise RuntimeError("gp_disguise did not produce output files")

    progress(0.55, "Running gpmc upload step")
    upload_params: dict[str, Any] = {"target": created, "recursive": False}
    upload_params.update(upload_options)
    upload_result = gpmc_adapter.run(
        operation="gpmc.upload",
        params=upload_params,
        auth_data=auth_data,
        dry_run=False,
        progress=lambda value, message: progress(0.55 + value * 0.4, f"upload: {message}"),
    )

    cleaned_files: list[str] = []
    if not keep_artifacts:
        progress(0.97, "Cleaning up temporary artifacts")
        for item in created:
            try:
                Path(item).unlink(missing_ok=True)
                cleaned_files.append(item)
            except OSError:
                continue
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

    progress(1.0, "Pipeline completed")
    return {
        "summary": "pipeline completed",
        "processed_count": len(input_files),
        "success_count": len(created),
        "failed_count": 0,
        "artifacts": {"created": created, "cleaned": cleaned_files, "kept": keep_artifacts},
        "upload": upload_result,
        "errors": [],
    }
