"""Workspace 下各文件路径。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    """指向同一 workspace 根目录下的标准文件。"""

    root: Path

    @property
    def identity(self) -> Path:
        return self.root / "IDENTITY.md"

    @property
    def soul(self) -> Path:
        return self.root / "SOUL.md"

    @property
    def user_md(self) -> Path:
        return self.root / "USER.md"

    @property
    def memory_md(self) -> Path:
        return self.root / "MEMORY.md"

    @property
    def transcript(self) -> Path:
        return self.root / "transcript.jsonl"

    @property
    def context_json(self) -> Path:
        return self.root / "context.json"

    @property
    def memory_dir(self) -> Path:
        return self.root / "memory"
