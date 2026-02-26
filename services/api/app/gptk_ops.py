from __future__ import annotations

from typing import Any

from .adapters.gptk_methods import METHODS, resolve_method
from .gphotos_rpc import GPhotosRpcClient
from .gptk_parser import parse_response


def list_operations() -> list[str]:
    return sorted([f"gptk.{name}" for name in METHODS])


def execute_operation(
    client: GPhotosRpcClient,
    operation: str,
    params: dict[str, Any],
    session_state: dict[str, Any],
) -> dict[str, Any]:
    normalized = operation.replace("gptk.", "")

    if normalized == "rpc_execute":
        rpcid = params.get("rpcid")
        request_data = params.get("requestData")
        source_path = params.get("sourcePath", "/")
        if not rpcid:
            raise ValueError("rpcid is required for gptk.rpc_execute")
        if request_data is None:
            raise ValueError("requestData is required for gptk.rpc_execute")
    else:
        method = resolve_method(normalized)
        rpcid = method.rpcid
        request_data = method.request_builder(params)
        source_path = params.get("sourcePath", method.source_path_hint)

    current_session = dict(session_state)
    if params.get("forceBootstrap") or not current_session.get("fSid"):
        current_session = client.bootstrap_session(source_path)

    rpc_result = client.execute_rpc(
        session_state=current_session,
        rpcid=rpcid,
        request_data=request_data,
        source_path=source_path,
    )

    return {
        "rpcid": rpcid,
        "data": parse_response(rpcid, rpc_result.get("data")),
        "raw_data": rpc_result.get("data"),
        "session_state": rpc_result.get("session") or current_session,
    }
