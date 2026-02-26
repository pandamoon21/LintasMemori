from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT / ".runtime"
LOGS_DIR = RUNTIME_DIR / "logs"
STATE_FILE = RUNTIME_DIR / "processes_py.json"

API_DIR = ROOT / "services" / "api"
WEB_DIR = ROOT / "apps" / "web"
WORKER_SCRIPT = ROOT / "workers" / "python" / "worker.py"
DATA_DIR = ROOT / "data"

VENV_DIR = API_DIR / ".venv"
VENV_PY = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"[start_all] $ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def _python_version(python_exec: str) -> tuple[int, int]:
    output = subprocess.check_output(
        [python_exec, "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()
    major, minor = output.split(".")
    return int(major), int(minor)


def _resolve_python_runtime() -> str:
    env_python = os.getenv("LM_PYTHON")
    if env_python:
        major, minor = _python_version(env_python)
        if (major, minor) >= (3, 9):
            return env_python
        raise RuntimeError(f"LM_PYTHON points to Python {major}.{minor}. Require Python 3.9+")

    candidates: list[str] = []
    if sys.version_info >= (3, 9):
        candidates.append(sys.executable)

    if os.name == "nt":
        try:
            resolved = subprocess.check_output(
                ["py", "-3.11", "-c", "import sys; print(sys.executable)"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            if resolved:
                candidates.append(resolved)
        except Exception:
            pass

    for name in ("python3.11", "python3", "python"):
        path = shutil.which(name)
        if path:
            candidates.append(path)

    for candidate in dict.fromkeys(candidates):
        try:
            major, minor = _python_version(candidate)
        except Exception:
            continue
        if (major, minor) >= (3, 9):
            return candidate

    raise RuntimeError(
        "Python 3.9+ not found. Install Python 3.9 or newer and retry, "
        "or set LM_PYTHON to a valid Python executable."
    )


def _ensure_venv(base_python: str) -> None:
    if VENV_PY.exists():
        major, minor = _python_version(str(VENV_PY))
        if (major, minor) >= (3, 9):
            return
        print(f"[start_all] Existing venv uses Python {major}.{minor}; recreating for Python 3.9+")
        shutil.rmtree(VENV_DIR, ignore_errors=True)

    print(f"[start_all] Creating virtualenv in services/api/.venv using {base_python}")
    _run([base_python, "-m", "venv", str(VENV_DIR)])


def _ensure_api_deps(skip_install: bool) -> None:
    if skip_install:
        return
    _run([str(VENV_PY), "-m", "pip", "install", "--upgrade", "pip"])
    _run([str(VENV_PY), "-m", "pip", "install", "-e", "."], cwd=API_DIR)


def _ensure_web_dist(skip_install: bool, skip_web_build: bool, rebuild_web: bool) -> None:
    if skip_web_build:
        return
    dist_dir = WEB_DIR / "dist"
    if dist_dir.exists() and any(dist_dir.iterdir()) and not rebuild_web:
        index_html = dist_dir / "index.html"
        if index_html.exists():
            content = index_html.read_text(encoding="utf-8", errors="ignore")
            if "/app/assets/" in content:
                return
            print("[start_all] Existing dist uses old base path. Rebuilding web bundle...")
        else:
            return

    npm = shutil.which("npm")
    if not npm:
        print("[start_all] WARNING: npm not found; skipping web build. /app route may be unavailable.")
        return

    if not skip_install and not (WEB_DIR / "node_modules").exists():
        _run([npm, "install"], cwd=WEB_DIR)
    _run([npm, "run", "build"], cwd=WEB_DIR)


def _wait_health(url: str, timeout_seconds: int = 40) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=3) as response:
                if 200 <= response.status < 500:
                    return True
        except URLError:
            time.sleep(0.6)
        except Exception:
            time.sleep(0.6)
    return False


def _start_process(name: str, cmd: list[str], cwd: Path, env: dict[str, str]) -> dict[str, str | int]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"{name}.log"
    with log_path.open("a", encoding="utf-8") as log_file:
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env,
            creationflags=creationflags,
        )
    print(f"[start_all] started {name} (pid={proc.pid})")
    return {
        "name": name,
        "pid": proc.pid,
        "cmd": cmd,
        "cwd": str(cwd),
        "log": str(log_path),
        "started_at": _now_iso(),
    }


def _stop_existing() -> None:
    if not STATE_FILE.exists():
        return
    print("[start_all] Existing state file detected. Stopping previous processes first...")
    subprocess.run([sys.executable, str(ROOT / "stop_all.py")], check=False)


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.6)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start LintasMemori stack (api + worker)")
    parser.add_argument("--prepare-only", action="store_true", help="Only install/build dependencies")
    parser.add_argument("--skip-install", action="store_true", help="Skip pip/npm install steps")
    parser.add_argument("--skip-web-build", action="store_true", help="Skip React build step")
    parser.add_argument("--rebuild-web", action="store_true", help="Force rebuild React dist")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_port = int(os.getenv("LM_API_PORT", "1453"))

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    _stop_existing()
    if _is_port_in_use(api_port):
        raise RuntimeError(
            f"Port {api_port} is already in use by another process. "
            "Stop that process first, then rerun start_all.py."
        )

    base_python = _resolve_python_runtime()
    major, minor = _python_version(base_python)
    if (major, minor) < (3, 11):
        print(f"[start_all] INFO: running with Python {major}.{minor}. Recommended: Python 3.11+")
    _ensure_venv(base_python=base_python)
    _ensure_api_deps(skip_install=args.skip_install)
    _ensure_web_dist(skip_install=args.skip_install, skip_web_build=args.skip_web_build, rebuild_web=args.rebuild_web)

    if args.prepare_only:
        print("[start_all] Prepare complete. No process started (--prepare-only).")
        return 0

    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("LM_STATIC_DIR", str(WEB_DIR / "dist"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    env.setdefault("LM_DB_PATH", str(DATA_DIR / "lintasmemori.db"))

    processes: list[dict[str, str | int]] = []
    processes.append(
        _start_process(
            "api",
            [str(VENV_PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(api_port)],
            cwd=API_DIR,
            env=env,
        )
    )
    processes.append(
        _start_process(
            "worker",
            [str(VENV_PY), str(WORKER_SCRIPT)],
            cwd=API_DIR,
            env=env,
        )
    )

    state = {
        "repo_root": str(ROOT),
        "started_at": _now_iso(),
        "processes": processes,
    }
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    healthy = _wait_health(f"http://127.0.0.1:{api_port}/health", timeout_seconds=45)
    if healthy:
        print(f"[start_all] API healthy: http://127.0.0.1:{api_port}/health")
    else:
        print("[start_all] WARNING: API health check timed out")

    print("[start_all] Started services:")
    print(f"  API: http://127.0.0.1:{api_port}")
    print(f"  UI:  http://127.0.0.1:{api_port}/app")
    print(f"  state: {STATE_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
