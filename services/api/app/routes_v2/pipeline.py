from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_session
from ..models import Account, PreviewAction
from ..pipeline_service import PipelineService
from ..schemas import ActionCommitResponse, DisguiseUploadRequest, PipelineCommitRequest, PipelinePreviewResult

router = APIRouter(prefix="/api/v2/pipeline", tags=["v2-pipeline"])


def _require_account(session: Session, account_id: str) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post("/disguise-upload/preview", response_model=PipelinePreviewResult)
def preview_disguise_upload(payload: DisguiseUploadRequest, session: Session = Depends(get_session)) -> PipelinePreviewResult:
    account = _require_account(session, payload.account_id)
    service = PipelineService(session, account)
    try:
        return service.create_preview(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/disguise-upload/commit", response_model=ActionCommitResponse)
def commit_disguise_upload(payload: PipelineCommitRequest, session: Session = Depends(get_session)) -> ActionCommitResponse:
    preview = session.get(PreviewAction, payload.preview_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="Preview not found")
    account = _require_account(session, preview.account_id)
    service = PipelineService(session, account)
    try:
        result = service.commit_preview(payload.preview_id, confirm=payload.confirm)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ActionCommitResponse(**result)
