"""Runtime build identity from environment (VCS revision, optional build time).

CI and Docker should set INTY_VCS_REVISION (and optionally INTY_BUILD_TIME, INTY_VCS_DIRTY).
Falls back to common CI variables when INTY_* is unset.
"""

from __future__ import annotations

import os

_VCS_REVISION_ENV_KEYS = (
    "INTY_VCS_REVISION",
    "GITHUB_SHA",
    "SOURCE_VERSION",
    "COMMIT_SHA",
    "GIT_COMMIT",
)


def vcs_revision() -> str:
    for key in _VCS_REVISION_ENV_KEYS:
        raw = os.environ.get(key, "").strip()
        if raw:
            return raw
    return ""


def vcs_dirty() -> bool:
    raw = os.environ.get("INTY_VCS_DIRTY", "").strip().lower()
    return raw in ("1", "true", "yes")


def build_time_utc() -> str:
    return os.environ.get("INTY_BUILD_TIME", "").strip()
