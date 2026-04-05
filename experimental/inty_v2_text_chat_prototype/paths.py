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
    def agents_md(self) -> Path:
        return self.root / "AGENTS.md"

    @property
    def heartbeat_md(self) -> Path:
        return self.root / "HEARTBEAT.md"

    @property
    def tools_md(self) -> Path:
        return self.root / "TOOLS.md"

    @property
    def transcript(self) -> Path:
        return self.root / "transcript.jsonl"

    @property
    def context_json(self) -> Path:
        return self.root / "context.json"

    @property
    def memory_dir(self) -> Path:
        return self.root / "memory"

    @property
    def memory_daily_dir(self) -> Path:
        """逐条原始流水：memory/daily/YYYY-MM-DD.md"""
        return self.memory_dir / "daily"

    def memory_raw_diary(self, day: str) -> Path:
        """当日原始对话行（追加）。"""
        return self.memory_daily_dir / f"{day}.md"

    def memory_day_summary(self, day: str) -> Path:
        """当日总结性记忆（LLM 整文件覆盖）：memory/YYYY-MM-DD.md"""
        return self.memory_dir / f"{day}.md"

    @property
    def memory_pipeline_state_json(self) -> Path:
        """记忆管线累计轮次（用于按间隔跑当日总结 LLM）；与 transcript 同目录，不入版控时可随 workspace 忽略。"""
        return self.root / ".inty_v2_memory_pipeline.json"

    @property
    def schedule_queue_json(self) -> Path:
        """定时任务持久化队列。"""
        return self.root / ".inty_v2_schedule_tasks.json"
