from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_session
from ..models import Account, PreviewAction
from ..schemas import ActionCommitResponse, UploadCommitRequest, UploadPreviewRequest, UploadPreviewResult
from ..upload_service import UploadService

router = APIRouter(prefix="/api/v2/uploads", tags=["v2-uploads"])


def _require_account(session: Session, account_id: str) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post("/preview", response_model=UploadPreviewResult)
def preview_upload(payload: UploadPreviewRequest, session: Session = Depends(get_session)) -> UploadPreviewResult:
    account = _require_account(session, payload.account_id)
    service = UploadService(session, account)
    try:
        return service.create_preview(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/commit", response_model=ActionCommitResponse)
def commit_upload(payload: UploadCommitRequest, session: Session = Depends(get_session)) -> ActionCommitResponse:
    preview = session.get(PreviewAction, payload.preview_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="Preview not found")
    account = _require_account(session, preview.account_id)
    service = UploadService(session, account)
    try:
        result = service.commit_preview(payload.preview_id, confirm=payload.confirm)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ActionCommitResponse(**result)
