#!/usr/bin/env python3
"""
清理脚本：删除所有agent和相关对话数据，保留用户信息

此脚本会永久删除：
- 所有agent记录
- 所有chat记录
- 所有message记录
- user_subscriptions中的相关记录（如果必要）

保留的数据：
- 用户账户信息
- 订阅计划配置
- 系统配置
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.core.logging import init_logger

# 初始化日志
init_logger()


class AgentChatCleanup:
    """Agent和Chat数据清理器"""

    def __init__(self):
        self.session: AsyncSession = None

    async def get_data_counts(self) -> dict:
        """获取各表的数据统计"""
        counts = {}

        # 获取各表记录数（只包含实际存在的表）
        tables = [
            "messages",
            "chat_settings",
            "chats",
            "agents",
            "users",
            "subscription_plans",
            "user_subscriptions",
            "report",
            "user_notifications",
        ]

        for table in tables:
            try:
                result = await self.session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                )
                counts[table] = result.scalar()
            except Exception as e:
                # 如果表不存在，跳过
                logger.warning(f"表 {table} 不存在或无法访问: {str(e)}")
                counts[table] = 0

        return counts

    async def cleanup_all_agents_and_chats(self) -> bool:
        """清理所有agent和chat相关数据"""
        try:
            logger.info("开始清理agent和chat数据...")

            # 获取清理前的数据统计
            before_counts = await self.get_data_counts()
            logger.info(f"清理前数据统计: {before_counts}")

            # 按照外键依赖顺序删除数据，避免外键约束违反

            # 1. 删除用户通知记录（先删除，避免后续依赖问题）
            logger.info("删除所有通知记录...")
            result = await self.session.execute(
                text("DELETE FROM user_notifications")
            )
            logger.info(f"删除了 {result.rowcount} 条通知记录")

            # 2. 删除与agent相关的举报记录（使用正确的字段名target_id）
            logger.info("删除相关举报记录...")
            # 由于report表的target_id可能指向agent，先删除所有举报记录
            result = await self.session.execute(text("DELETE FROM report"))
            logger.info(f"删除了 {result.rowcount} 条举报记录")

            # 3. 删除messages表（依赖chat_id）
            logger.info("删除所有消息记录...")
            result = await self.session.execute(text("DELETE FROM messages"))
            logger.info(f"删除了 {result.rowcount} 条消息记录")

            # 4. 删除chat_settings表（依赖chat_id、agent_id、user_id）
            logger.info("删除所有对话设置...")
            result = await self.session.execute(
                text("DELETE FROM chat_settings")
            )
            logger.info(f"删除了 {result.rowcount} 条对话设置")

            # 5. 删除chats表（依赖user_id和agent_id）
            logger.info("删除所有对话记录...")
            result = await self.session.execute(text("DELETE FROM chats"))
            logger.info(f"删除了 {result.rowcount} 条对话记录")

            # 6. 删除agents表
            logger.info("删除所有agent记录...")
            result = await self.session.execute(text("DELETE FROM agents"))
            logger.info(f"删除了 {result.rowcount} 条agent记录")

            # 提交事务
            await self.session.commit()

            # 获取清理后的数据统计
            after_counts = await self.get_data_counts()
            logger.info(f"清理后数据统计: {after_counts}")

            # 验证清理结果
            if (
                after_counts["messages"] == 0
                and after_counts["chat_settings"] == 0
                and after_counts["chats"] == 0
                and after_counts["agents"] == 0
            ):
                logger.success("✅ 所有agent和chat数据已成功清理！")
                logger.info(f"✅ 保留用户数据: {after_counts['users']} 个用户")
                logger.info(
                    f"✅ 保留订阅计划: {after_counts['subscription_plans']} 个计划"
                )
                logger.info(
                    f"✅ 保留用户订阅: {after_counts['user_subscriptions']} 个订阅"
                )
                logger.info(
                    f"✅ 清理了举报记录: {before_counts.get('report', 0)} 条"
                )
                logger.info(
                    f"✅ 清理了通知记录: {before_counts.get('user_notifications', 0)} 条"
                )
                return True
            else:
                logger.error("❌ 数据清理可能不完整，请检查！")
                logger.error(
                    f"剩余数据: messages={after_counts['messages']}, chat_settings={after_counts['chat_settings']}, chats={after_counts['chats']}, agents={after_counts['agents']}"
                )
                return False

        except Exception as e:
            logger.error(f"清理过程中发生错误: {str(e)}")
            await self.session.rollback()
            return False

    async def run(self):
        """执行清理流程"""
        async with AsyncSessionLocal() as session:
            self.session = session

            try:
                # 显示警告信息
                print("\n" + "=" * 60)
                print("⚠️  警告：此操作将永久删除所有Agent和Chat数据！")
                print("=" * 60)
                print("将要删除的数据：")
                print("  • 所有AI agent记录")
                print("  • 所有对话(chat)记录")
                print("  • 所有消息(message)记录")
                print("  • 所有对话设置(chat_settings)记录")
                print("  • 相关的举报和通知记录")
                print("\n保留的数据：")
                print("  • 用户账户信息")
                print("  • 订阅计划配置")
                print("  • 用户订阅记录")
                print("=" * 60)

                # 获取当前数据统计
                current_counts = await self.get_data_counts()
                print(f"\n当前数据统计：")
                for table, count in current_counts.items():
                    print(f"  {table}: {count} 条记录")

                # 确认操作
                print(f"\n")
                confirmation = input(
                    "请输入 'DELETE' 来确认删除操作（其他任何输入都会取消）: "
                )

                if confirmation != "DELETE":
                    logger.info("操作已取消")
                    return

                # 二次确认
                print(f"\n")
                final_confirmation = input(
                    "最后确认：此操作不可逆！请再次输入 'DELETE' 确认: "
                )

                if final_confirmation != "DELETE":
                    logger.info("操作已取消")
                    return

                # 执行清理
                success = await self.cleanup_all_agents_and_chats()

                if success:
                    print("\n" + "=" * 60)
                    print("🎉 清理操作已成功完成！")
                    print("=" * 60)
                else:
                    print("\n" + "=" * 60)
                    print("❌ 清理操作失败，请检查日志！")
                    print("=" * 60)

            except KeyboardInterrupt:
                logger.info("操作被用户中断")
            except Exception as e:
                logger.error(f"执行过程中发生错误: {str(e)}")


async def main():
    """主函数"""
    cleanup = AgentChatCleanup()
    await cleanup.run()


if __name__ == "__main__":
    asyncio.run(main())
