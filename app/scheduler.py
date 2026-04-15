from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.time import deployment_tz, utc_now
from app.services import auto_advance_due_episodes


def run_scheduler_cycle() -> int:
    db = SessionLocal()
    try:
        return auto_advance_due_episodes(db, utc_now())
    finally:
        db.close()


def _seconds_until_next_run(now: datetime) -> float:
    local_now = now.astimezone(deployment_tz())
    target = local_now.replace(hour=0, minute=5, second=0, microsecond=0)
    if local_now >= target:
        target = target + timedelta(days=1)
    return max((target - local_now).total_seconds(), 0.0)


def start_scheduler(stop_event: threading.Event | None = None) -> threading.Thread | None:
    if not settings.enable_scheduler:
        return None

    stop = stop_event or threading.Event()

    def loop() -> None:
        while not stop.is_set():
            sleep_for = _seconds_until_next_run(datetime.now(timezone.utc))
            if stop.wait(timeout=sleep_for):
                break
            run_scheduler_cycle()

    thread = threading.Thread(target=loop, name="eczema-scheduler", daemon=True)
    thread.start()
    return thread
