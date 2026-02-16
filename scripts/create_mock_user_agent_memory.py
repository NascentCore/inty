#!/usr/bin/env python3
# CREATED_BY_AGENT
"""
为指定 (user_id, agent_id) 创建一条 mock 记忆（memory 表）及对应消息（chat_history：
节日记忆提示 + 可选 mock 人机对话）。幂等：同维度先删后插，等价于覆盖。
"""

import asyncio
import sys
from datetime import date, datetime, timezone
from typing import Annotated, Optional

import cyclopts
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db.session import AsyncSessionLocal
from app.models.memory import Memory
from app.services import chat_history_service, chat_service
from app.services.memory_service import (
    build_festival_memory_metadata,
    resolve_festival_name_and_date,
)

DEFAULT_MOCK_CONTENT = "这是一条测试记忆。"
DEFAULT_FESTIVAL_NAME = "测试节日"
MOCK_HUMAN_CONTENT = "（mock）今天聊得很开心。"
MOCK_AI_CONTENT = "（mock）我也是，期待下次再聊。"


async def _ensure_user_and_agent_exist(
    db: AsyncSession, user_id: str, agent_id: str
) -> None:
    u = await db.execute(select(models.User).where(models.User.id == user_id))
    if u.scalar_one_or_none() is None:
        logger.error(f"用户不存在: user_id={user_id}")
        sys.exit(1)
    a = await db.execute(select(models.Agent).where(models.Agent.id == agent_id))
    if a.scalar_one_or_none() is None:
        logger.error(f"角色不存在: agent_id={agent_id}")
        sys.exit(1)


def _parse_date(value: Optional[str]) -> date:
    if value is None:
        return date.today()
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError) as e:
        logger.error(f"无效的日期格式，应为 YYYY-MM-DD: {value} ({e})")
        sys.exit(1)


async def _get_festival_name_date(
    db: AsyncSession,
    memory_type: str,
    festival_config_id: Optional[int],
    festival_name: Optional[str],
    festival_date: Optional[str],
) -> tuple[str, date]:
    if memory_type != "festival":
        raise ValueError("memory_type must be festival")
    if festival_config_id is not None:
        r = await db.execute(
            select(models.FestivalMemoryConfig).where(
                models.FestivalMemoryConfig.id == festival_config_id
            )
        )
        config = r.scalar_one_or_none()
        if config is None:
            logger.error(f"节日配置不存在: festival_config_id={festival_config_id}")
            sys.exit(1)
        return config.festival_name, config.festival_date
    name = festival_name or DEFAULT_FESTIVAL_NAME
    d = _parse_date(festival_date)
    return name, d


def _add_mock_chat_messages_sync(session_id: str, agent_id: str) -> None:
    chat_history_service.add_user_message(session_id, MOCK_HUMAN_CONTENT, meta_data={})
    chat_history_service.add_ai_message_sync(
        session_id, MOCK_AI_CONTENT, agent_id=agent_id
    )


