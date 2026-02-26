from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth_store import set_cookie_jar, set_gpmc_auth
from ..cookies import parse_cookie_string, parse_netscape_cookie_file
from ..database import get_session
from ..gptk_service import GptkService
from ..models import Account
from ..schemas import (
    AccountCreate,
    AccountOut,
    CookieImportResponse,
    SessionRefreshRequest,
    SessionRefreshResponse,
    SetCookiesPasteRequest,
    SetGpmcAuthRequest,
)
from ..serializers import account_to_out

router = APIRouter(prefix="/api/v2/accounts", tags=["v2-accounts"])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _require_account(session: Session, account_id: str) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post("", response_model=AccountOut)
def create_account(payload: AccountCreate, session: Session = Depends(get_session)) -> AccountOut:
    account = Account(label=payload.label, email_hint=payload.email_hint)
    session.add(account)
    session.commit()
    session.refresh(account)
    return account_to_out(account)


@router.get("", response_model=list[AccountOut])
def list_accounts(session: Session = Depends(get_session)) -> list[AccountOut]:
    rows = session.execute(select(Account).order_by(Account.created_at.desc())).scalars().all()
    return [account_to_out(item) for item in rows]


@router.post("/{account_id}/credentials/gpmc", response_model=AccountOut)
def set_gpmc_credentials(account_id: str, payload: SetGpmcAuthRequest, session: Session = Depends(get_session)) -> AccountOut:
    account = _require_account(session, account_id)
    set_gpmc_auth(session, account, payload.auth_data)
    account.updated_at = utc_now()
    session.commit()
    session.refresh(account)
    return account_to_out(account)


@router.post("/{account_id}/credentials/cookies/import", response_model=CookieImportResponse)
async def import_cookies_file(
    account_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> CookieImportResponse:
    account = _require_account(session, account_id)
    data = await file.read()
    try:
        raw = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Cookie file must be UTF-8 text") from exc

    cookies = parse_netscape_cookie_file(raw)
    if not cookies:
        raise HTTPException(status_code=400, detail="No valid cookies found in file")

    set_cookie_jar(session, account, cookies)
    account.gptk_session_state = None
    account.updated_at = utc_now()
    session.commit()
    return CookieImportResponse(account_id=account_id, cookies_imported=len(cookies))


@router.post("/{account_id}/credentials/cookies/paste", response_model=CookieImportResponse)
def paste_cookie_string(
    account_id: str,
    payload: SetCookiesPasteRequest,
    session: Session = Depends(get_session),
) -> CookieImportResponse:
    account = _require_account(session, account_id)
    cookies = parse_cookie_string(payload.cookie_string)
    if not cookies:
        raise HTTPException(status_code=400, detail="Invalid cookie string")

    set_cookie_jar(session, account, cookies)
    account.gptk_session_state = None
    account.updated_at = utc_now()
    session.commit()
    return CookieImportResponse(account_id=account_id, cookies_imported=len(cookies))


@router.post("/{account_id}/session/refresh", response_model=SessionRefreshResponse)
def refresh_session(
    account_id: str,
    payload: SessionRefreshRequest,
    session: Session = Depends(get_session),
) -> SessionRefreshResponse:
    account = _require_account(session, account_id)
    try:
        service = GptkService(session, account)
        state = service.refresh_session(source_path=payload.source_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SessionRefreshResponse(account_id=account_id, session_state=state)
