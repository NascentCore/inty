#!/usr/bin/env python3
"""
清理脚本：清理所有存储动图（gif/avif）而不是视频的agent的background_animated字段

此脚本会：
- 查找所有 background_animated 字段包含动图URL（.gif 或 .avif）的agent
- 将这些字段清空（设置为 NULL）

使用场景：
- 在系统从存储动图改为存储视频后，清理历史数据
"""

import asyncio
import re
import sys
from pathlib import Path
from typing import List

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.session import AsyncSessionLocal
from app.core.logging import init_logger
from app.models.agent import Agent

# 初始化日志
init_logger()


def is_animated_image_url(url: str) -> bool:
    """
    判断URL是否为动图（gif或avif格式）

    Args:
        url: 要检查的URL

    Returns:
        True 如果是动图URL，False 否则
    """
    if not url:
        return False

    url_lower = url.lower()

    # 检查文件扩展名
    if url_lower.endswith(".gif") or url_lower.endswith(".avif"):
        return True

    # 检查URL路径中是否包含动图相关路径
    # 之前存储动图的路径通常是 uploads/animated_images
    if "animated_images" in url_lower:
        return True

    # 检查URL中是否包含动图格式标识
    # 例如：.gif? 或 .avif? 或 /gif/ 或 /avif/
    if re.search(r"\.(gif|avif)(\?|/|$)", url_lower):
        return True

    return False


async def find_agents_with_animated_backgrounds(
    session: AsyncSession,
) -> List[Agent]:
    """
    查找所有 background_animated 字段包含动图URL的agent

    Args:
        session: 数据库会话

    Returns:
        包含动图URL的agent列表
    """
    # 获取所有有 background_animated 的agent
    result = await session.execute(
        select(Agent).where(
            Agent.background_animated.isnot(None),
            Agent.deleted_at.is_(None),
        )
    )
    all_agents = result.scalars().all()

    # 过滤出包含动图URL的agent
    agents_with_animated = []
    for agent in all_agents:
        if is_animated_image_url(agent.background_animated):
            agents_with_animated.append(agent)

    return agents_with_animated


async def cleanup_animated_backgrounds(
    session: AsyncSession, dry_run: bool = True
) -> dict:
    """
    清理所有包含动图URL的background_animated字段

    Args:
        session: 数据库会话
        dry_run: 如果为True，只统计不实际修改

    Returns:
        包含统计信息的字典
    """
    logger.info("开始查找包含动图URL的agent...")

    agents_with_animated = await find_agents_with_animated_backgrounds(session)

    stats = {
        "total_found": len(agents_with_animated),
        "cleaned": 0,
        "errors": 0,
        "agent_ids": [],
    }

    if len(agents_with_animated) == 0:
        logger.info("未找到包含动图URL的agent")
        return stats

    logger.info(f"找到 {len(agents_with_animated)} 个包含动图URL的agent")

    if dry_run:
        logger.info("【DRY RUN模式】以下agent将被清理：")
        for agent in agents_with_animated:
            logger.info(
                f"  - Agent ID: {agent.id}, Name: {agent.name}, "
                f"URL: {agent.background_animated}"
            )
            stats["agent_ids"].append(agent.id)
        return stats

    # 实际清理
    logger.info("开始清理...")
    for agent in agents_with_animated:
        try:
            # 将 background_animated 设置为 None
            await session.execute(
                update(Agent)
                .where(Agent.id == agent.id)
                .values(background_animated=None)
            )
            stats["cleaned"] += 1
            stats["agent_ids"].append(agent.id)
            logger.info(
                f"已清理 Agent ID: {agent.id}, Name: {agent.name}, "
                f"原URL: {agent.background_animated}"
            )
        except Exception as e:
            stats["errors"] += 1
            logger.error(f"清理 Agent {agent.id} 时出错: {str(e)}")

    # 提交事务
    await session.commit()
    logger.info(f"清理完成：成功 {stats['cleaned']} 个，错误 {stats['errors']} 个")

    return stats


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("清理脚本：清理存储动图而不是视频的agent")
    print("=" * 60)
    print("\n此脚本会：")
    print("  • 查找所有 background_animated 字段包含动图URL（.gif 或 .avif）的agent")
    print("  • 将这些字段清空（设置为 NULL）")
    print("\n识别规则：")
    print("  • URL 以 .gif 或 .avif 结尾")
    print("  • URL 路径中包含 'animated_images'")
    print("  • URL 中包含 .gif 或 .avif 格式标识")
    print("=" * 60)

    # 先执行 dry run
    async with AsyncSessionLocal() as session:
        logger.info("\n执行 DRY RUN（预览模式）...")
        dry_run_stats = await cleanup_animated_backgrounds(session, dry_run=True)

        if dry_run_stats["total_found"] == 0:
            print("\n✅ 未找到需要清理的agent，脚本结束")
            return

        print(f"\n找到 {dry_run_stats['total_found']} 个需要清理的agent")
        print("\n将被清理的Agent ID列表：")
        for agent_id in dry_run_stats["agent_ids"]:
            print(f"  - {agent_id}")

    # 确认操作
    print("\n" + "=" * 60)
    confirmation = input("请输入 'CLEANUP' 来确认清理操作（其他任何输入都会取消）: ")

    if confirmation != "CLEANUP":
        logger.info("操作已取消")
        return

    # 二次确认
    print("\n" + "=" * 60)
    final_confirmation = input(
        "最后确认：此操作将清空这些agent的background_animated字段！"
        "请再次输入 'CLEANUP' 确认: "
    )

    if final_confirmation != "CLEANUP":
        logger.info("操作已取消")
        return

    # 执行实际清理
    async with AsyncSessionLocal() as session:
        logger.info("\n开始执行清理...")
        stats = await cleanup_animated_backgrounds(session, dry_run=False)

        print("\n" + "=" * 60)
        if stats["errors"] == 0:
            print("🎉 清理操作已成功完成！")
            print(f"✅ 成功清理 {stats['cleaned']} 个agent")
        else:
            print("⚠️  清理操作完成，但有部分错误")
            print(f"✅ 成功清理 {stats['cleaned']} 个agent")
            print(f"❌ 错误 {stats['errors']} 个")
        print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("操作被用户中断")
    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}")
        raise
