from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .app_context import AppContext


def replay_events(
    *,
    ctx: AppContext,
    since_minutes: int,
    user_id: str | None,
    limit: int,
) -> list[str]:
    if since_minutes <= 0:
        raise ValueError("since_minutes must be > 0")
    if limit <= 0:
        raise ValueError("limit must be > 0")
    since = datetime.now(timezone.utc).replace(microsecond=0)
    since = since - timedelta(minutes=since_minutes)
    if user_id:
        events = ctx.events_repo.list_events_by_user(
            user_id=user_id, limit=limit
        )
    else:
        events = ctx.events_repo.list_events_since(since=since, limit=limit)
    lines: list[str] = []
    for event in events:
        lines.append(
            f"{event.timestamp.isoformat()} event_id={event.event_id} "
            f"user_id={event.user_id} channel={event.channel.value} "
            f"direction={event.direction.value} content={event.content}"
        )
    return lines
