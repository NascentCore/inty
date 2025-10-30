# 数据库迁移指南：从 SOURCE 到 SINK

本指南提供了在具有相同 schema 的数据库服务器之间进行完整数据迁移的详细步骤。

## 前提条件

- SOURCE 和 SINK 数据库具有完全相同的表结构和列定义
- SINK 数据库为空（仅有表结构，无数据）
- 两个数据库服务器都支持 PostgreSQL
- 具有足够的网络带宽和存储空间
- 具有数据库管理员权限

## 迁移方法选择

### 方法一：使用 pg_dump/pg_restore（推荐）
适用于：数据量较大，需要完整迁移的场景

### 方法二：使用自定义脚本
适用于：需要选择性迁移，或需要数据转换的场景

### 方法三：使用 Alembic + 自定义脚本
适用于：需要保持迁移历史，或需要复杂数据处理的场景

## 方法一：使用 pg_dump/pg_restore

### 步骤 1：准备工作

1. **备份 SOURCE 数据库**
```bash
# 创建备份目录
mkdir -p /tmp/db_migration_backup
cd /tmp/db_migration_backup

# 备份 SOURCE 数据库
pg_dump -h SOURCE_HOST -p SOURCE_PORT -U SOURCE_USER -d SOURCE_DB \
  --verbose --clean --no-owner --no-privileges \
  --file=source_backup.sql
```

2. **验证 SINK 数据库为空**
```bash
# 连接到 SINK 数据库
psql -h SINK_HOST -p SINK_PORT -U SINK_USER -d SINK_DB

# 检查所有表是否为空
\dt
SELECT schemaname, tablename, n_tup_ins as row_count 
FROM pg_stat_user_tables 
WHERE n_tup_ins > 0;
```

### 步骤 2：执行迁移

1. **直接恢复数据**
```bash
# 将数据恢复到 SINK 数据库
psql -h SINK_HOST -p SINK_PORT -U SINK_USER -d SINK_DB \
  -f source_backup.sql
```

2. **或者使用 pg_restore（如果使用自定义格式）**
```bash
# 使用自定义格式备份
pg_dump -h SOURCE_HOST -p SOURCE_PORT -U SOURCE_USER -d SOURCE_DB \
  --verbose --clean --no-owner --no-privileges \
  --format=custom --file=source_backup.dump

# 恢复到 SINK 数据库
pg_restore -h SINK_HOST -p SINK_PORT -U SINK_USER -d SINK_DB \
  --verbose --clean --no-owner --no-privileges \
  source_backup.dump
```

### 步骤 3：验证迁移结果

```bash
# 连接到 SINK 数据库验证
psql -h SINK_HOST -p SINK_PORT -U SINK_USER -d SINK_DB

# 检查表数量
SELECT COUNT(*) as table_count FROM information_schema.tables 
WHERE table_schema = 'public';

# 检查总记录数
SELECT 
  schemaname,
  tablename,
  n_tup_ins as row_count
FROM pg_stat_user_tables 
ORDER BY n_tup_ins DESC;

# 检查关键表的数据
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM agents;
SELECT COUNT(*) FROM chats;
```

## 方法二：使用自定义脚本

### 步骤 1：创建迁移脚本

创建 `database_migration.py`：

