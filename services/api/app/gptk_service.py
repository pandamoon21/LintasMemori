from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from .auth_store import get_cookie_jar, get_session_state, set_session_state
from .config import settings
from .gphotos_rpc import GPhotosRpcClient
from .gptk_ops import execute_operation
from .models import Account


@dataclass
class GptkCallResult:
    data: Any
    raw_data: Any
    session_state: dict[str, Any]
    rpcid: str


class GptkService:
    def __init__(self, session: Session, account: Account) -> None:
        self.session = session
        self.account = account

    def _client(self) -> GPhotosRpcClient:
        cookie_jar = get_cookie_jar(self.session, self.account)
        if not cookie_jar:
            raise RuntimeError("No cookie credential found for account")
        return GPhotosRpcClient(
            cookie_jar=cookie_jar,
            max_retries=settings.rpc_max_retries,
            retry_base_delay_ms=settings.rpc_retry_base_delay_ms,
        )

    def call(self, operation: str, params: dict[str, Any]) -> GptkCallResult:
        client = self._client()
        current_state = get_session_state(self.session, self.account)
        result = execute_operation(client=client, operation=operation, params=params, session_state=current_state)
        session_state = result.get("session_state") or current_state
        if isinstance(session_state, dict):
            set_session_state(self.session, self.account, session_state)
            self.session.commit()
        return GptkCallResult(
            data=result.get("data"),
            raw_data=result.get("raw_data"),
            session_state=session_state,
            rpcid=str(result.get("rpcid")),
        )

    def refresh_session(self, source_path: str = "/") -> dict[str, Any]:
        client = self._client()
        state = client.bootstrap_session(source_path=source_path)
        set_session_state(self.session, self.account, state)
        self.session.commit()
        return state
