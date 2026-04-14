#!/usr/bin/env python3
"""
清空单个用户与 agent 之间活跃聊天的 companion 工作区版本行与 chat_history。

用于本地联调：删库后下一轮会重新 seed（含 templates/SOUL.md），但须重启后端以丢弃
进程内 CompanionManager / MemoryStore 缓存。

用法（仓库根目录）:

  export PYTHONPATH=.
  export INTY_ACCESS_TOKEN=...   # 与 REPL backend-ws 相同
  python scripts/clear_companion_chat_session.py --agent-id <uuid>
  python scripts/clear_companion_chat_session.py --agent-id <uuid> --no-dry-run --yes
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Annotated

import cyclopts
from jose import JWTError, jwt
from loguru import logger
from sqlalchemy import delete, func, select

from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal
from app.models.chat import Chat
from app.models.chat_history import ChatHistory
from app.models.companion_workspace import CompanionWorkspaceDocumentVersion
from app.services.chat_service import generate_session_id


def _resolve_user_id_from_token() -> str:
    raw = (os.environ.get("INTY_ACCESS_TOKEN") or "").strip()
    if not raw:
        raise SystemExit("需要 INTY_ACCESS_TOKEN（JWT），或使用 --user-id 显式传入 sub")
    cfg = global_config_loaded_from_config_yaml
    try:
        payload = jwt.decode(
            raw,
            cfg.security.secret_key,
            algorithms=[cfg.security.algorithm],
        )
    except JWTError as e:
        raise SystemExit(f"JWT 解析失败: {e}") from e
    sub = payload.get("sub")
    if not sub:
        raise SystemExit("JWT 缺少 sub")
    return str(sub)


async def _run(
    *,
    agent_id: str,
    user_id: str,
    execute: bool,
    yes: bool,
) -> None:
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Chat)
            .where(
                Chat.user_id == user_id,
                Chat.agent_id == agent_id,
                Chat.is_active.is_(True),
            )
            .limit(2)
        )
        res = await db.execute(stmt)
        rows = res.scalars().all()
        if not rows:
            raise SystemExit(
                f"未找到活跃聊天: user_id={user_id!r} agent_id={agent_id!r}"
            )
        if len(rows) > 1:
            raise SystemExit(f"查到多条活跃聊天（{len(rows)}），请人工处理或收窄条件")
        chat = rows[0]
        chat_id_str = str(chat.id)
        session_id = generate_session_id(chat_id_str)

        cnt_ws = await db.scalar(
            select(func.count())
            .select_from(CompanionWorkspaceDocumentVersion)
            .where(
                CompanionWorkspaceDocumentVersion.user_id == user_id,
                CompanionWorkspaceDocumentVersion.companion_id == agent_id,
                CompanionWorkspaceDocumentVersion.chat_id == chat_id_str,
            )
        )
        cnt_hist = await db.scalar(
            select(func.count())
            .select_from(ChatHistory)
            .where(ChatHistory.session_id == uuid.UUID(session_id))
        )

        logger.info(
            "scope user_id={} agent_id={} chat_id={} session_id={}",
            user_id,
            agent_id,
            chat_id_str,
            session_id,
        )
        print(
            f"将删除 companion_workspace_document_versions 约 {cnt_ws} 行，"
            f"chat_history 约 {cnt_hist} 行（session_id={session_id}）。"
        )

        if not execute:
            print("当前为 dry-run，未改库。确认无误后加 --no-dry-run --yes 执行。")
            return

        if not yes:
            raise SystemExit("非 dry-run 时必须传入 --yes 以确认")

        await db.execute(
            delete(CompanionWorkspaceDocumentVersion).where(
                CompanionWorkspaceDocumentVersion.user_id == user_id,
                CompanionWorkspaceDocumentVersion.companion_id == agent_id,
                CompanionWorkspaceDocumentVersion.chat_id == chat_id_str,
            )
        )
        await db.execute(
            delete(ChatHistory).where(ChatHistory.session_id == uuid.UUID(session_id))
        )
        await db.commit()
        print(
            "已删除。请重启 Inty 后端（例如 8001）再连 WebSocket，否则会读到旧 MemoryStore 缓存。"
        )


def main(
    agent_id: Annotated[str, cyclopts.Parameter(help="agents.id / companion_id")],
    user_id: Annotated[
        str | None,
        cyclopts.Parameter(help="users.id；默认从 INTY_ACCESS_TOKEN 的 sub 解析"),
    ] = None,
    no_dry_run: Annotated[
        bool,
        cyclopts.Parameter(
            name="--no-dry-run",
            help="执行删除（默认仅统计并打印，不写库）",
        ),
    ] = False,
    yes: Annotated[
        bool,
        cyclopts.Parameter(
            name="--yes",
            help="与 --no-dry-run 联用，跳过交互确认",
        ),
    ] = False,
) -> None:
    uid = user_id or _resolve_user_id_from_token()
    asyncio.run(_run(agent_id=agent_id, user_id=uid, execute=no_dry_run, yes=yes))


if __name__ == "__main__":
    cyclopts.run(main)
