"""
数据库迁移脚本：从 SOURCE 数据库迁移数据到 SINK 数据库

使用方法：
1. 配置 SOURCE 和 SINK 数据库连接信息
2. 运行脚本：python scripts/migrate_database.py
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any

from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from loguru import logger

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


class DatabaseMigrator:
    """数据库迁移器"""
    
    def __init__(self, source_db_url: str, sink_db_url: str):
        self.source_db_url = source_db_url
        self.sink_db_url = sink_db_url
        self.source_engine = None
        self.sink_engine = None
        
    async def __aenter__(self):
        self.source_engine = create_async_engine(
            self.source_db_url,
            pool_size=10,
            max_overflow=5,
            echo=False
        )
        self.sink_engine = create_async_engine(
            self.sink_db_url,
            pool_size=10,
            max_overflow=5,
            echo=False
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.source_engine:
            await self.source_engine.dispose()
        if self.sink_engine:
            await self.sink_engine.dispose()
    
    async def get_table_names(self, session: AsyncSession) -> List[str]:
        """获取所有表名"""
        result = await session.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """))
        return [row[0] for row in result]
    
    async def get_table_row_count(self, session: AsyncSession, table_name: str) -> int:
        """获取表的行数"""
        try:
            result = await session.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            )
            return result.scalar() or 0
        except Exception as e:
            logger.warning(f"无法获取表 {table_name} 的行数: {e}")
            return 0
    
    async def get_table_columns(self, session: AsyncSession, table_name: str) -> List[str]:
        """获取表的列名"""
        result = await session.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = '{table_name}'
            ORDER BY ordinal_position
        """))
        return [row[0] for row in result]
    
    async def disable_foreign_keys(self, session: AsyncSession):
        """禁用外键约束"""
        await session.execute(text("SET session_replication_role = 'replica';"))
        await session.commit()
        logger.info("已禁用外键约束检查")
    
    async def enable_foreign_keys(self, session: AsyncSession):
        """启用外键约束"""
        await session.execute(text("SET session_replication_role = 'origin';"))
        await session.commit()
        logger.info("已启用外键约束检查")
    
    async def migrate_table(
        self, 
        source_session: AsyncSession, 
        sink_session: AsyncSession, 
        table_name: str,
        batch_size: int = 1000
    ) -> int:
        """迁移单个表"""
        logger.info(f"开始迁移表: {table_name}")
        
        # 检查 SINK 表是否已有数据
        sink_count = await self.get_table_row_count(sink_session, table_name)
        if sink_count > 0:
            logger.warning(f"表 {table_name} 在 SINK 数据库中已有 {sink_count} 行数据，将跳过迁移")
            return 0
        
        # 获取 SOURCE 表行数
        source_count = await self.get_table_row_count(source_session, table_name)
        if source_count == 0:
            logger.info(f"表 {table_name} 在 SOURCE 数据库中为空，跳过")
            return 0
        
        # 获取列名
        columns = await self.get_table_columns(source_session, table_name)
        if not columns:
            logger.warning(f"表 {table_name} 没有列，跳过")
            return 0
        
        column_names = ', '.join([f'"{col}"' for col in columns])
        placeholders = ', '.join([f':{col}' for col in columns])
        
        # 分批迁移数据
        offset = 0
        total_inserted = 0
        
        while offset < source_count:
            # 获取一批数据
            query = text(f"""
                SELECT * FROM {table_name} 
                ORDER BY (SELECT 1)
                LIMIT :limit OFFSET :offset
            """)
            result = await source_session.execute(
                query, 
                {"limit": batch_size, "offset": offset}
            )
            rows = result.fetchall()
            
            if not rows:
                break
            
            # 转换为字典列表
            batch_data = [dict(zip(columns, row)) for row in rows]
            
            # 插入到 SINK
            insert_sql = text(f"""
                INSERT INTO {table_name} ({column_names})
                VALUES ({placeholders})
            """)
            
            try:
                await sink_session.execute(insert_sql, batch_data)
                await sink_session.commit()
                
                total_inserted += len(batch_data)
                offset += len(batch_data)
                
                if total_inserted % 10000 == 0:
                    logger.info(f"  已迁移 {total_inserted}/{source_count} 行...")
            except Exception as e:
                await sink_session.rollback()
                logger.error(f"迁移表 {table_name} 失败（偏移量 {offset}）: {e}")
                raise
        
        logger.success(f"完成迁移表 {table_name}: {total_inserted} 行")
        return total_inserted
    
    async def reset_sequences(self, session: AsyncSession):
        """重置所有序列"""
        logger.info("开始重置序列...")
        
        result = await session.execute(text("""
            SELECT sequence_name 
            FROM information_schema.sequences 
            WHERE sequence_schema = 'public'
        """))
        
        sequences = [row[0] for row in result]
        
        for seq_name in sequences:
            # 尝试从序列名推断表名和列名
            # 假设序列名为 table_name_id_seq
            if seq_name.endswith('_id_seq'):
                table_name = seq_name[:-7]  # 移除 '_id_seq'
                col_name = table_name + '_id'
            else:
                # 如果命名规则不同，尝试其他方式
                parts = seq_name.split('_')
                if len(parts) >= 2:
                    table_name = '_'.join(parts[:-2])
                    col_name = '_'.join(parts[:-1])
                else:
                    logger.warning(f"无法推断序列 {seq_name} 对应的表和列，跳过")
                    continue
            
            try:
                # 检查表是否存在
                check_table = await session.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table_name}'
                    )
                """))
                
                if not check_table.scalar():
                    logger.warning(f"序列 {seq_name} 对应的表 {table_name} 不存在，跳过")
                    continue
                
                # 检查列是否存在
                check_col = await session.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table_name}'
                        AND column_name = '{col_name}'
                    )
                """))
                
                if not check_col.scalar():
                    logger.warning(f"序列 {seq_name} 对应的列 {table_name}.{col_name} 不存在，跳过")
                    continue
                
                # 重置序列
                reset_sql = text(f"""
                    SELECT setval('{seq_name}', 
                        COALESCE((SELECT MAX({col_name}) FROM {table_name}), 1), 
                        true)
                """)
                await session.execute(reset_sql)
                await session.commit()
                
                logger.info(f"重置序列: {seq_name}")
            except Exception as e:
                logger.warning(f"重置序列 {seq_name} 失败: {e}")
                await session.rollback()
    
    async def verify_migration(
        self, 
        source_session: AsyncSession, 
        sink_session: AsyncSession,
        tables: List[str]
    ) -> bool:
        """验证迁移结果"""
        logger.info("开始验证迁移结果...")
        
        all_match = True
        for table in tables:
            source_count = await self.get_table_row_count(source_session, table)
            sink_count = await self.get_table_row_count(sink_session, table)
            
            if source_count != sink_count:
                logger.error(f"表 {table} 行数不匹配: SOURCE={source_count}, SINK={sink_count}")
                all_match = False
            else:
                logger.info(f"表 {table}: {source_count} 行（匹配）")
        
        return all_match
    
    async def migrate_all(self, batch_size: int = 1000, disable_fk: bool = True):
        """执行完整迁移"""
        async with AsyncSession(self.source_engine) as source_session, \
                 AsyncSession(self.sink_engine) as sink_session:
            
            # 获取所有表
            tables = await self.get_table_names(source_session)
            logger.info(f"找到 {len(tables)} 个表需要迁移")
            
            # 统计 SOURCE 数据库信息
            logger.info("\nSOURCE 数据库统计:")
            total_source_rows = 0
            for table in tables:
                count = await self.get_table_row_count(source_session, table)
                total_source_rows += count
                logger.info(f"  {table}: {count:,} 行")
            logger.info(f"总计: {total_source_rows:,} 行")
            
            # 禁用外键约束（如果需要）
            if disable_fk:
                await self.disable_foreign_keys(sink_session)
            
            try:
                # 迁移每个表
                logger.info("\n开始迁移...")
                total_rows = 0
                for table in tables:
                    try:
                        rows = await self.migrate_table(
                            source_session, 
                            sink_session, 
                            table,
                            batch_size=batch_size
                        )
                        total_rows += rows
                    except Exception as e:
                        logger.error(f"迁移表 {table} 失败: {e}")
                        raise
                
                # 启用外键约束
                if disable_fk:
                    await self.enable_foreign_keys(sink_session)
                
                # 重置序列
                await self.reset_sequences(sink_session)
                
                # 验证迁移结果
                logger.info("\n验证迁移结果...")
                is_valid = await self.verify_migration(source_session, sink_session, tables)
                
                if is_valid:
                    logger.success(f"\n迁移完成！总共迁移 {total_rows:,} 行数据")
                else:
                    logger.warning("\n迁移完成，但验证发现部分表数据不匹配，请检查")
                
            except Exception as e:
                logger.error(f"迁移过程中发生错误: {e}")
                await sink_session.rollback()
                raise


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库迁移工具")
    parser.add_argument(
        "--source-url",
        required=True,
        help="SOURCE 数据库连接 URL，例如: postgresql+asyncpg://user:password@host:port/dbname"
    )
    parser.add_argument(
        "--sink-url",
        required=True,
        help="SINK 数据库连接 URL，例如: postgresql+asyncpg://user:password@host:port/dbname"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="批量处理大小（默认: 1000）"
    )
    parser.add_argument(
        "--keep-fk",
        action="store_true",
        help="保持外键约束（默认会禁用外键以加快迁移速度）"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("数据库迁移工具")
    logger.info("=" * 60)
    logger.info(f"SOURCE: {args.source_url.split('@')[-1] if '@' in args.source_url else args.source_url}")
    logger.info(f"SINK: {args.sink_url.split('@')[-1] if '@' in args.sink_url else args.sink_url}")
    logger.info(f"批量大小: {args.batch_size}")
    logger.info("=" * 60)
    
    async with DatabaseMigrator(args.source_url, args.sink_url) as migrator:
        await migrator.migrate_all(
            batch_size=args.batch_size,
            disable_fk=not args.keep_fk
        )


if __name__ == "__main__":
    asyncio.run(main())
