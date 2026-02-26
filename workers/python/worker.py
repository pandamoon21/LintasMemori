from __future__ import annotations

import os
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "services" / "api"
if API_DIR.as_posix() not in sys.path:
    sys.path.insert(0, API_DIR.as_posix())

from app.database import engine, initialize_database  # noqa: E402
from app.job_executor import claim_jobs, execute_job  # noqa: E402

POLL_SECONDS = float(os.getenv("LM_WORKER_POLL_SECONDS", "1.0"))
MAX_WORKERS = int(os.getenv("LM_WORKER_MAX_WORKERS", "4"))
MAX_PER_ACCOUNT = int(os.getenv("LM_WORKER_MAX_PER_ACCOUNT", "1"))


def _run_job(job_id: str) -> None:
    with Session(engine) as session:
        execute_job(session, job_id)


def main() -> None:
    initialize_database()
    print(f"[worker] started max_workers={MAX_WORKERS}, max_per_account={MAX_PER_ACCOUNT}")

    in_flight: dict[str, tuple[str, Future[None]]] = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        while True:
            try:
                finished_ids = [job_id for job_id, (_, future) in in_flight.items() if future.done()]
                for job_id in finished_ids:
                    account_id, future = in_flight.pop(job_id)
                    try:
                        future.result()
                    except Exception as exc:  # noqa: BLE001
                        print(f"[worker] job {job_id} ({account_id}) crashed: {exc}")

                available_slots = MAX_WORKERS - len(in_flight)
                if available_slots > 0:
                    in_flight_accounts: dict[str, int] = {}
                    for _, (account_id, _) in in_flight.items():
                        in_flight_accounts[account_id] = in_flight_accounts.get(account_id, 0) + 1

                    with Session(engine) as session:
                        claimed = claim_jobs(
                            session=session,
                            limit=available_slots,
                            max_per_account=MAX_PER_ACCOUNT,
                            in_flight_accounts=in_flight_accounts,
                        )

                    for job in claimed:
                        print(f"[worker] executing {job.id} ({job.account_id}, {job.provider}:{job.operation})")
                        future = pool.submit(_run_job, job.id)
                        in_flight[job.id] = (job.account_id, future)

                time.sleep(POLL_SECONDS)
            except Exception as exc:  # noqa: BLE001
                print(f"[worker] error: {exc}")
                time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
