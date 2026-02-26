from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..action_service import ActionService
from ..database import get_session
from ..models import Account, PreviewAction
from ..schemas import ActionCommitRequest, ActionCommitResponse, ActionPreviewRequest, ActionPreviewResult, ExplorerItem

router = APIRouter(prefix="/api/v2/actions", tags=["v2-actions"])


def _require_account(session: Session, account_id: str) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post("/preview", response_model=ActionPreviewResult)
def preview_action(payload: ActionPreviewRequest, session: Session = Depends(get_session)) -> ActionPreviewResult:
    account = _require_account(session, payload.account_id)
    service = ActionService(session, account)
    try:
        return service.create_preview(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/commit", response_model=ActionCommitResponse)
def commit_action(payload: ActionCommitRequest, session: Session = Depends(get_session)) -> ActionCommitResponse:
    preview = session.get(PreviewAction, payload.preview_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="Preview not found")
    account = _require_account(session, preview.account_id)
    service = ActionService(session, account)
    try:
        result = service.commit_preview(payload.preview_id, confirm=payload.confirm)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ActionCommitResponse(**result)


@router.get("/previews/{preview_id}", response_model=ActionPreviewResult)
def get_preview(
    preview_id: str,
    account_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> ActionPreviewResult:
    preview = session.get(PreviewAction, preview_id)
    if preview is None or preview.kind != "explorer_action":
        raise HTTPException(status_code=404, detail="Preview not found")
    if account_id and preview.account_id != account_id:
        raise HTTPException(status_code=404, detail="Preview not found for account")
    sample_items = [ExplorerItem(**item) for item in (preview.sample_items or [])]
    return ActionPreviewResult(
        preview_id=preview.id,
        match_count=len(preview.matched_media_keys or []),
        sample_items=sample_items,
        warnings=list(preview.warnings or []),
        requires_confirm=preview.requires_confirm,
    )
