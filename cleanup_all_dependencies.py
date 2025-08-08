#!/usr/bin/env python3
"""
清理chats表及所有依赖项
为并发测试准备完全干净的数据环境
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


async def get_foreign_key_dependencies(session):
    """获取所有引用chats表的外键依赖"""
    result = await session.execute(text("""
        SELECT DISTINCT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' 
        AND ccu.table_name = 'chats'
        ORDER BY tc.table_name;
    """))
    
    return result.fetchall()


async def cleanup_with_dependencies():
    """清理chats表及所有依赖项"""
    print("=== 清理chats表及所有依赖项 ===")
    
    # 从配置创建数据库连接
    db_config = settings.database
    db_url = f"postgresql+asyncpg://{db_config.user}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.db}"
    
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # 1. 先检查chats表记录数
            result = await session.execute(text("SELECT COUNT(*) FROM chats"))
            chats_count = result.scalar()
            print(f"chats表记录数: {chats_count}")
            
            if chats_count == 0:
                print("✅ chats表已经是空的，检查依赖项...")
            
            # 2. 获取所有外键依赖
            print("\n🔍 分析外键依赖关系...")
            dependencies = await get_foreign_key_dependencies(session)
            
            if dependencies:
                print("发现以下表依赖chats表:")
                for dep in dependencies:
                    print(f"  - {dep.table_name}.{dep.column_name} -> chats.{dep.foreign_column_name}")
            else:
                print("  未发现外键依赖")
            
            # 3. 手动检查常见的依赖表并清理
            tables_to_clean = [
                # 直接依赖chats的表
                "evaluation_interactions",  # chat_id -> chats.id
                "chat_settings",           # chat_id -> chats.id  
                "messages",                # chat_id -> chats.id
                
                # 可能的间接依赖
                "user_subscriptions",      # 可能通过user_id间接关联
                "subscription_usage",      # 可能记录chat相关的使用情况
            ]
            
            print(f"\n🚀 开始清理依赖项和主表...")
            total_deleted = 0
            
            # 按依赖关系顺序清理
            for table_name in tables_to_clean:
                try:
                    # 检查表是否存在
                    result = await session.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = '{table_name}'
                        )
                    """))
                    table_exists = result.scalar()
                    
                    if not table_exists:
                        print(f"  ⚠️ 表 {table_name} 不存在，跳过")
                        continue
                    
                    # 检查表中的记录数
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count_before = result.scalar()
                    
                    if count_before == 0:
                        print(f"  ✅ {table_name}: 已经是空的")
                        continue
                    
                    # 根据表的特点执行不同的清理策略
                    if table_name in ["evaluation_interactions", "chat_settings", "messages"]:
                        # 这些表直接引用chats.id
                        if chats_count > 0:
                            result = await session.execute(text(f"""
                                DELETE FROM {table_name} 
                                WHERE chat_id IN (SELECT id FROM chats)
                            """))
                        else:
                            # 如果chats表已空，直接清空这些表
                            result = await session.execute(text(f"DELETE FROM {table_name}"))
                    else:
                        # 其他表，先检查是否真的需要清理
                        print(f"  ⚠️ {table_name}: {count_before} 条记录，需要手动确认是否清理")
                        continue
                    
                    count_deleted = result.rowcount
                    if count_deleted > 0:
                        print(f"  🗑️ {table_name}: 删除 {count_deleted} 条记录")
                        total_deleted += count_deleted
                    else:
                        print(f"  ✅ {table_name}: 无需删除")
                        
                except Exception as e:
                    print(f"  ❌ 清理 {table_name} 时出错: {e}")
                    continue
            
            # 4. 最后清理chats表
            if chats_count > 0:
                result = await session.execute(text("DELETE FROM chats"))
                chats_deleted = result.rowcount
                print(f"  🗑️ chats: 删除 {chats_deleted} 条记录")
                total_deleted += chats_deleted
            else:
                print(f"  ✅ chats: 已经是空的")
            
            # 5. 提交所有更改
            await session.commit()
            print(f"\n✅ 清理完成! 总共删除 {total_deleted} 条记录")
            
            # 6. 验证清理结果
            print("\n🔍 验证清理结果:")
            for table_name in tables_to_clean + ["chats"]:
                try:
                    result = await session.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = '{table_name}'
                        )
                    """))
                    if result.scalar():
                        result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                        count = result.scalar()
                        status = "✅" if count == 0 else f"⚠️ ({count})"
                        print(f"  {status} {table_name}: {count} 条记录")
                except Exception as e:
                    print(f"  ❌ {table_name}: 检查失败 - {e}")
            
            print("\n🎉 数据库已准备好进行并发测试!")
                
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
        await cleanup_with_dependencies()
    except Exception as e:
        print(f"❌ 脚本执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())