from __future__ import annotations

from typing import Any

import requests

from .common import AdapterResult, ProgressFn
from .gptk_methods import resolve_method


def _bootstrap_session(sidecar_base_url: str, cookie_jar: list[dict[str, Any]], source_path: str | None = None) -> dict[str, Any]:
    response = requests.post(
        f"{sidecar_base_url.rstrip('/')}/api/session/bootstrap",
        json={"cookieJar": cookie_jar, "sourcePath": source_path or "/"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json().get("session", {})


def _execute_rpc(
    sidecar_base_url: str,
    cookie_jar: list[dict[str, Any]],
    current_session: dict[str, Any],
    rpcid: str,
    request_data: Any,
    source_path: str,
    progress: ProgressFn,
) -> tuple[dict[str, Any], dict[str, Any]]:
    response = requests.post(
        f"{sidecar_base_url.rstrip('/')}/api/rpc/execute",
        json={
            "cookieJar": cookie_jar,
            "session": current_session,
            "rpcid": rpcid,
            "requestData": request_data,
            "sourcePath": source_path,
        },
        timeout=120,
    )

    if response.status_code == 401:
        progress(0.7, "Session expired, attempting one refresh")
        current_session = _bootstrap_session(sidecar_base_url, cookie_jar, source_path)
        response = requests.post(
            f"{sidecar_base_url.rstrip('/')}/api/rpc/execute",
            json={
                "cookieJar": cookie_jar,
                "session": current_session,
                "rpcid": rpcid,
                "requestData": request_data,
                "sourcePath": source_path,
            },
            timeout=120,
        )

    response.raise_for_status()
    payload = response.json()
    return payload, payload.get("session") or current_session


def run(
    operation: str,
    params: dict[str, Any],
    cookie_jar: list[dict[str, Any]] | None,
    session_state: dict[str, Any] | None,
    sidecar_base_url: str,
    dry_run: bool,
    progress: ProgressFn,
) -> AdapterResult:
    op = operation.replace("gptk.", "")

    source_path = params.get("sourcePath", "/")
    resolved_operation = op

    if op == "rpc_execute":
        rpcid = params.get("rpcid")
        request_data = params.get("requestData")
        if not rpcid:
            raise ValueError("gptk.rpc_execute requires params.rpcid")
        if request_data is None:
            raise ValueError("gptk.rpc_execute requires params.requestData")
    else:
        method = resolve_method(op)
        rpcid = method.rpcid
        request_data = method.request_builder(params)
        source_path = params.get("sourcePath", method.source_path_hint)
        resolved_operation = method.operation

    if dry_run:
        return {
            "operation": resolved_operation,
            "rpcid": rpcid,
            "sourcePath": source_path,
            "request_preview": request_data,
        }

    if not cookie_jar:
        raise RuntimeError("GPTK cookie jar is missing for this account")

    current_session = session_state or {}
    if params.get("forceBootstrap") or not current_session.get("fSid"):
        progress(0.2, "Bootstrapping GPTK session")
        current_session = _bootstrap_session(sidecar_base_url, cookie_jar, source_path)

    progress(0.55, "Executing GPTK RPC")
    payload, refreshed_session = _execute_rpc(
        sidecar_base_url=sidecar_base_url,
        cookie_jar=cookie_jar,
        current_session=current_session,
        rpcid=rpcid,
        request_data=request_data,
        source_path=source_path,
        progress=progress,
    )
    progress(1.0, "GPTK RPC completed")

    return {
        "operation": resolved_operation,
        "rpcid": rpcid,
        "data": payload.get("data"),
        "session_state": refreshed_session,
    }
