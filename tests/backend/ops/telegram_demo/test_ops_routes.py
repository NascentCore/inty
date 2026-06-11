"""Ops mounts telegram-demo onboard page."""

from __future__ import annotations

from fastapi.routing import APIRoute

from backend.ops.main import app


def test_ops_mounts_telegram_demo_page() -> None:
    paths = [
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
    ]
    assert "/telegram-demo" in paths
