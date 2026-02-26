from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..advanced_service import AdvancedService
from ..database import get_session
from ..models import Account, PreviewAction
from ..operation_catalog import catalog_entries
from ..schemas import AdvancedCommitRequest, AdvancedPreviewRequest, AdvancedPreviewResult, ActionCommitResponse

router = APIRouter(prefix="/api/v2/advanced", tags=["v2-advanced"])


def _require_account(session: Session, account_id: str) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get("/operations")
def list_operations() -> list[dict]:
    return catalog_entries()


@router.post("/preview", response_model=AdvancedPreviewResult)
def preview_advanced(payload: AdvancedPreviewRequest, session: Session = Depends(get_session)) -> AdvancedPreviewResult:
    account = _require_account(session, payload.account_id)
    service = AdvancedService(session, account)
    try:
        return service.create_preview(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/commit", response_model=ActionCommitResponse)
def commit_advanced(payload: AdvancedCommitRequest, session: Session = Depends(get_session)) -> ActionCommitResponse:
    preview = session.get(PreviewAction, payload.preview_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="Preview not found")
    account = _require_account(session, preview.account_id)
    service = AdvancedService(session, account)
    try:
        result = service.commit_preview(payload.preview_id, confirm=payload.confirm)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ActionCommitResponse(**result)
