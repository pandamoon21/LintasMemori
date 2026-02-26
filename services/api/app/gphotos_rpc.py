from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests


@dataclass
class RpcSession:
    account: Optional[str]
    f_sid: str
    bl: str
    path: str
    at: str
    rapt: Optional[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "account": self.account,
            "fSid": self.f_sid,
            "bl": self.bl,
            "path": self.path,
            "at": self.at,
            "rapt": self.rapt,
        }


def cookie_header(cookie_jar: list[dict[str, Any]]) -> str:
    return "; ".join([f"{item.get('name')}={item.get('value')}" for item in cookie_jar if item.get("name")])


def _extract_wiz_value(html: str, key: str) -> Optional[str]:
    escaped = re.escape(key)
    match = re.search(rf'"{escaped}":"([^\"]+)"', html)
    if not match:
        return None
    value = match.group(1)
    return value.replace("\\u003d", "=").replace("\\u0026", "&").replace("\\/", "/")


def parse_wrb_payload(response_body: str) -> Any:
    json_line = None
    for line in response_body.split("\n"):
        candidate = line.strip()
        if "wrb.fr" in candidate:
            json_line = candidate
            break

    if not json_line:
        raise RuntimeError("No wrb.fr envelope found")

    parsed = json.loads(json_line)
    payload = parsed[0][2] if parsed and parsed[0] and len(parsed[0]) > 2 else None
    if not payload:
        raise RuntimeError("Missing payload in wrb.fr envelope")
    return json.loads(payload)


class GPhotosRpcClient:
    def __init__(
        self,
        cookie_jar: list[dict[str, Any]],
        max_retries: int = 3,
        retry_base_delay_ms: int = 1500,
        timeout_seconds: int = 120,
    ) -> None:
        self.cookie_jar = cookie_jar
        self.max_retries = max_retries
        self.retry_base_delay_ms = retry_base_delay_ms
        self.timeout_seconds = timeout_seconds

    def bootstrap_session(self, source_path: str = "/") -> dict[str, Any]:
        if not self.cookie_jar:
            raise RuntimeError("cookie jar is empty")

        response = requests.get(
            f"https://photos.google.com{source_path}",
            headers={"Cookie": cookie_header(self.cookie_jar)},
            timeout=60,
            allow_redirects=True,
        )
        response.raise_for_status()
        html = response.text

        session = RpcSession(
            account=_extract_wiz_value(html, "oPEP7c"),
            f_sid=_extract_wiz_value(html, "FdrFJe") or "",
            bl=_extract_wiz_value(html, "cfb2h") or "",
            path=_extract_wiz_value(html, "eptZe") or "/_/PhotosUi/",
            at=_extract_wiz_value(html, "SNlM0e") or "",
            rapt=_extract_wiz_value(html, "Dbw5Ud"),
        )

        if not session.f_sid or not session.bl or not session.at:
            raise RuntimeError("Unable to extract required session fields (f.sid/bl/at)")

        return session.as_dict()

    def execute_rpc(
        self,
        session_state: dict[str, Any],
        rpcid: str,
        request_data: Any,
        source_path: str = "/",
    ) -> dict[str, Any]:
        if not rpcid:
            raise ValueError("rpcid is required")

        current_session = dict(session_state)

        for attempt in range(1, self.max_retries + 1):
            try:
                data = self._execute_once(current_session, rpcid, request_data, source_path)
                return {"data": data, "session": current_session}
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else 0
                if status in {401, 403}:
                    current_session = self.bootstrap_session(source_path)
                if attempt >= self.max_retries:
                    raise
            except Exception:
                if attempt >= self.max_retries:
                    raise

            time.sleep((self.retry_base_delay_ms * attempt) / 1000.0)

        raise RuntimeError("RPC failed after retries")

    def _execute_once(
        self,
        session_state: dict[str, Any],
        rpcid: str,
        request_data: Any,
        source_path: str,
    ) -> Any:
        f_sid = session_state.get("fSid")
        bl = session_state.get("bl")
        path = session_state.get("path")
        at = session_state.get("at")
        rapt = session_state.get("rapt")

        if not all([f_sid, bl, path, at]):
            raise RuntimeError("session state missing fSid/bl/path/at")

        wrapped_data = [[[rpcid, json.dumps(request_data), None, "generic"]]]
        body = f"f.req={requests.utils.quote(json.dumps(wrapped_data))}&at={requests.utils.quote(str(at))}&"

        params: dict[str, str] = {
            "rpcids": rpcid,
            "source-path": source_path,
            "f.sid": str(f_sid),
            "bl": str(bl),
            "pageId": "none",
            "rt": "c",
        }
        if rapt:
            params["rapt"] = str(rapt)

        query = "&".join([f"{k}={requests.utils.quote(v)}" for k, v in params.items()])
        url = f"https://photos.google.com{path}data/batchexecute?{query}"

        response = requests.post(
            url,
            headers={
                "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Cookie": cookie_header(self.cookie_jar),
            },
            data=body,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        if not response.text:
            raise RuntimeError("Empty response body")

        return parse_wrb_payload(response.text)
