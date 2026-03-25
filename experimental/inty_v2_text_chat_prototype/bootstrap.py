"""生成 workspace 模板（init-workspace）。"""

from __future__ import annotations

import json
from pathlib import Path

from .file_store import write_text
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

_TEMPLATE_CAPABILITIES = """# CAPABILITIES

本文件记录**基础性限制**（用户侧生理与现实条件、助手侧技术与产品形态），不是 SOUL/USER 里的人为相处规则。
可随产品、通道或模型能力变化更新；与「关系偏好」无关。

## 用户侧（生理与现实）

（例如：作息、注意力时长、身体状态对互动的客观影响；此处不写「用户规定不许怎样」。）

## 助手侧（技术与产品形态）

（例如：当前仅为文本通道、无真实躯体、上下文与工具能力上限、无法访问未授权系统等。）
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

    root.mkdir(parents=True, exist_ok=True)
    paths.memory_dir.mkdir(parents=True, exist_ok=True)
    paths.memory_daily_dir.mkdir(parents=True, exist_ok=True)

    write_text(paths.identity, _TEMPLATE_IDENTITY.strip() + "\n")
    write_text(paths.soul, _TEMPLATE_SOUL.strip() + "\n")
    write_text(paths.user_md, _TEMPLATE_USER.strip() + "\n")
    write_text(paths.memory_md, _TEMPLATE_MEMORY.strip() + "\n")
    write_text(paths.capabilities_md, _TEMPLATE_CAPABILITIES.strip() + "\n")
    write_text(paths.transcript, "")
    # memory/.gitkeep、memory/daily/.gitkeep（便于空目录进 git）
    write_text(paths.memory_dir / ".gitkeep", "")
    write_text(paths.memory_daily_dir / ".gitkeep", "")
    if write_context:
        write_text(
            paths.context_json,
            json.dumps(_CONTEXT_JSON, indent=2, ensure_ascii=False) + "\n",
        )
