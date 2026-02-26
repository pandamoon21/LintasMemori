from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: str = os.getenv("LM_DB_PATH", str(Path(__file__).resolve().parents[1] / "lintasmemori.db"))
    poll_interval_seconds: float = float(os.getenv("LM_POLL_INTERVAL_SECONDS", "1.0"))
    preview_ttl_minutes: int = int(os.getenv("LM_PREVIEW_TTL_MINUTES", "30"))
    rpc_max_retries: int = int(os.getenv("LM_RPC_MAX_RETRIES", "3"))
    rpc_retry_base_delay_ms: int = int(os.getenv("LM_RPC_RETRY_BASE_DELAY_MS", "1500"))
    static_dir: str = os.getenv("LM_STATIC_DIR", str(Path(__file__).resolve().parents[2] / ".." / "apps" / "web" / "dist"))


settings = Settings()
