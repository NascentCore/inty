#!/usr/bin/env python3
"""
自动清理chats表脚本（非交互式）
为并发测试准备干净的数据环境
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings


async def cleanup_chats_table():
    """自动清理chats表"""
    print("=== 自动清理chats表 ===")
    
    # 从配置创建数据库连接
    db_config = settings.database
    db_url = f"postgresql+asyncpg://{db_config.user}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.db}"
    
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # 先查看当前记录数
            result = await session.execute(text("SELECT COUNT(*) FROM chats"))
            count_before = result.scalar()
            print(f"清理前chats表记录数: {count_before}")
            
            if count_before == 0:
                print("✅ chats表已经是空的，无需清理")
                return
            
            # 显示一些示例记录
            result = await session.execute(text("""
                SELECT id, user_id, agent_id, is_active, created_at 
                FROM chats 
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            records = result.fetchall()
            
            print(f"\n最近5条记录示例:")
            for record in records:
                print(f"  {record.id[:8]}... | {record.user_id[:8]}... | {record.agent_id[:8]}... | active:{record.is_active} | {record.created_at}")
            
            print(f"\n🚀 开始自动清理 {count_before} 条记录...")
            
            # 由于有外键约束，需要按顺序清理
            # 1. 清理evaluation_interactions表的外键引用
            result = await session.execute(text("DELETE FROM evaluation_interactions WHERE chat_id IN (SELECT id FROM chats)"))
            eval_deleted = result.rowcount
            if eval_deleted > 0:
                print(f"  删除evaluation_interactions记录: {eval_deleted}")
            
            # 2. 清理chat_settings表
            result = await session.execute(text("DELETE FROM chat_settings WHERE chat_id IN (SELECT id FROM chats)"))
            settings_deleted = result.rowcount
            if settings_deleted > 0:
                print(f"  删除chat_settings记录: {settings_deleted}")
            
            # 3. 清理messages表
            result = await session.execute(text("DELETE FROM messages WHERE chat_id IN (SELECT id FROM chats)"))
            messages_deleted = result.rowcount
            if messages_deleted > 0:
                print(f"  删除messages记录: {messages_deleted}")
            
            # 4. 最后清理chats表
            result = await session.execute(text("DELETE FROM chats"))
            chats_deleted = result.rowcount
            print(f"  删除chats记录: {chats_deleted}")
            
            # 提交事务
            await session.commit()
            
            # 验证清理结果
            result = await session.execute(text("SELECT COUNT(*) FROM chats"))
            count_after = result.scalar()
            
            print(f"\n✅ 清理完成!")
            print(f"   清理前: {count_before} 条记录")
            print(f"   清理后: {count_after} 条记录")
            
            if count_after == 0:
                print("✅ chats表已完全清空，可以进行并发测试")
            else:
                print(f"⚠️ 仍有 {count_after} 条记录未清理")
                
    except Exception as e:
        print(f"❌ 清理过程中出错: {e}")
        # 回滚事务
        try:
            await session.rollback()
        except:
            pass
        raise
    finally:
        await engine.dispose()


async def main():
    """主函数"""
    try:
        await cleanup_chats_table()
    except Exception as e:
        print(f"❌ 脚本执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())