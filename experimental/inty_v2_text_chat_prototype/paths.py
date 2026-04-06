"""Re-export WorkspacePaths from kernel with prototype default prefix."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.agentic_kernel.companion.workspace import (
    WorkspacePaths as _KernelWorkspacePaths,
    is_workspace_initialized,  # noqa: F401
    needs_startup_profile_inquiry,  # noqa: F401
)


@dataclass(frozen=True)
class WorkspacePaths(_KernelWorkspacePaths):
    """Prototype WorkspacePaths: uses .inty_v2 prefix for state files by default."""

    state_file_prefix: str = ".inty_v2"
