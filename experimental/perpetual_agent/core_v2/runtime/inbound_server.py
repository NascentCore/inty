from __future__ import annotations

import random
import time

from ..services.retry_policy import RetryPolicy
from .app_context import AppContext


def run_inbound_server(*, ctx: AppContext, once: bool) -> None:
    owner_id = f"pid-{time.time_ns()}-{random.randint(1000, 9999)}"
    acquired = ctx.lease_repo.try_acquire_or_renew(
        lease_key=ctx.settings.lease_key_telegram_inbound,
        owner_id=owner_id,
        ttl_seconds=ctx.settings.lease_ttl_seconds,
    )
    if not acquired:
        raise RuntimeError(
            "telegram inbound consumer lease is held by another owner"
        )

    retry = RetryPolicy(
        max_attempts=ctx.settings.retry_max_attempts,
        base_delay_seconds=ctx.settings.retry_base_delay_seconds,
    )
    try:
        while True:
            applied_update_id = ctx.orchestrator.get_last_applied_update_id(
                cursor_key=ctx.settings.cursor_key_telegram_update
            )
            poll_offset = (
                None if applied_update_id is None else (applied_update_id + 1)
            )
            envelopes, _next_offset = retry.execute(
                lambda: ctx.telegram_adapter.poll_updates(offset=poll_offset)
            )
            processed_any = False
            for envelope in envelopes:
                result = ctx.orchestrator.process_inbound_telegram(
                    envelope=envelope
                )
                if result.should_advance_cursor:
                    ctx.orchestrator.advance_applied_update_id(
                        cursor_key=ctx.settings.cursor_key_telegram_update,
                        update_id=envelope.update_id,
                    )
                if result.processed:
                    processed_any = True
            ctx.lease_repo.try_acquire_or_renew(
                lease_key=ctx.settings.lease_key_telegram_inbound,
                owner_id=owner_id,
                ttl_seconds=ctx.settings.lease_ttl_seconds,
            )
            if once:
                return
            if not processed_any:
                time.sleep(ctx.settings.inbound_idle_sleep_seconds)
    finally:
        ctx.lease_repo.release_if_owner(
            lease_key=ctx.settings.lease_key_telegram_inbound,
            owner_id=owner_id,
        )
