"""DSN gate string for ``get_memory_store`` in companion harness tests.

Tests that use the process-local MemoryStore registry assume repo-root ``config.yaml``
provides a non-empty ``database.url`` (same as production ``CompanionManager`` wiring).
"""

from __future__ import annotations

import pytest

from app.core.companion_harness.memory.memory_registry import (
    MEMORY_STORE_REGISTRY_REQUIRES_DSN,
)
from app.core.config import global_config_loaded_from_config_yaml


def companion_memory_registry_dsn() -> str:
    url = (global_config_loaded_from_config_yaml.database.url or "").strip()
    if not url:
        pytest.fail(MEMORY_STORE_REGISTRY_REQUIRES_DSN)
    return url
