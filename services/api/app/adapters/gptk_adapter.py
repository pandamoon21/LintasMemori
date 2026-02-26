from __future__ import annotations

from typing import Any

from .common import AdapterResult, ProgressFn
from .gptk_methods import resolve_method
from ..config import settings
from ..gphotos_rpc import GPhotosRpcClient
from ..gptk_parser import parse_response


def run(
    operation: str,
    params: dict[str, Any],
    cookie_jar: list[dict[str, Any]] | None,
    session_state: dict[str, Any] | None,
    _sidecar_base_url: str | None,
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

    client = GPhotosRpcClient(
        cookie_jar=cookie_jar,
        max_retries=settings.rpc_max_retries,
        retry_base_delay_ms=settings.rpc_retry_base_delay_ms,
    )

    current_session = dict(session_state or {})
    if params.get("forceBootstrap") or not current_session.get("fSid"):
        progress(0.2, "Bootstrapping GPTK session")
        current_session = client.bootstrap_session(source_path)

    progress(0.55, f"Executing GPTK RPC {rpcid}")
    rpc_result = client.execute_rpc(
        session_state=current_session,
        rpcid=rpcid,
        request_data=request_data,
        source_path=source_path,
    )
    parsed_data = parse_response(rpcid, rpc_result.get("data"))

    progress(1.0, "GPTK RPC completed")

    return {
        "operation": resolved_operation,
        "rpcid": rpcid,
        "data": parsed_data,
        "raw_data": rpc_result.get("data"),
        "session_state": rpc_result.get("session") or current_session,
    }