```python
#!/usr/bin/env python3
"""
数据库迁移脚本
用于在具有相同 schema 的数据库之间迁移数据
"""

import asyncio
import asyncpg
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import yaml

class DatabaseMigrator:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('migration.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    async def get_connection(self, env: str) -> asyncpg.Connection:
        """获取数据库连接"""
        db_config = self.config['environments'][env]['database']
        return await asyncpg.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['db']
        )
    
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
    
    async def migrate_table(self, source_conn: asyncpg.Connection, 
                          sink_conn: asyncpg.Connection, table_name: str):
        """迁移单个表"""
        self.logger.info(f"开始迁移表: {table_name}")
        
        # 获取表列信息
        columns = await self.get_table_columns(source_conn, table_name)
        column_names = [col['column_name'] for col in columns]
        
        # 检查 SINK 表是否为空
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        sink_count = await sink_conn.fetchval(count_query)
        
        if sink_count > 0:
            self.logger.warning(f"表 {table_name} 在 SINK 中不为空，跳过迁移")
            return
        
        # 从 SOURCE 读取数据
        select_query = f"SELECT * FROM {table_name}"
        rows = await source_conn.fetch(select_query)
        
        if not rows:
            self.logger.info(f"表 {table_name} 在 SOURCE 中为空")
            return
        
        # 构建插入语句
        placeholders = [f"${i+1}" for i in range(len(column_names))]
        insert_query = f"""
        INSERT INTO {table_name} ({', '.join(column_names)})
        VALUES ({', '.join(placeholders)})
        """
        
        # 批量插入数据
        batch_size = self.config.get('migration', {}).get('batch_size', 1000)
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            values_list = []
            for row in batch:
                values_list.append([row[col] for col in column_names])
            
            await sink_conn.executemany(insert_query, values_list)
            self.logger.info(f"已迁移 {min(i + batch_size, len(rows))}/{len(rows)} 行")
        
        self.logger.info(f"表 {table_name} 迁移完成，共 {len(rows)} 行")
    
    async def migrate_all_tables(self):
        """迁移所有表"""
        source_conn = await self.get_connection('source')
        sink_conn = await self.get_connection('sink')
        
        try:
            # 获取所有表
            tables = await self.get_table_list(source_conn)
            self.logger.info(f"发现 {len(tables)} 个表需要迁移")
            
            # 按依赖顺序迁移（先迁移没有外键的表）
            migration_order = self._get_migration_order(tables)
            
            for table_name in migration_order:
                try:
                    await self.migrate_table(source_conn, sink_conn, table_name)
                except Exception as e:
                    self.logger.error(f"迁移表 {table_name} 失败: {e}")
                    if not self.config.get('migration', {}).get('continue_on_error', True):
                        raise
            
            self.logger.info("所有表迁移完成")
            
        finally:
            await source_conn.close()
            await sink_conn.close()
    
    def _get_migration_order(self, tables: List[str]) -> List[str]:
        """获取迁移顺序（简单实现，可根据外键关系优化）"""
        # 这里可以根据外键关系优化顺序
        # 暂时按字母顺序，实际项目中需要分析表依赖关系
        return sorted(tables)

async def main():
    migrator = DatabaseMigrator('migration_config.yaml')
    await migrator.migrate_all_tables()

if __name__ == "__main__":
    asyncio.run(main())
```

### 步骤 2：创建配置文件

创建 `migration_config.yaml`：

```yaml
# 数据库迁移配置文件
environments:
  source:
    name: "源数据库"
    database:
      host: "SOURCE_HOST"
      port: 5432
      user: "SOURCE_USER"
      password: "SOURCE_PASSWORD"
      db: "SOURCE_DB"

  sink:
    name: "目标数据库"
    database:
      host: "SINK_HOST"
      port: 5432
      user: "SINK_USER"
      password: "SINK_PASSWORD"
      db: "SINK_DB"

migration:
  batch_size: 1000  # 批量插入大小
  continue_on_error: true  # 遇到错误是否继续
  verify_data: true  # 是否验证数据完整性

logging:
  level: "INFO"
  file: "migration.log"
```

### 步骤 3：执行迁移

```bash
# 安装依赖
pip install asyncpg pyyaml

# 执行迁移
python database_migration.py
```

## 方法三：使用 Alembic + 自定义脚本

### 步骤 1：创建 Alembic 迁移脚本

```python
# 在 alembic/versions/ 目录下创建新文件
# 例如：20250101_120000_migrate_data_from_source.py

"""Migrate data from SOURCE to SINK

Revision ID: migrate_data_001
Revises: [previous_revision]
Create Date: 2025-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = 'migrate_data_001'
down_revision = '[previous_revision]'
branch_labels = None
depends_on = None

def upgrade():
    """迁移数据从 SOURCE 到 SINK"""
    # 这里可以添加数据迁移逻辑
    # 例如：从外部数据源导入数据
    pass

def downgrade():
    """回滚数据迁移"""
    # 清理迁移的数据
    pass
```

### 步骤 2：创建数据迁移脚本

