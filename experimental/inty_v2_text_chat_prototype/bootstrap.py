"""生成 workspace 模板（init-workspace）。"""

from __future__ import annotations

import json
from pathlib import Path

from .file_store import write_text
from .memory_store_registry import get_memory_store, shutdown_memory_store
from .paths import WorkspacePaths

_TEMPLATE_IDENTITY = """# IDENTITY

（在此填写助手身份表层：称呼、角色、与用户的关系等。）
"""

_TEMPLATE_SOUL = """# SOUL

（在此填写价值观、边界、危机与安全相关原则。）
"""

_TEMPLATE_USER = """# USER

（用户称呼、界限、互动密度等约定。）
"""

_TEMPLATE_MEMORY = """# MEMORY

（长期记忆定稿；对话后可能由记忆更新步骤自动覆盖。）
"""

_CONTEXT_JSON = {
    "context_mode": "intimate",
    "user_id": "proto-user-1",
    "companion_id": "proto-companion-1",
    "chat_id": "proto-chat-1",
}


def init_workspace(path: Path, *, write_context: bool = True) -> None:
    """创建必选文件、空 transcript、memory 目录与可选 context.json。"""
    root = path.resolve()
    paths = WorkspacePaths(root=root)
    store = get_memory_store(root)
    try:
        root.mkdir(parents=True, exist_ok=True)
        paths.memory_dir.mkdir(parents=True, exist_ok=True)
        paths.memory_daily_dir.mkdir(parents=True, exist_ok=True)

        store.write_document("IDENTITY.md", _TEMPLATE_IDENTITY.strip() + "\n")
        store.write_document("SOUL.md", _TEMPLATE_SOUL.strip() + "\n")
        store.write_document("USER.md", _TEMPLATE_USER.strip() + "\n")
        store.write_document("MEMORY.md", _TEMPLATE_MEMORY.strip() + "\n")
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
