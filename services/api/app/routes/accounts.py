from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..cookies import parse_netscape_cookie_file
from ..database import get_session
from ..models import Account
from ..schemas import AccountCreate, AccountOut, CookieImportResponse, SetGpmcAuthRequest
from ..serializers import account_to_out

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    return [account_to_out(row) for row in rows]


@router.post("/{account_id}/gpmc-auth", response_model=AccountOut)
def set_gpmc_auth(account_id: str, payload: SetGpmcAuthRequest, session: Session = Depends(get_session)) -> AccountOut:
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    account.gpmc_auth_data = payload.auth_data
    account.updated_at = utc_now()
    session.commit()
    session.refresh(account)
    return account_to_out(account)


@router.post("/{account_id}/gptk-cookies/import", response_model=CookieImportResponse)
async def import_gptk_cookies(account_id: str, file: UploadFile = File(...), session: Session = Depends(get_session)) -> CookieImportResponse:
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    data = await file.read()
    try:
        raw = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Cookie file must be UTF-8 text") from exc

    cookies = parse_netscape_cookie_file(raw)
    if not cookies:
        raise HTTPException(status_code=400, detail="No valid cookies found in file")

    account.gptk_cookie_jar = cookies
    account.gptk_session_state = None
    account.updated_at = utc_now()
    session.commit()

    return CookieImportResponse(account_id=account_id, cookies_imported=len(cookies))