async def _run(
    user_id: str,
    agent_id: str,
    memory_type: str,
    festival_config_id: Optional[int],
    festival_name: Optional[str],
    festival_date: Optional[str],
    content: str,
    add_mock_chat: bool,
    dry_run: bool,
    yes: bool,
) -> None:
    if not dry_run and not yes:
        print("\n此操作将创建/覆盖 mock 记忆及对应消息。")
        confirm = input("输入 y 确认执行，其他键取消: ").strip().lower()
        if confirm != "y":
            logger.info("已取消")
            return

    async with AsyncSessionLocal() as db:
        try:
            await _ensure_user_and_agent_exist(db, user_id, agent_id)
        except SystemExit:
            raise
        except Exception as e:
            logger.error(f"校验失败: {e}")
            sys.exit(1)

        if memory_type == "festival":
            try:
                festival_name_val, festival_date_val = await _get_festival_name_date(
                    db, memory_type, festival_config_id, festival_name, festival_date
                )
            except SystemExit:
                raise
            except ValueError as e:
                logger.error(str(e))
                sys.exit(1)
            logger.info(
                f"将写入 Memory: user_id={user_id}, agent_id={agent_id}, "
                f"memory_type=festival, festival_name={festival_name_val}, "
                f"festival_date={festival_date_val}, content={content[:50]}..."
            )
        else:
            logger.info(
                f"将写入 Memory: user_id={user_id}, agent_id={agent_id}, "
                f"memory_type=user_agent, content={content[:50]}..."
            )

        if dry_run:
            logger.info(
                "DRY-RUN: 将 get_or_create_chat，删除旧 memory 并插入新 memory，"
                + ("插入 mock 人机 2 条 + " if add_mock_chat else "")
                + (
                    "不插入节日记忆提示（与生产一致，由发起聊天/消息列表按需投递）。"
                    if memory_type == "festival"
                    else "不插入提示消息。"
                )
            )
            return

        try:
            chat = await chat_service.get_or_create_chat_by_agent(db, user_id, agent_id)
        except Exception as e:
            logger.error(f"get_or_create_chat_by_agent 失败: {e}")
            sys.exit(1)
        session_id = chat_service.generate_session_id(chat.id)
        logger.debug(f"session_id={session_id}")

        extracted_at = datetime.now(timezone.utc)
        memory_row = None

        if memory_type == "festival":
            festival_name_val, festival_date_val = await _get_festival_name_date(
                db, memory_type, festival_config_id, festival_name, festival_date
            )
            existing_rows = await db.execute(
                select(
                    Memory.id,
                    Memory.meta_data,
                    Memory.festival_name,
                    Memory.festival_date,
                ).where(
                    Memory.user_id == user_id,
                    Memory.agent_id == agent_id,
                    Memory.memory_type == "festival",
                )
            )
            existing_ids = []
            for row in existing_rows.fetchall():
                memory_id, metadata, legacy_festival_name, legacy_festival_date = row
                resolved_name, resolved_date = resolve_festival_name_and_date(
                    metadata, legacy_festival_name, legacy_festival_date
                )
                if (
                    resolved_name == festival_name_val
                    and resolved_date == festival_date_val
                ):
                    existing_ids.append(memory_id)
            if existing_ids:
                await db.execute(delete(Memory).where(Memory.id.in_(existing_ids)))
            memory_row = Memory(
                user_id=user_id,
                memory_type="festival",
                agent_id=agent_id,
                content=content,
                meta_data=build_festival_memory_metadata(
                    festival_name_val, festival_date_val
                ),
                extracted_at=extracted_at,
                festival_name=festival_name_val,
                festival_date=festival_date_val,
            )
            db.add(memory_row)
        else:
            await db.execute(
                delete(Memory).where(
                    Memory.user_id == user_id,
                    Memory.agent_id == agent_id,
                    Memory.memory_type == "user_agent",
                )
            )
            db.add(
                Memory(
                    user_id=user_id,
                    memory_type="user_agent",
                    agent_id=agent_id,
                    content=content,
                    extracted_at=extracted_at,
                )
            )
        await db.commit()

        if add_mock_chat:
            await asyncio.to_thread(_add_mock_chat_messages_sync, session_id, agent_id)
            logger.info("已插入 mock 人机消息 2 条")

        # 节日记忆与生产一致：仅写 memory，不在此处写 chat_history；用户发起聊天或拉取消息列表时会按需投递
        if memory_type == "festival" and memory_row is not None:
            logger.info(
                f"节日记忆已写入 memory id={memory_row.id}，提示将在用户发起聊天或拉取消息列表时按需投递"
            )

    logger.success("mock 记忆与对应消息已创建")


def main(
    user_id: str,
    agent_id: str,
    memory_type: Annotated[
        str,
        cyclopts.Parameter(help="记忆类型: festival | user_agent"),
    ] = "festival",
    festival_config_id: Annotated[
        Optional[int],
        cyclopts.Parameter(
            name="--festival-config-id",
            help="指定已有节日配置 id，用于 festival_name/festival_date；与手动参数二选一",
        ),
    ] = None,
    festival_name: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--festival-name",
            help="节日名称（未指定 --festival-config-id 时使用，默认「测试节日」）",
        ),
    ] = None,
    festival_date: Annotated[
        Optional[str],
        cyclopts.Parameter(
            name="--festival-date",
            help="节日日期 YYYY-MM-DD（未指定 --festival-config-id 时使用，默认今日）",
        ),
    ] = None,
    content: Annotated[
        str,
        cyclopts.Parameter(help="记忆内容，默认一段测试文案"),
    ] = DEFAULT_MOCK_CONTENT,
    add_mock_chat: Annotated[
        bool,
        cyclopts.Parameter(
            name="--add-mock-chat",
            help="在会话中插入 1 条 human + 1 条 ai 的 mock 对话",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        cyclopts.Parameter(name="--dry-run", help="仅打印将执行的操作，不落库"),
    ] = True,
    no_dry_run: Annotated[
        bool,
        cyclopts.Parameter(
            name="--no-dry-run",
            help="实际执行写入",
        ),
    ] = False,
    yes: Annotated[
        bool,
        cyclopts.Parameter(
            name="--yes",
            help="非 dry-run 时跳过交互确认",
        ),
    ] = False,
) -> None:
    """为指定用户与角色创建 mock 记忆及对应消息。"""
    if no_dry_run:
        dry_run = False
    if memory_type not in ("festival", "user_agent"):
        logger.error("--memory-type 必须为 festival 或 user_agent")
        sys.exit(1)
    logger.info("=" * 60)
    logger.info("创建用户与角色 Mock 记忆及对应消息")
    logger.info("=" * 60)
    asyncio.run(
        _run(
            user_id=user_id,
            agent_id=agent_id,
            memory_type=memory_type,
            festival_config_id=festival_config_id,
            festival_name=festival_name,
            festival_date=festival_date,
            content=content,
            add_mock_chat=add_mock_chat,
            dry_run=dry_run,
            yes=yes,
        )
    )


if __name__ == "__main__":
    cyclopts.run(main)
