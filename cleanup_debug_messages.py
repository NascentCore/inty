#!/usr/bin/env python3
"""
清理chats表中的debug_messages字段

由于新的角色卡逻辑和性能优化，旧的debug_messages可能包含过时的信息
"""

import asyncio
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, update
from app.core.config import settings
from app.api.deps import get_async_db
from app import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def analyze_debug_messages():
    """分析现有的debug_messages使用情况"""
    logger.info("分析chats表中的debug_messages使用情况...")
    
    async for session in get_async_db():
        try:
            # 统计debug_messages使用情况
            result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total_chats,
                    COUNT(CASE WHEN debug_messages IS NOT NULL THEN 1 END) as has_debug_messages,
                    AVG(CASE WHEN debug_messages IS NOT NULL THEN 
                        LENGTH(debug_messages::text) ELSE 0 END) as avg_debug_size
                FROM chats
            """))
            stats = result.first()
            
            logger.info(f"总聊天记录数: {stats[0]}")
            logger.info(f"有debug_messages的记录: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
            logger.info(f"平均debug_messages大小: {stats[2]:.0f}字符")
            
            # 查看最近的debug_messages示例
            result2 = await session.execute(text("""
                SELECT id, agent_id, updated_at, 
                       CASE WHEN debug_messages IS NOT NULL THEN 
                            LEFT(debug_messages::text, 100) || '...'
                       ELSE 'NULL' END as debug_preview
                FROM chats 
                WHERE debug_messages IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT 5
            """))
            examples = result2.fetchall()
            
            logger.info(f"\n=== 最近的debug_messages示例 ===")
            for chat_id, agent_id, updated_at, preview in examples:
                logger.info(f"Chat {chat_id[:8]}... (Agent: {agent_id[:8]}...): {preview}")
            
        except Exception as e:
            logger.error(f"分析debug_messages失败: {str(e)}")
        finally:
            break

async def cleanup_debug_messages(dry_run: bool = True):
    """
    清理debug_messages字段
    
    Args:
        dry_run: 是否只是测试模式
    """
    logger.info(f"开始清理debug_messages字段 (dry_run={dry_run})")
    
    async for session in get_async_db():
        try:
            # 查询有debug_messages的聊天记录
            result = await session.execute(
                select(models.Chat).where(
                    models.Chat.debug_messages.isnot(None)
                )
            )
            chats_with_debug = result.scalars().all()
            
            logger.info(f"找到 {len(chats_with_debug)} 个包含debug_messages的聊天记录")
            
            if not dry_run and chats_with_debug:
                # 批量更新，将debug_messages设为NULL
                await session.execute(
                    update(models.Chat)
                    .where(models.Chat.debug_messages.isnot(None))
                    .values(debug_messages=None)
                )
                
                await session.commit()
                logger.info(f"成功清理了 {len(chats_with_debug)} 个聊天记录的debug_messages")
            else:
                logger.info(f"测试模式：预计清理 {len(chats_with_debug)} 个debug_messages")
            
            # 检查清理后的状态
            if not dry_run:
                result_after = await session.execute(text("""
                    SELECT COUNT(CASE WHEN debug_messages IS NOT NULL THEN 1 END) as remaining_debug
                    FROM chats
                """))
                remaining = result_after.scalar()
                logger.info(f"清理后剩余debug_messages记录: {remaining}")
            
        except Exception as e:
            if not dry_run:
                await session.rollback()
            logger.error(f"清理debug_messages失败: {str(e)}")
            raise
        finally:
            break

async def main():
    """主函数"""
    print("Debug Messages 清理工具")
    print("=" * 50)
    print("由于角色卡系统和性能优化的引入，旧的debug_messages可能包含过时信息")
    print("建议清理这些数据以提升数据库性能")
    print()
    
    # 先分析现状
    await analyze_debug_messages()
    
    print("\n操作选项:")
    print("1. 测试模式 (预览清理效果)")
    print("2. 执行清理")
    print("3. 退出")
    
    choice = input("请选择操作 (1-3): ").strip()
    
    if choice == '1':
        await cleanup_debug_messages(dry_run=True)
    elif choice == '2':
        confirm = input("确认要清理所有debug_messages吗？这将不可逆 (y/N): ").strip().lower()
        if confirm == 'y':
            await cleanup_debug_messages(dry_run=False)
            print("✅ debug_messages清理完成")
        else:
            print("取消清理")
    else:
        print("退出")

if __name__ == "__main__":
    asyncio.run(main())