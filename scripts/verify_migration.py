#!/usr/bin/env python3
"""
数据库迁移验证脚本
用于验证从 SOURCE 到 SINK 的数据迁移是否成功

使用方法:
    python verify_migration.py --config migration_config.yaml
    python verify_migration.py --config migration_config.yaml --detailed
    python verify_migration.py --config migration_config.yaml --sample-ratio 0.1
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
import random
from pathlib import Path

class MigrationVerifier:
    """迁移验证器"""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        self.verification_results = []
        
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
                logging.FileHandler(log_config.get('file', 'verification.log'), encoding='utf-8'),
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
    
    async def get_table_row_count(self, conn: asyncpg.Connection, table_name: str) -> int:
        """获取表行数"""
        query = f"SELECT COUNT(*) FROM {table_name}"
        return await conn.fetchval(query)
    
    async def get_table_schema(self, conn: asyncpg.Connection, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_name = $1 AND table_schema = 'public'
        ORDER BY ordinal_position
        """
        rows = await conn.fetch(query, table_name)
        return [dict(row) for row in rows]
    
    async def verify_table_counts(self, source_conn: asyncpg.Connection, 
                                sink_conn: asyncpg.Connection) -> Dict[str, Any]:
        """验证表行数"""
        self.logger.info("开始验证表行数...")
        
        source_tables = await self.get_table_list(source_conn)
        sink_tables = await self.get_table_list(sink_conn)
        
        # 检查表是否一致
        missing_in_sink = set(source_tables) - set(sink_tables)
        extra_in_sink = set(sink_tables) - set(source_tables)
        
        if missing_in_sink:
            self.logger.warning(f"SINK 中缺失表: {missing_in_sink}")
        if extra_in_sink:
            self.logger.warning(f"SINK 中额外表: {extra_in_sink}")
        
        # 验证共同表的行数
        common_tables = set(source_tables) & set(sink_tables)
        count_results = []
        all_match = True
        
        self.logger.info("表名\t\t源记录数\t目标记录数\t状态")
        self.logger.info("-" * 60)
        
        for table_name in sorted(common_tables):
            source_count = await self.get_table_row_count(source_conn, table_name)
            sink_count = await self.get_table_row_count(sink_conn, table_name)
            
            match = source_count == sink_count
            if not match:
                all_match = False
            
            status = "✓" if match else "✗"
            self.logger.info(f"{table_name:<20}\t{source_count}\t\t{sink_count}\t\t{status}")
            
            count_results.append({
                'table_name': table_name,
                'source_count': source_count,
                'sink_count': sink_count,
                'match': match,
                'difference': sink_count - source_count
            })
        
        self.logger.info("-" * 60)
        self.logger.info(f"行数验证: {'✓ 通过' if all_match else '✗ 失败'}")
        
        return {
            'all_match': all_match,
            'missing_in_sink': list(missing_in_sink),
            'extra_in_sink': list(extra_in_sink),
            'count_results': count_results
        }
    
    async def verify_table_schemas(self, source_conn: asyncpg.Connection, 
                                 sink_conn: asyncpg.Connection) -> Dict[str, Any]:
        """验证表结构"""
        self.logger.info("开始验证表结构...")
        
        source_tables = await self.get_table_list(source_conn)
        sink_tables = await self.get_table_list(sink_conn)
        common_tables = set(source_tables) & set(sink_tables)
        
        schema_results = []
        all_match = True
        
        for table_name in sorted(common_tables):
            source_schema = await self.get_table_schema(source_conn, table_name)
            sink_schema = await self.get_table_schema(sink_conn, table_name)
            
            # 比较列
            source_columns = {col['column_name']: col for col in source_schema}
            sink_columns = {col['column_name']: col for col in sink_schema}
            
            missing_in_sink = set(source_columns.keys()) - set(sink_columns.keys())
            extra_in_sink = set(sink_columns.keys()) - set(source_columns.keys())
            common_columns = set(source_columns.keys()) & set(sink_columns.keys())
            
            column_differences = []
            for col_name in common_columns:
                source_col = source_columns[col_name]
                sink_col = sink_columns[col_name]
                
                # 比较关键属性
                differences = []
                if source_col['data_type'] != sink_col['data_type']:
                    differences.append(f"data_type: {source_col['data_type']} != {sink_col['data_type']}")
                if source_col['is_nullable'] != sink_col['is_nullable']:
                    differences.append(f"is_nullable: {source_col['is_nullable']} != {sink_col['is_nullable']}")
                if source_col['character_maximum_length'] != sink_col['character_maximum_length']:
                    differences.append(f"max_length: {source_col['character_maximum_length']} != {sink_col['character_maximum_length']}")
                
                if differences:
                    column_differences.append({
                        'column_name': col_name,
                        'differences': differences
                    })
            
            table_match = not missing_in_sink and not extra_in_sink and not column_differences
            if not table_match:
                all_match = False
            
            schema_results.append({
                'table_name': table_name,
                'match': table_match,
                'missing_in_sink': list(missing_in_sink),
                'extra_in_sink': list(extra_in_sink),
                'column_differences': column_differences
            })
            
            if not table_match:
                self.logger.warning(f"表 {table_name} 结构不匹配:")
                if missing_in_sink:
                    self.logger.warning(f"  缺失列: {missing_in_sink}")
                if extra_in_sink:
                    self.logger.warning(f"  额外列: {extra_in_sink}")
                if column_differences:
                    self.logger.warning(f"  列差异: {column_differences}")
        
        self.logger.info(f"结构验证: {'✓ 通过' if all_match else '✗ 失败'}")
        
        return {
            'all_match': all_match,
            'schema_results': schema_results
        }
    
    async def verify_sample_data(self, source_conn: asyncpg.Connection, 
                               sink_conn: asyncpg.Connection, sample_ratio: float = 0.1) -> Dict[str, Any]:
        """验证抽样数据"""
        self.logger.info(f"开始验证抽样数据 (抽样比例: {sample_ratio})...")
        
        source_tables = await self.get_table_list(source_conn)
        sink_tables = await self.get_table_list(sink_conn)
        common_tables = set(source_tables) & set(sink_tables)
        
        sample_results = []
        all_match = True
        
        for table_name in sorted(common_tables):
            source_count = await self.get_table_row_count(source_conn, table_name)
            sink_count = await self.get_table_row_count(sink_conn, table_name)
            
            if source_count == 0:
                continue
            
            # 计算抽样数量
            sample_size = max(1, int(source_count * sample_ratio))
            
            try:
                # 从源表随机抽样
                source_query = f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT {sample_size}"
                source_rows = await source_conn.fetch(source_query)
                
                if not source_rows:
                    continue
                
                # 获取列名
                columns = list(source_rows[0].keys())
                
                # 在目标表中查找对应的行
                matches = 0
                for source_row in source_rows:
                    # 构建查询条件（假设有主键或唯一标识）
                    where_conditions = []
                    params = []
                    param_count = 0
                    
                    for col in columns:
                        if source_row[col] is not None:
                            param_count += 1
                            where_conditions.append(f"{col} = ${param_count}")
                            params.append(source_row[col])
                    
                    if where_conditions:
                        sink_query = f"SELECT COUNT(*) FROM {table_name} WHERE {' AND '.join(where_conditions)}"
                        sink_match_count = await sink_conn.fetchval(sink_query, *params)
                        if sink_match_count > 0:
                            matches += 1
                
                match_ratio = matches / len(source_rows) if source_rows else 0
                table_match = match_ratio >= 0.95  # 95% 匹配率认为通过
                
                if not table_match:
                    all_match = False
                
                sample_results.append({
                    'table_name': table_name,
                    'sample_size': len(source_rows),
                    'matches': matches,
                    'match_ratio': match_ratio,
                    'match': table_match
                })
                
                self.logger.info(f"表 {table_name}: 抽样 {len(source_rows)} 行，匹配 {matches} 行 ({match_ratio:.2%})")
                
            except Exception as e:
                self.logger.error(f"验证表 {table_name} 抽样数据失败: {e}")
                all_match = False
                sample_results.append({
                    'table_name': table_name,
                    'error': str(e),
                    'match': False
                })
        
        self.logger.info(f"抽样验证: {'✓ 通过' if all_match else '✗ 失败'}")
        
        return {
            'all_match': all_match,
            'sample_results': sample_results
        }
    
    async def verify_foreign_keys(self, sink_conn: asyncpg.Connection) -> Dict[str, Any]:
        """验证外键约束"""
        self.logger.info("开始验证外键约束...")
        
        query = """
        SELECT 
            tc.table_name,
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
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
        
        fk_constraints = await sink_conn.fetch(query)
        
        fk_results = []
        all_valid = True
        
        for fk in fk_constraints:
            table_name = fk['table_name']
            column_name = fk['column_name']
            foreign_table = fk['foreign_table_name']
            foreign_column = fk['foreign_column_name']
            
            # 检查外键约束是否有效
            check_query = f"""
            SELECT COUNT(*) 
            FROM {table_name} t1
            LEFT JOIN {foreign_table} t2 ON t1.{column_name} = t2.{foreign_column}
            WHERE t1.{column_name} IS NOT NULL AND t2.{foreign_column} IS NULL
            """
            
            try:
                invalid_count = await sink_conn.fetchval(check_query)
                is_valid = invalid_count == 0
                
                if not is_valid:
                    all_valid = False
                
                fk_results.append({
                    'table_name': table_name,
                    'column_name': column_name,
                    'foreign_table': foreign_table,
                    'foreign_column': foreign_column,
                    'invalid_count': invalid_count,
                    'valid': is_valid
                })
                
                if not is_valid:
                    self.logger.warning(f"外键约束无效: {table_name}.{column_name} -> {foreign_table}.{foreign_column} ({invalid_count} 个无效引用)")
                
            except Exception as e:
                self.logger.error(f"检查外键约束失败 {table_name}.{column_name}: {e}")
                all_valid = False
                fk_results.append({
                    'table_name': table_name,
                    'column_name': column_name,
                    'foreign_table': foreign_table,
                    'foreign_column': foreign_column,
                    'error': str(e),
                    'valid': False
                })
        
        self.logger.info(f"外键验证: {'✓ 通过' if all_valid else '✗ 失败'}")
        
        return {
            'all_valid': all_valid,
            'fk_results': fk_results
        }
    
    async def verify_sequences(self, source_conn: asyncpg.Connection, 
                             sink_conn: asyncpg.Connection) -> Dict[str, Any]:
        """验证序列值"""
        self.logger.info("开始验证序列值...")
        
        # 获取所有序列
        sequence_query = """
        SELECT sequence_name, last_value
        FROM information_schema.sequences
        WHERE sequence_schema = 'public'
        """
        
        source_sequences = await source_conn.fetch(sequence_query)
        sink_sequences = await sink_conn.fetch(sequence_query)
        
        source_seq_dict = {seq['sequence_name']: seq['last_value'] for seq in source_sequences}
        sink_seq_dict = {seq['sequence_name']: seq['last_value'] for seq in sink_sequences}
        
        sequence_results = []
        all_match = True
        
        for seq_name in source_seq_dict:
            source_value = source_seq_dict[seq_name]
            sink_value = sink_seq_dict.get(seq_name)
            
            if sink_value is None:
                self.logger.warning(f"序列 {seq_name} 在 SINK 中不存在")
                all_match = False
                sequence_results.append({
                    'sequence_name': seq_name,
                    'source_value': source_value,
                    'sink_value': None,
                    'match': False,
                    'reason': 'missing_in_sink'
                })
            else:
                # 序列值可能不同，但应该大于等于源值
                match = sink_value >= source_value
                if not match:
                    all_match = False
                
                sequence_results.append({
                    'sequence_name': seq_name,
                    'source_value': source_value,
                    'sink_value': sink_value,
                    'match': match,
                    'reason': 'value_mismatch' if not match else None
                })
                
                if not match:
                    self.logger.warning(f"序列 {seq_name} 值不匹配: 源={source_value}, 目标={sink_value}")
        
        self.logger.info(f"序列验证: {'✓ 通过' if all_match else '✗ 失败'}")
        
        return {
            'all_match': all_match,
            'sequence_results': sequence_results
        }
    
    async def run_full_verification(self, detailed: bool = False, sample_ratio: float = 0.1) -> Dict[str, Any]:
        """运行完整验证"""
        self.logger.info("开始完整验证...")
        
        source_conn = await self.get_connection('source')
        sink_conn = await self.get_connection('sink')
        
        try:
            verification_results = {
                'timestamp': datetime.now().isoformat(),
                'count_verification': None,
                'schema_verification': None,
                'sample_verification': None,
                'foreign_key_verification': None,
                'sequence_verification': None,
                'overall_success': False
            }
            
            # 1. 验证表行数
            count_result = await self.verify_table_counts(source_conn, sink_conn)
            verification_results['count_verification'] = count_result
            
            # 2. 验证表结构
            if detailed:
                schema_result = await self.verify_table_schemas(source_conn, sink_conn)
                verification_results['schema_verification'] = schema_result
            
            # 3. 验证抽样数据
            sample_result = await self.verify_sample_data(source_conn, sink_conn, sample_ratio)
            verification_results['sample_verification'] = sample_result
            
            # 4. 验证外键约束
            if detailed:
                fk_result = await self.verify_foreign_keys(sink_conn)
                verification_results['foreign_key_verification'] = fk_result
            
            # 5. 验证序列值
            if detailed:
                seq_result = await self.verify_sequences(source_conn, sink_conn)
                verification_results['sequence_verification'] = seq_result
            
            # 计算总体成功率
            all_checks = [
                count_result['all_match'],
                sample_result['all_match']
            ]
            
            if detailed:
                if verification_results['schema_verification']:
                    all_checks.append(verification_results['schema_verification']['all_match'])
                if verification_results['foreign_key_verification']:
                    all_checks.append(verification_results['foreign_key_verification']['all_valid'])
                if verification_results['sequence_verification']:
                    all_checks.append(verification_results['sequence_verification']['all_match'])
            
            verification_results['overall_success'] = all(all_checks)
            
            # 保存验证结果
            await self._save_verification_results(verification_results)
            
            self.logger.info(f"验证完成: {'✓ 通过' if verification_results['overall_success'] else '✗ 失败'}")
            
            return verification_results
            
        finally:
            await source_conn.close()
            await sink_conn.close()
    
    async def _save_verification_results(self, results: Dict[str, Any]):
        """保存验证结果"""
        results_file = self.config.get('verification', {}).get('results_file', 'verification_results.json')
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        self.logger.info(f"验证结果已保存到: {results_file}")

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库迁移验证工具")
    parser.add_argument("--config", "-c", required=True, help="配置文件路径")
    parser.add_argument("--detailed", "-d", action="store_true", help="执行详细验证")
    parser.add_argument("--sample-ratio", "-s", type=float, default=0.1, help="抽样验证比例")
    
    args = parser.parse_args()
    
    try:
        verifier = MigrationVerifier(args.config)
        results = await verifier.run_full_verification(args.detailed, args.sample_ratio)
        
        print(f"验证结果: {'通过' if results['overall_success'] else '失败'}")
        
        if not results['overall_success']:
            sys.exit(1)
            
    except Exception as e:
        print(f"验证失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())