```python
# scripts/migrate_database_data.py
import asyncio
import asyncpg
from app.core.config import global_config_loaded_from_config_yaml

async def migrate_database_data():
    """使用 Alembic 迁移数据"""
    # 连接到源数据库
    source_url = "postgresql://SOURCE_USER:SOURCE_PASSWORD@SOURCE_HOST:SOURCE_PORT/SOURCE_DB"
    sink_url = global_config_loaded_from_config_yaml.database.url
    
    source_conn = await asyncpg.connect(source_url)
    sink_conn = await asyncpg.connect(sink_url)
    
    try:
        # 获取所有表
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
        
        tables = await source_conn.fetch(tables_query)
        
        for table in tables:
            table_name = table['table_name']
            print(f"迁移表: {table_name}")
            
            # 检查目标表是否为空
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            sink_count = await sink_conn.fetchval(count_query)
            
            if sink_count > 0:
                print(f"表 {table_name} 不为空，跳过")
                continue
            
            # 迁移数据
            data_query = f"SELECT * FROM {table_name}"
            rows = await source_conn.fetch(data_query)
            
            if not rows:
                print(f"表 {table_name} 为空，跳过")
                continue
            
            # 获取列名
            columns = list(rows[0].keys())
            placeholders = [f"${i+1}" for i in range(len(columns))]
            
            insert_query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            """
            
            # 批量插入
            values_list = []
            for row in rows:
                values_list.append([row[col] for col in columns])
            
            await sink_conn.executemany(insert_query, values_list)
            print(f"表 {table_name} 迁移完成，共 {len(rows)} 行")
    
    finally:
        await source_conn.close()
        await sink_conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_database_data())
```

## 验证迁移结果

### 数据完整性验证

```python
# scripts/verify_migration.py
import asyncio
import asyncpg

async def verify_migration():
    """验证迁移结果"""
    source_url = "postgresql://SOURCE_USER:SOURCE_PASSWORD@SOURCE_HOST:SOURCE_PORT/SOURCE_DB"
    sink_url = "postgresql://SINK_USER:SINK_PASSWORD@SINK_HOST:SINK_PORT/SINK_DB"
    
    source_conn = await asyncpg.connect(source_url)
    sink_conn = await asyncpg.connect(sink_url)
    
    try:
        # 获取所有表
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
        
        tables = await source_conn.fetch(tables_query)
        
        print("表名\t\t源记录数\t目标记录数\t状态")
        print("-" * 50)
        
        all_match = True
        for table in tables:
            table_name = table['table_name']
            
            # 统计记录数
            source_count = await source_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            sink_count = await sink_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            
            status = "✓" if source_count == sink_count else "✗"
            if source_count != sink_count:
                all_match = False
            
            print(f"{table_name:<20}\t{source_count}\t\t{sink_count}\t\t{status}")
        
        print("-" * 50)
        print(f"总体状态: {'✓ 通过' if all_match else '✗ 失败'}")
        
    finally:
        await source_conn.close()
        await sink_conn.close()

if __name__ == "__main__":
    asyncio.run(verify_migration())
```

## 最佳实践

### 1. 迁移前准备

- **备份数据**：在迁移前备份 SOURCE 数据库
- **测试环境验证**：先在测试环境验证迁移脚本
- **检查依赖关系**：确保 SINK 数据库的表结构完全匹配
- **权限检查**：确保有足够的数据库权限

### 2. 迁移过程

- **分批处理**：对于大表，使用分批处理避免内存溢出
- **事务控制**：使用事务确保数据一致性
- **错误处理**：实现完善的错误处理和回滚机制
- **进度监控**：记录迁移进度，便于问题排查

### 3. 迁移后验证

- **数据完整性**：验证所有表的数据行数
- **关键数据检查**：检查重要业务数据是否正确
- **性能测试**：验证 SINK 数据库的性能
- **应用测试**：确保应用程序能正常访问新数据库

### 4. 回滚计划

- **保留备份**：保留 SOURCE 数据库的完整备份
- **回滚脚本**：准备回滚脚本以应对迁移失败
- **监控告警**：设置监控告警及时发现问题

## 常见问题解决

### 1. 外键约束问题

```sql
-- 临时禁用外键约束
SET session_replication_role = replica;

-- 迁移数据...

-- 重新启用外键约束
SET session_replication_role = DEFAULT;
```

### 2. 序列值不同步

```sql
-- 重置序列值
SELECT setval('table_id_seq', (SELECT MAX(id) FROM table_name));
```

### 3. 权限问题

```sql
-- 授予必要权限
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO user_name;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO user_name;
```

## 总结

选择适合的迁移方法：

- **小到中等数据量**：使用方法一（pg_dump/pg_restore）
- **需要选择性迁移**：使用方法二（自定义脚本）
- **需要保持迁移历史**：使用方法三（Alembic + 自定义脚本）

无论选择哪种方法，都要确保：
1. 充分的测试和验证
2. 完整的备份和回滚计划
3. 详细的迁移日志
4. 迁移后的数据完整性验证