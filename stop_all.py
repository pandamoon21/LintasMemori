from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / ".runtime" / "processes_py.json"


def _is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, check=False)
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _stop_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False)
        return

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return

    deadline = time.time() + 8
    while time.time() < deadline:
        if not _is_pid_running(pid):
            return
        time.sleep(0.3)

    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def main() -> int:
    if not STATE_FILE.exists():
        print("[stop_all] No process state file found.")
        return 0

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        STATE_FILE.unlink(missing_ok=True)
        print("[stop_all] Invalid state file removed.")
        return 0

    processes = data.get("processes", []) if isinstance(data, dict) else []
    if not isinstance(processes, list):
        processes = []

    for proc in processes:
        name = str(proc.get("name", "process"))
        pid = int(proc.get("pid", 0) or 0)
        if pid <= 0:
            continue
        if not _is_pid_running(pid):
            print(f"[stop_all] Already stopped: {name} (pid={pid})")
            continue
        _stop_pid(pid)
        print(f"[stop_all] Stopped: {name} (pid={pid})")

    STATE_FILE.unlink(missing_ok=True)
    print("[stop_all] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
