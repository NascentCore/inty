#!/usr/bin/env python3
"""
清空所有 agents 的 main_prompt 和 mode_prompt 字段

此脚本会：
- 将所有 agents 的 main_prompt 字段设置为 NULL
- 将所有 agents 的 mode_prompt 字段设置为 NULL
"""

import asyncio
import sys
from pathlib import Path

from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from app.core.logging import init_logger
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent

# 初始化日志
init_logger()


class AgentPromptCleaner:
    """Agent 提示词字段清理器"""

    def __init__(self):
        self.session: AsyncSession = None

    async def get_prompt_statistics(self) -> dict:
        """获取提示词字段的统计信息"""
        stats = {}

        # 统计总 agents 数（只统计未删除的）
        total_result = await self.session.execute(
            select(func.count(Agent.id)).where(Agent.deleted_at.is_(None))
        )
        stats["total_agents"] = total_result.scalar() or 0

        # 统计有 main_prompt 的 agents 数（只统计未删除的）
        main_prompt_result = await self.session.execute(
            select(func.count(Agent.id)).where(
                Agent.deleted_at.is_(None),
                Agent.main_prompt.isnot(None),
                Agent.main_prompt != "",
            )
        )
        stats["agents_with_main_prompt"] = main_prompt_result.scalar() or 0

        # 统计有 mode_prompt 的 agents 数（只统计未删除的）
        mode_prompt_result = await self.session.execute(
            select(func.count(Agent.id)).where(
                Agent.deleted_at.is_(None),
                Agent.mode_prompt.isnot(None),
                Agent.mode_prompt != "",
            )
        )
        stats["agents_with_mode_prompt"] = mode_prompt_result.scalar() or 0

        return stats

    async def clear_prompts(self) -> bool:
        """清空所有未删除 agents 的 main_prompt 和 mode_prompt 字段"""
        try:
            logger.info("开始清空未删除 agents 的提示词字段...")

            # 获取更新前的统计信息
            before_stats = await self.get_prompt_statistics()
            logger.info(f"更新前统计: {before_stats}")

            # 批量更新所有未删除的 agents
            logger.info("正在更新 agents 记录...")
            result = await self.session.execute(
                update(Agent)
                .where(Agent.deleted_at.is_(None))
                .values(main_prompt=None, mode_prompt=None)
            )
            updated_count = result.rowcount
            logger.info(f"已更新 {updated_count} 条 agents 记录")

            # 提交事务
            await self.session.commit()

            # 获取更新后的统计信息
            after_stats = await self.get_prompt_statistics()
            logger.info(f"更新后统计: {after_stats}")

            # 验证更新结果
            if (
                after_stats["agents_with_main_prompt"] == 0
                and after_stats["agents_with_mode_prompt"] == 0
            ):
                logger.success("✅ 所有未删除 agents 的提示词字段已成功清空！")
                logger.info(f"✅ 共更新了 {updated_count} 条记录")
                logger.info(
                    f"✅ 清空了 {before_stats['agents_with_main_prompt']} 个 main_prompt"
                )
                logger.info(
                    f"✅ 清空了 {before_stats['agents_with_mode_prompt']} 个 mode_prompt"
                )
                return True
            else:
                logger.error("❌ 提示词字段清空可能不完整，请检查！")
                logger.error(
                    f"剩余 main_prompt: {after_stats['agents_with_main_prompt']}, "
                    f"剩余 mode_prompt: {after_stats['agents_with_mode_prompt']}"
                )
                return False

        except Exception as e:
            logger.error(f"清空过程中发生错误: {str(e)}")
            await self.session.rollback()
            return False

    async def run(self):
        """执行清空流程"""
        async with AsyncSessionLocal() as session:
            self.session = session

            try:
                logger.info("=" * 60)
                logger.info(
                    "开始清空所有未删除 agents 的 main_prompt 和 mode_prompt 字段"
                )
                logger.info("=" * 60)

                # 执行清空操作
                success = await self.clear_prompts()

                if success:
                    logger.info("=" * 60)
                    logger.success("🎉 清空操作已成功完成！")
                    logger.info("=" * 60)
                else:
                    logger.error("=" * 60)
                    logger.error("❌ 清空操作失败，请检查日志！")
                    logger.error("=" * 60)

            except KeyboardInterrupt:
                logger.info("操作被用户中断")
            except Exception as e:
                logger.error(f"执行过程中发生错误: {str(e)}")


async def main():
    """主函数"""
    cleaner = AgentPromptCleaner()
    await cleaner.run()


if __name__ == "__main__":
    asyncio.run(main())
