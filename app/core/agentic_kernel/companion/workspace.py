"""Companion workspace: 路径定义与初始化状态检查。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from .file_store import read_text
from .memory_store import MemoryStore

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def load_workspace_seed_text(filename: str) -> str:
    path = _TEMPLATES_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"missing companion workspace seed template: {path}")
    return read_text(path).rstrip() + "\n"


@dataclass(frozen=True)
class WorkspacePaths:
    """指向同一 workspace 根目录下的标准文件。"""

    root: Path
    # 状态文件前缀, prototype 传 ".inty_v2" 以兼容已有 workspace
    state_file_prefix: str = ".companion"

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
    def ai_private_md(self) -> Path:
        return self.root / "ai_private.md"

    @property
    def ai_private_jsonl(self) -> Path:
        return self.root / "ai_private.jsonl"

    @property
    def context_json(self) -> Path:
        return self.root / "context.json"

    @property
    def memory_dir(self) -> Path:
        return self.root / "memory"

    @property
    def memory_daily_dir(self) -> Path:
        return self.memory_dir / "daily"

    def memory_raw_diary(self, day: str) -> Path:
        return self.memory_daily_dir / f"{day}.md"

    def memory_day_summary(self, day: str) -> Path:
        return self.memory_dir / f"{day}.md"

    @property
    def memory_pipeline_state_json(self) -> Path:
        return self.root / f"{self.state_file_prefix}_memory_pipeline.json"

    @property
    def context_compaction_state_json(self) -> Path:
        return self.root / f"{self.state_file_prefix}_context_compaction_state.json"

    @property
    def schedule_queue_json(self) -> Path:
        return self.root / f"{self.state_file_prefix}_schedule_tasks.json"

    @property
    def image_gate_json(self) -> Path:
        return self.root / f"{self.state_file_prefix}_image_gate.json"


_REQUIRED_FILES_ATTR = ("identity", "soul", "user_md", "memory_md", "transcript")


def _required_workspace_file_paths(paths: WorkspacePaths) -> tuple[Path, ...]:
    return tuple(getattr(paths, attr) for attr in _REQUIRED_FILES_ATTR)


def is_workspace_initialized(workspace: Path) -> bool:
    """五件套存在则认为已初始化（磁盘；原型 REPL）。"""
    paths = WorkspacePaths(root=workspace.resolve())
    for p in _required_workspace_file_paths(paths):
        if not p.is_file():
            return False
    return True


def is_workspace_initialized_from_store(workspace: Path, store: MemoryStore) -> bool:
    """五件套在 MemoryStore 中有内容则认为已初始化（生产：DB + 进程内，不依赖磁盘）。"""
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    for attr in _REQUIRED_FILES_ATTR:
        rel = getattr(paths, attr).relative_to(root).as_posix()
        body = store.read_document_if_exists(rel)
        if body is None or not body.strip():
            return False
    return True


_MINIMAL_TRANSCRIPT_SEED = "# companion_minimal_seed\n"


def ensure_minimal_workspace_documents_in_store(
    workspace: Path,
    store: MemoryStore,
) -> None:
    """Write seed content for required paths into MemoryStore only (no disk authority)."""
    root = workspace.resolve()
    if is_workspace_initialized_from_store(root, store):
        return
    paths = WorkspacePaths(root=root)
    for attr in _REQUIRED_FILES_ATTR:
        rel = getattr(paths, attr).relative_to(root).as_posix()
        body = store.read_document_if_exists(rel)
        if body is not None and body.strip():
            continue
        if attr == "transcript":
            store.write_document(rel, _MINIMAL_TRANSCRIPT_SEED)
        else:
            store.write_document(rel, load_workspace_seed_text(rel))


# IDENTITY/USER 仍像模板或未约定时的子串
_IDENTITY_STUB_MARKERS: tuple[str, ...] = (
    "（在此填写",
    "（待定义）",
    "还没定",
    "等你来",
    "待对话填充",
)
_USER_STUB_MARKERS: tuple[str, ...] = (
    "（在此填写",
    "等待你告诉",
    "等待观察",
    "待对话填充",
)


def _text_matches_any_marker(text: str, markers: tuple[str, ...]) -> bool:
    s = text.strip()
    if not s:
        return True
    return any(m in s for m in markers)


def needs_startup_profile_inquiry(
    workspace: Path,
    store: MemoryStore,
) -> bool:
    """
    已初始化、且 transcript 仍为空时：若 IDENTITY 或 USER 仍像占位/未约定，
    则启动时应由助手先开口发问。
    """
    from .models import load_transcript_from_store

    root = workspace.resolve()
    if not is_workspace_initialized_from_store(root, store):
        return False
    paths = WorkspacePaths(root=root)
    rel_tr = paths.transcript.relative_to(root).as_posix()
    for m in load_transcript_from_store(store, rel_tr):
        if m.role in ("user", "assistant"):
            return False
    ident = store.read_document_if_exists("IDENTITY.md") or ""
    user_md = store.read_document_if_exists("USER.md") or ""
    id_stub = _text_matches_any_marker(ident, _IDENTITY_STUB_MARKERS)
    user_stub = _text_matches_any_marker(user_md, _USER_STUB_MARKERS)
    out = id_stub or user_stub
    logger.debug(
        "needs_startup_profile_inquiry ws={} id_stub={} user_stub={} -> {}",
        root.name,
        id_stub,
        user_stub,
        out,
    )
    return out
