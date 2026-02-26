from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: str = os.getenv("LM_DB_PATH", str(Path(__file__).resolve().parents[1] / "lintasmemori.db"))
    sidecar_base_url: str = os.getenv("LM_SIDECAR_URL", "http://localhost:8787")
    poll_interval_seconds: float = float(os.getenv("LM_POLL_INTERVAL_SECONDS", "1.0"))


settings = Settings()
