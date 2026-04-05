"""生成 workspace 模板（init-workspace）。"""

from __future__ import annotations

import json
from pathlib import Path

from .file_store import write_text
from .jsonl_db_store import flush_jsonl_db_store, shutdown_jsonl_db_store
from .memory_store_registry import get_memory_store, shutdown_memory_store
from .paths import WorkspacePaths

_PKG_DIR = Path(__file__).resolve().parent
_TEMPLATES_DIR = _PKG_DIR / "templates"
_TEMPLATE_DOCS: tuple[str, ...] = (
    "IDENTITY.md",
    "SOUL.md",
    "USER.md",
    "MEMORY.md",
)


def _read_workspace_template(name: str) -> str:
    path = _TEMPLATES_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"missing workspace template: {path}")
    return path.read_text(encoding="utf-8")


_CONTEXT_JSON = {
    "context_mode": "intimate",
    "user_id": "proto-user-1",
    "companion_id": "proto-companion-1",
    "chat_id": "proto-chat-1",
}


def init_workspace(path: Path, *, write_context: bool = True) -> None:
    """从 templates/ 拷贝四份 md 模板，创建空 transcript、memory 目录与可选 context.json。"""
    root = path.resolve()
    paths = WorkspacePaths(root=root)
    store = get_memory_store(root)
    try:
        root.mkdir(parents=True, exist_ok=True)
        paths.memory_dir.mkdir(parents=True, exist_ok=True)
        paths.memory_daily_dir.mkdir(parents=True, exist_ok=True)

        for name in _TEMPLATE_DOCS:
            raw = _read_workspace_template(name)
            body = raw if raw.endswith("\n") else raw + "\n"
            store.write_document(name, body)
        write_text(paths.transcript, "")
        # memory/.gitkeep、memory/daily/.gitkeep（便于空目录进 git）
        write_text(paths.memory_dir / ".gitkeep", "")
        write_text(paths.memory_daily_dir / ".gitkeep", "")
        if write_context:
            write_text(
                paths.context_json,
                json.dumps(_CONTEXT_JSON, indent=2, ensure_ascii=False) + "\n",
            )
        store.flush_now(timeout_s=5.0)
    finally:
        shutdown_memory_store(root, timeout_s=5.0)
        flush_jsonl_db_store(timeout_s=5.0)
        shutdown_jsonl_db_store(timeout_s=5.0)
