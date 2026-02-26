from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from .models import Account, CredentialCookies, CredentialGpmc, GPhotosSessionState


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_gpmc_auth(session: Session, account: Account) -> Optional[str]:
    cred = session.query(CredentialGpmc).filter(CredentialGpmc.account_id == account.id).one_or_none()
    if cred and cred.auth_data:
        return cred.auth_data
    return account.gpmc_auth_data


def set_gpmc_auth(session: Session, account: Account, auth_data: str) -> None:
    cred = session.query(CredentialGpmc).filter(CredentialGpmc.account_id == account.id).one_or_none()
    if cred is None:
        cred = CredentialGpmc(account_id=account.id, auth_data=auth_data)
        session.add(cred)
    else:
        cred.auth_data = auth_data
        cred.updated_at = utc_now()

    account.gpmc_auth_data = auth_data
    account.updated_at = utc_now()


def get_cookie_jar(session: Session, account: Account) -> list[dict[str, Any]]:
    cred = session.query(CredentialCookies).filter(CredentialCookies.account_id == account.id).one_or_none()
    if cred and isinstance(cred.cookie_jar, list):
        return cred.cookie_jar
    if isinstance(account.gptk_cookie_jar, list):
        return account.gptk_cookie_jar
    return []


def set_cookie_jar(session: Session, account: Account, cookie_jar: list[dict[str, Any]]) -> None:
    cred = session.query(CredentialCookies).filter(CredentialCookies.account_id == account.id).one_or_none()
    if cred is None:
        cred = CredentialCookies(account_id=account.id, cookie_jar=cookie_jar)
        session.add(cred)
    else:
        cred.cookie_jar = cookie_jar
        cred.updated_at = utc_now()

    account.gptk_cookie_jar = cookie_jar
    account.updated_at = utc_now()


def get_session_state(session: Session, account: Account) -> dict[str, Any]:
    state_row = session.query(GPhotosSessionState).filter(GPhotosSessionState.account_id == account.id).one_or_none()
    if state_row and isinstance(state_row.session_state, dict):
        return state_row.session_state
    if isinstance(account.gptk_session_state, dict):
        return account.gptk_session_state
    return {}


def set_session_state(session: Session, account: Account, state: dict[str, Any]) -> None:
    state_row = session.query(GPhotosSessionState).filter(GPhotosSessionState.account_id == account.id).one_or_none()
    if state_row is None:
        state_row = GPhotosSessionState(account_id=account.id, session_state=state)
        session.add(state_row)
    else:
        state_row.session_state = state
        state_row.updated_at = utc_now()

    account.gptk_session_state = state
    account.updated_at = utc_now()
