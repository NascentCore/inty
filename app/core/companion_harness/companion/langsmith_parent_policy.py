"""Pure policy for whether companion turns create a LangSmith parent ``RunTree``.

The predicate is split so tests and callers can evaluate rules without importing
``global_config``; ``companion_turn_langsmith_parent_enabled_from_app_config`` is
the production entry that reads app YAML + process environment.
"""

from __future__ import annotations

import os

from app.core.config import (
    _langsmith_tracing_v2_enabled,
    global_config_loaded_from_config_yaml,
)
from app.utils.config import Environment


def companion_langsmith_parent_run_allowed(
    *,
    under_pytest: bool,
    app_environment: Environment,
    langsmith_v2_enabled_in_config: bool,
    langsmith_tracing_v2_env_raw: str,
) -> bool:
    """Return whether companion kernel may create a LangSmith parent run (explicit inputs only)."""
    if under_pytest:
        return False
    if app_environment == Environment.TEST:
        return False
    if not langsmith_v2_enabled_in_config:
        return False
    if langsmith_tracing_v2_env_raw.strip().lower() != "true":
        return False
    return True


def companion_turn_langsmith_parent_enabled_from_app_config() -> bool:
    """Production gate: reads ``config.yaml`` and ``LANGSMITH_TRACING_V2`` / pytest marker."""
    return companion_langsmith_parent_run_allowed(
        under_pytest=bool(os.environ.get("PYTEST_CURRENT_TEST")),
        app_environment=global_config_loaded_from_config_yaml.app.environment,
        langsmith_v2_enabled_in_config=_langsmith_tracing_v2_enabled(
            global_config_loaded_from_config_yaml
        ),
        langsmith_tracing_v2_env_raw=os.environ.get("LANGSMITH_TRACING_V2", ""),
    )
