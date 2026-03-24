from __future__ import annotations

import cyclopts

from .runtime.admin_replay import replay_events
from .runtime.app_context import build_app_context
from .runtime.inbound_server import run_inbound_server
from .runtime.scheduler_server import run_scheduler_server
from .settings import get_settings

app = cyclopts.App(name="companion")
serve_app = cyclopts.App(name="serve")
admin_app = cyclopts.App(name="admin")


@serve_app.command(name="inbound")
def serve_inbound(
    once: bool = False,
) -> None:
    ctx = build_app_context(settings=get_settings())
    run_inbound_server(ctx=ctx, once=once)


@serve_app.command(name="scheduler")
def serve_scheduler(
    once: bool = False,
) -> None:
    ctx = build_app_context(settings=get_settings())
    run_scheduler_server(ctx=ctx, once=once)


@admin_app.command(name="replay")
def admin_replay(
    since_minutes: int = 60,
    user_id: str | None = None,
    limit: int = 50,
) -> None:
    ctx = build_app_context(settings=get_settings())
    lines = replay_events(
        ctx=ctx,
        since_minutes=since_minutes,
        user_id=user_id,
        limit=limit,
    )
    for line in lines:
        print(line)


app.command(serve_app, name="serve")
app.command(admin_app, name="admin")


if __name__ == "__main__":
    app()
