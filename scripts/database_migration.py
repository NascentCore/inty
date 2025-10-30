#!/usr/bin/env python3
"""
通用数据库迁移脚本
用于在具有相同 schema 的数据库之间迁移数据

使用方法:
    python database_migration.py --config migration_config.yaml --action migrate
    python database_migration.py --config migration_config.yaml --action verify
    python database_migration.py --config migration_config.yaml --action rollback
"""

import argparse
import asyncio
import asyncpg
import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import yaml
from pathlib import Path

class DatabaseMigrator:
    """数据库迁移器"""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        self.migration_log = []
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件未找到: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def _setup_logging(self):
        """设置日志"""
        log_config = self.config.get('logging', {})
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format=log_config.get('format', '%(asctime)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.FileHandler(log_config.get('file', 'migration.log'), encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    async def get_connection(self, env: str) -> asyncpg.Connection:
        """获取数据库连接"""
        if env not in self.config['environments']:
            raise ValueError(f"未知环境: {env}")
        
        db_config = self.config['environments'][env]['database']
        try:
            conn = await asyncpg.connect(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['db']
            )
            self.logger.info(f"成功连接到 {env} 环境数据库")
            return conn
        except Exception as e:
            self.logger.error(f"连接 {env} 环境数据库失败: {e}")
            raise
    
    async def get_table_list(self, conn: asyncpg.Connection) -> List[str]:
        """获取所有表名"""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
        rows = await conn.fetch(query)
        return [row['table_name'] for row in rows]
    
    async def get_table_columns(self, conn: asyncpg.Connection, table_name: str) -> List[Dict[str, Any]]:
        """获取表列信息"""
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = $1 AND table_schema = 'public'
        ORDER BY ordinal_position
        """
        rows = await conn.fetch(query, table_name)
        return [dict(row) for row in rows]
    
    async def get_table_row_count(self, conn: asyncpg.Connection, table_name: str) -> int:
        """获取表行数"""
        query = f"SELECT COUNT(*) FROM {table_name}"
        return await conn.fetchval(query)
    
    async def check_table_empty(self, conn: asyncpg.Connection, table_name: str) -> bool:
        """检查表是否为空"""
        count = await self.get_table_row_count(conn, table_name)
        return count == 0
    
    async def get_table_dependencies(self, conn: asyncpg.Connection) -> Dict[str, List[str]]:
        """获取表依赖关系"""
        query = """
        SELECT 
            tc.table_name,
            ccu.table_name AS foreign_table_name
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'public'
        """
        rows = await conn.fetch(query)
        
        dependencies = {}
        for row in rows:
            table = row['table_name']
            foreign_table = row['foreign_table_name']
            if table not in dependencies:
                dependencies[table] = []
            dependencies[table].append(foreign_table)
        
        return dependencies
    
    def _get_migration_order(self, tables: List[str], dependencies: Dict[str, List[str]]) -> List[str]:
        """获取迁移顺序（考虑外键依赖）"""
        # 简单的拓扑排序
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(table):
            if table in temp_visited:
                raise ValueError(f"检测到循环依赖: {table}")
            if table in visited:
                return
            
            temp_visited.add(table)
            
            # 先迁移依赖的表
            for dep in dependencies.get(table, []):
                if dep in tables:  # 只考虑在迁移列表中的表
                    visit(dep)
            
            temp_visited.remove(table)
            visited.add(table)
            result.append(table)
        
        for table in tables:
            if table not in visited:
                visit(table)
        
        return result
    
    async def migrate_table(self, source_conn: asyncpg.Connection, 
                          sink_conn: asyncpg.Connection, table_name: str) -> Dict[str, Any]:
        """迁移单个表"""
        self.logger.info(f"开始迁移表: {table_name}")
        
        start_time = datetime.now()
        
        # 获取表列信息
        columns = await self.get_table_columns(source_conn, table_name)
        column_names = [col['column_name'] for col in columns]
        
        # 检查 SINK 表是否为空
        if not await self.check_table_empty(sink_conn, table_name):
            self.logger.warning(f"表 {table_name} 在 SINK 中不为空，跳过迁移")
            return {
                'table_name': table_name,
                'status': 'skipped',
                'reason': 'table_not_empty',
                'rows_migrated': 0,
                'duration': 0
            }
        
        # 从 SOURCE 读取数据
        select_query = f"SELECT * FROM {table_name}"
        rows = await source_conn.fetch(select_query)
        
        if not rows:
            self.logger.info(f"表 {table_name} 在 SOURCE 中为空")
            return {
                'table_name': table_name,
                'status': 'skipped',
                'reason': 'source_empty',
                'rows_migrated': 0,
                'duration': 0
            }
        
        # 构建插入语句
        placeholders = [f"${i+1}" for i in range(len(column_names))]
        insert_query = f"""
        INSERT INTO {table_name} ({', '.join(column_names)})
        VALUES ({', '.join(placeholders)})
        """
        
        # 批量插入数据
        batch_size = self.config.get('migration', {}).get('batch_size', 1000)
        rows_migrated = 0
        
        try:
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                values_list = []
                for row in batch:
                    values_list.append([row[col] for col in column_names])
                
                await sink_conn.executemany(insert_query, values_list)
                rows_migrated += len(batch)
                self.logger.info(f"已迁移 {rows_migrated}/{len(rows)} 行")
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"表 {table_name} 迁移完成，共 {rows_migrated} 行，耗时 {duration:.2f} 秒")
            
            return {
                'table_name': table_name,
                'status': 'success',
                'rows_migrated': rows_migrated,
                'duration': duration
            }
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"表 {table_name} 迁移失败: {e}")
            return {
                'table_name': table_name,
                'status': 'failed',
                'error': str(e),
                'rows_migrated': rows_migrated,
                'duration': duration
            }
    
    async def migrate_all_tables(self) -> Dict[str, Any]:
        """迁移所有表"""
        self.logger.info("开始数据库迁移")
        
        source_conn = await self.get_connection('source')
        sink_conn = await self.get_connection('sink')
        
        try:
            # 获取所有表
            tables = await self.get_table_list(source_conn)
            self.logger.info(f"发现 {len(tables)} 个表需要迁移")
            
            # 获取表依赖关系
            dependencies = await self.get_table_dependencies(source_conn)
            
            # 按依赖顺序迁移
            migration_order = self._get_migration_order(tables, dependencies)
            self.logger.info(f"迁移顺序: {migration_order}")
            
            # 执行迁移
            results = []
            total_rows = 0
            success_count = 0
            failed_count = 0
            
            for table_name in migration_order:
                try:
                    result = await self.migrate_table(source_conn, sink_conn, table_name)
                    results.append(result)
                    
                    if result['status'] == 'success':
                        success_count += 1
                        total_rows += result['rows_migrated']
                    elif result['status'] == 'failed':
                        failed_count += 1
                    
                    # 记录到迁移日志
                    self.migration_log.append({
                        'timestamp': datetime.now().isoformat(),
                        'table_name': table_name,
                        'result': result
                    })
                    
                except Exception as e:
                    self.logger.error(f"迁移表 {table_name} 时发生异常: {e}")
                    failed_count += 1
                    results.append({
                        'table_name': table_name,
                        'status': 'failed',
                        'error': str(e),
                        'rows_migrated': 0,
                        'duration': 0
                    })
                    
                    if not self.config.get('migration', {}).get('continue_on_error', True):
                        raise
            
            # 保存迁移日志
            await self._save_migration_log()
            
            self.logger.info(f"迁移完成: 成功 {success_count}, 失败 {failed_count}, 总行数 {total_rows}")
            
            return {
                'total_tables': len(tables),
                'success_count': success_count,
                'failed_count': failed_count,
                'total_rows': total_rows,
                'results': results
            }
            
        finally:
            await source_conn.close()
            await sink_conn.close()
    
    async def verify_migration(self) -> Dict[str, Any]:
        """验证迁移结果"""
        self.logger.info("开始验证迁移结果")
        
        source_conn = await self.get_connection('source')
        sink_conn = await self.get_connection('sink')
        
        try:
            # 获取所有表
            tables = await self.get_table_list(source_conn)
            
            verification_results = []
            all_match = True
            
            self.logger.info("表名\t\t源记录数\t目标记录数\t状态")
            self.logger.info("-" * 60)
            
            for table_name in tables:
                source_count = await self.get_table_row_count(source_conn, table_name)
                sink_count = await self.get_table_row_count(sink_conn, table_name)
                
                match = source_count == sink_count
                if not match:
                    all_match = False
                
                status = "✓" if match else "✗"
                self.logger.info(f"{table_name:<20}\t{source_count}\t\t{sink_count}\t\t{status}")
                
                verification_results.append({
                    'table_name': table_name,
                    'source_count': source_count,
                    'sink_count': sink_count,
                    'match': match
                })
            
            self.logger.info("-" * 60)
            self.logger.info(f"总体状态: {'✓ 通过' if all_match else '✗ 失败'}")
            
            return {
                'all_match': all_match,
                'results': verification_results
            }
            
        finally:
            await source_conn.close()
            await sink_conn.close()
    
    async def rollback_migration(self) -> Dict[str, Any]:
        """回滚迁移"""
        self.logger.info("开始回滚迁移")
        
        sink_conn = await self.get_connection('sink')
        
        try:
            # 获取所有表
            tables = await self.get_table_list(sink_conn)
            
            # 按相反顺序清空表
            rollback_order = list(reversed(tables))
            
            results = []
            for table_name in rollback_order:
                try:
                    # 清空表
                    await sink_conn.execute(f"TRUNCATE TABLE {table_name} CASCADE")
                    self.logger.info(f"已清空表: {table_name}")
                    results.append({
                        'table_name': table_name,
                        'status': 'success'
                    })
                except Exception as e:
                    self.logger.error(f"清空表 {table_name} 失败: {e}")
                    results.append({
                        'table_name': table_name,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            self.logger.info("回滚完成")
            return {
                'results': results
            }
            
        finally:
            await sink_conn.close()
    
    async def _save_migration_log(self):
        """保存迁移日志"""
        log_file = self.config.get('migration', {}).get('log_file', 'migration_log.json')
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.migration_log, f, ensure_ascii=False, indent=2, default=str)
        self.logger.info(f"迁移日志已保存到: {log_file}")

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库迁移工具")
    parser.add_argument("--config", "-c", required=True, help="配置文件路径")
    parser.add_argument("--action", "-a", choices=["migrate", "verify", "rollback"], 
                       default="migrate", help="操作类型")
    
    args = parser.parse_args()
    
    try:
        migrator = DatabaseMigrator(args.config)
        
        if args.action == "migrate":
            result = await migrator.migrate_all_tables()
            print(f"迁移完成: {result}")
            
        elif args.action == "verify":
            result = await migrator.verify_migration()
            print(f"验证结果: {'通过' if result['all_match'] else '失败'}")
            
        elif args.action == "rollback":
            result = await migrator.rollback_migration()
            print(f"回滚完成: {result}")
            
    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())