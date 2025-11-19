#!/usr/bin/env python3
"""
修复数据库中 readable_id 为空的 agent 记录

为所有 readable_id 为 None 的 agent 生成并填充唯一的 readable_id。

使用方法:
    python scripts/fix_agent_readable_id.py [--dry-run]

选项:
    --dry-run: 仅显示需要修复的记录，不实际更新数据库
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_async_db
from app.models.agent import Agent
from sqlalchemy import select, update, text
from loguru import logger


async def get_agents_with_null_readable_id(db) -> list[Agent]:
    """查找所有 readable_id 为 None 的 agent"""
    stmt = select(Agent).where(
        (Agent.readable_id.is_(None)) | (Agent.readable_id == "")
    ).where(Agent.deleted_at.is_(None))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_max_readable_id(db) -> int:
    """获取当前数据库中最大的数字 readable_id"""
    result = await db.execute(
        text(
            "SELECT MAX(CAST(readable_id AS INTEGER)) FROM agents WHERE readable_id ~ '^[0-9]+$'"
        )
    )
    max_id = result.scalar()
    return max_id if max_id is not None and max_id >= 10000000 else 10000000 - 1


async def check_readable_id_exists(db, readable_id: str) -> bool:
    """检查 readable_id 是否已存在"""
    stmt = select(Agent).where(Agent.readable_id == readable_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def fix_agent_readable_ids(dry_run: bool = False):
    """修复所有 readable_id 为空的 agent"""
    try:
        async for db in get_async_db():
            # 查找所有需要修复的 agent
            logger.info("正在查找 readable_id 为空的 agent...")
            agents_to_fix = await get_agents_with_null_readable_id(db)
            
            if not agents_to_fix:
                logger.info("✅ 没有需要修复的记录，所有 agent 的 readable_id 都已填充")
                return
            
            logger.info(f"找到 {len(agents_to_fix)} 个需要修复的 agent")
            
            # 获取当前最大的 readable_id
            max_id = await get_max_readable_id(db)
            logger.info(f"当前最大 readable_id: {max_id}")
            
            if dry_run:
                logger.info("\n=== 以下 agent 需要修复 readable_id ===")
                for agent in agents_to_fix:
                    logger.info(
                        f"  - Agent ID: {agent.id}, Name: {agent.name}, "
                        f"Created: {agent.created_at}"
                    )
                logger.info(f"\n总共需要修复 {len(agents_to_fix)} 个 agent")
                logger.info("使用 --dry-run 参数，未实际更新数据库")
                return
            
            # 按创建时间排序，确保修复顺序一致
            agents_to_fix.sort(key=lambda a: a.created_at or a.id)
            
            # 批量修复
            next_id = max_id + 1
            fixed_count = 0
            skipped_count = 0
            
            logger.info(f"\n开始修复，从 readable_id {next_id} 开始...")
            
            for agent in agents_to_fix:
                # 生成下一个可用的 readable_id
                # 确保不与现有记录冲突
                attempts = 0
                max_attempts = 1000
                candidate_id = None
                
                while attempts < max_attempts:
                    candidate_id = str(next_id).zfill(8)
                    exists = await check_readable_id_exists(db, candidate_id)
                    
                    if not exists:
                        break
                    
                    next_id += 1
                    attempts += 1
                
                if attempts >= max_attempts:
                    logger.error(
                        f"❌ 无法为 agent {agent.id} 生成唯一的 readable_id，"
                        f"已尝试 {max_attempts} 次"
                    )
                    skipped_count += 1
                    continue
                
                # 更新 agent 的 readable_id
                await db.execute(
                    update(Agent)
                    .where(Agent.id == agent.id)
                    .values(readable_id=candidate_id)
                )
                
                logger.info(
                    f"✅ 修复 agent {agent.id} ({agent.name}): "
                    f"readable_id = {candidate_id}"
                )
                
                fixed_count += 1
                next_id += 1
            
            # 提交事务
            await db.commit()
            
            logger.info(f"\n=== 修复完成 ===")
            logger.info(f"成功修复: {fixed_count} 个 agent")
            if skipped_count > 0:
                logger.warning(f"跳过: {skipped_count} 个 agent（无法生成唯一 ID）")
            
            # 验证修复结果
            remaining = await get_agents_with_null_readable_id(db)
            if remaining:
                logger.warning(
                    f"⚠️  仍有 {len(remaining)} 个 agent 的 readable_id 为空"
                )
            else:
                logger.info("✅ 所有 agent 的 readable_id 已成功填充")
            
            break
            
    except Exception as e:
        logger.error(f"❌ 修复过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="修复数据库中 readable_id 为空的 agent 记录"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅显示需要修复的记录，不实际更新数据库",
    )
    
    args = parser.parse_args()
    
    logger.info("🔄 开始修复 agent readable_id...")
    if args.dry_run:
        logger.info("⚠️  运行在 dry-run 模式，不会实际更新数据库")
    
    asyncio.run(fix_agent_readable_ids(dry_run=args.dry_run))


if __name__ == "__main__":
    main()

