#!/usr/bin/env python3
# CREATED_BY_AGENT
"""
删除所有 festival 类型记忆（memory 表）以及对应的「节日记忆提示」类 chat_history 记录。
幂等：多次执行等价于删除所有符合条件的行。
"""

import asyncio
import sys
from typing import Annotated

import cyclopts
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal

MESSAGE_TYPE_FESTIVAL_MEMORY_PROMPT = "festival_memory_prompt"


async def _count_and_delete(
    session: AsyncSession,
    dry_run: bool,
) -> tuple[int, int]:
    """
    统计并（在非 dry_run 且已确认时）删除 festival 记忆与对应 chat_history。
    返回 (memory_count, chat_history_count) 表示将删除或已删除的条数。
    """
    # 统计
    memory_result = await session.execute(
        text("SELECT COUNT(*) FROM memory WHERE memory_type = 'festival'")
    )
    memory_count = memory_result.scalar() or 0
    ch_result = await session.execute(
        text(
            "SELECT COUNT(*) FROM chat_history WHERE meta_data->>'messageType' = :msg_type"
        ),
        {"msg_type": MESSAGE_TYPE_FESTIVAL_MEMORY_PROMPT},
    )
    ch_count = ch_result.scalar() or 0

    logger.info(
        f"将删除: memory (festival) {memory_count} 条, chat_history (festival_memory_prompt) {ch_count} 条"
    )
    logger.debug(f"dry_run={dry_run}")

    if dry_run:
        return memory_count, ch_count

    # 执行删除：先 chat_history 再 memory
    del_ch = await session.execute(
        text("DELETE FROM chat_history WHERE meta_data->>'messageType' = :msg_type"),
        {"msg_type": MESSAGE_TYPE_FESTIVAL_MEMORY_PROMPT},
    )
    del_mem = await session.execute(
        text("DELETE FROM memory WHERE memory_type = 'festival'")
    )
    await session.commit()
    logger.info(
        f"已删除: chat_history {del_ch.rowcount} 条, memory {del_mem.rowcount} 条"
    )
    return del_mem.rowcount, del_ch.rowcount


async def _run(
    dry_run: bool,
    yes: bool,
) -> None:
    if not dry_run and not yes:
        print("\n此操作将永久删除所有节日记忆及对应提示消息，不可恢复。")
        confirm = input("输入 y 确认执行，其他键取消: ").strip().lower()
        if confirm != "y":
            logger.info("已取消")
            return
    async with AsyncSessionLocal() as session:
        try:
            await _count_and_delete(session, dry_run=dry_run)
        except Exception as e:
            await session.rollback()
            logger.error(f"执行失败: {e}")
            sys.exit(1)
    if dry_run:
        logger.info("DRY-RUN 完成，未做任何实际修改")
    else:
        logger.success("节日记忆与对应 chat_history 已删除")


def main(
    dry_run: Annotated[
        bool,
        cyclopts.Parameter(
            name="--dry-run",
            help="仅统计并打印将删除的数量，不执行删除（默认开启）",
        ),
    ] = True,
    no_dry_run: Annotated[
        bool,
        cyclopts.Parameter(
            name="--no-dry-run",
            help="实际执行删除（需配合 --yes 跳过交互确认，或执行时输入 y 确认）",
        ),
    ] = False,
    yes: Annotated[
        bool,
        cyclopts.Parameter(
            name="--yes",
            help="非 dry-run 时跳过交互确认，直接执行删除",
        ),
    ] = False,
) -> None:
    """删除所有 festival 记忆及对应 chat_history。"""
    if no_dry_run:
        dry_run = False
    logger.info("=" * 60)
    logger.info("删除节日记忆与对应 chat_history")
    logger.info("=" * 60)
    asyncio.run(_run(dry_run=dry_run, yes=yes))


if __name__ == "__main__":
    cyclopts.run(main)
