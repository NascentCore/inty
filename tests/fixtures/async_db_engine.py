"""Shared async SQLAlchemy engine reset for DB integration tests."""

from __future__ import annotations

import pytest

from app.db.session import async_engine
from app.models.registry import load_model_modules


@pytest.fixture(autouse=True)
async def _dispose_async_engine() -> None:
    load_model_modules()
    await async_engine.dispose()
    yield
    await async_engine.dispose()
