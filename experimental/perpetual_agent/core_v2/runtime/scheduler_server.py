from __future__ import annotations

import time
from datetime import datetime, timezone

from .app_context import AppContext


def run_scheduler_server(*, ctx: AppContext, once: bool) -> None:
    while True:
        now = datetime.now(timezone.utc)
        executed = ctx.orchestrator.run_scheduler_once(now=now)
        if once:
            return
        if executed == 0:
            time.sleep(ctx.settings.scheduler_idle_sleep_seconds)
