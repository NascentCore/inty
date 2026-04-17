# CREATED_BY_AGENT
"""
手动对单个用户跑记忆抽取，用于测试。

用法（在仓库根目录）:
    export PYTHONPATH=.
    python scripts/run_memory_extraction.py --user-id <USER_UUID>
    python scripts/run_memory_extraction.py --user-id <USER_UUID> --dry-run

--dry-run: 只拉取该用户消息并打印条数，不调 LLM、不写 memory。
"""

import argparse
import asyncio
import sys

from loguru import logger

from app.core.logging import init_logger
from app.db.session import AsyncSessionLocal
from app.services.memory_extraction_service import (
    extract_and_save,
    get_all_messages_for_user,
)


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="对单个用户跑记忆抽取（测试用）",
    )
    parser.add_argument(
        "--user-id",
        required=True,
        help="users.id (UUID)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只拉取消息并打印条数，不调 LLM、不写 memory",
    )
    args = parser.parse_args()

    init_logger()

    if args.dry_run:
        msgs = get_all_messages_for_user(args.user_id)
        logger.info(f"user_id={args.user_id} 消息数: {len(msgs)}")
        if msgs:
            logger.info("前 3 条示例 (role, content 前 80 字):")
            for i, row in enumerate(msgs[:3]):
                r, c = row[0], row[1]
                logger.info(f"  [{i+1}] {r}: {(c or '')[:80]}...")
        return 0

    try:
        async with AsyncSessionLocal() as db:
            await extract_and_save(db, args.user_id)
        logger.info(f"记忆抽取完成 user_id={args.user_id}")
        return 0
    except KeyboardInterrupt:
        logger.info("用户中断")
        return 1
    except Exception as e:
        logger.error(f"记忆抽取失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
