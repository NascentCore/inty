# 数据库迁移指南：从 SOURCE 到 SINK

本文档提供从 SOURCE 数据库服务器迁移数据到 SINK 数据库服务器的详细步骤。两个数据库服务器具有完全相同的 schema（表结构），SINK 数据库为空（只有表结构但没有数据）。

## 前提条件

1. **确认 Schema 一致性**
   - SOURCE 和 SINK 数据库具有完全相同的表结构
   - SINK 数据库已创建所有表（通过 Alembic 迁移或手动创建）
   - 确认没有外键约束冲突

2. **网络连接**
   - 能够同时访问 SOURCE 和 SINK 数据库服务器
   - 具有足够的网络带宽用于数据传输

3. **权限要求**
   - SOURCE 数据库：需要 SELECT 权限
   - SINK 数据库：需要 INSERT, UPDATE, DELETE 权限

4. **备份**
   - **强烈建议**：在开始迁移前备份 SOURCE 数据库（以防万一）
   - **强烈建议**：在开始迁移前备份 SINK 数据库（虽然为空，但可作为回滚点）

## 方法一：使用 pg_dump 和 pg_restore（推荐）

### 优点
- PostgreSQL 官方工具，稳定可靠
- 支持自定义格式，可压缩
- 可以只导出数据，不导出 schema
- 支持并行恢复，速度快

### 步骤

#### 1. 从 SOURCE 导出数据（仅数据，不包含 schema）

```bash
# 导出为 SQL 格式（简单但较大）
pg_dump -h SOURCE_HOST -p SOURCE_PORT -U SOURCE_USER -d SOURCE_DB \
  --data-only --no-owner --no-acl \
  -f migration_data.sql

# 或导出为自定义格式（压缩，推荐）
pg_dump -h SOURCE_HOST -p SOURCE_PORT -U SOURCE_USER -d SOURCE_DB \
  --data-only --no-owner --no-acl \
  -Fc -f migration_data.dump
```

#### 2. 验证导出文件

```bash
# 查看 SQL 文件大小和行数
wc -l migration_data.sql
ls -lh migration_data.sql

# 或查看自定义格式文件信息
pg_restore --list -f migration_data.dump | head -20
```

#### 3. 导入数据到 SINK

**如果使用 SQL 格式：**

```bash
# 方法 A：使用 psql（简单直接）
psql -h SINK_HOST -p SINK_PORT -U SINK_USER -d SINK_DB \
  -f migration_data.sql

# 方法 B：使用 pg_restore（更快，支持并行）
pg_restore -h SINK_HOST -p SINK_PORT -U SINK_USER -d SINK_DB \
  --no-owner --no-acl \
  -j 4 migration_data.sql
```

**如果使用自定义格式（推荐）：**

```bash
# 并行恢复（使用 4 个线程，可根据服务器性能调整）
pg_restore -h SINK_HOST -p SINK_PORT -U SINK_USER -d SINK_DB \
  --no-owner --no-acl \
  --verbose \
  -j 4 \
  migration_data.dump
```

#### 4. 验证迁移结果

```bash
# 连接到 SINK 数据库，检查数据量
psql -h SINK_HOST -p SINK_PORT -U SINK_USER -d SINK_DB

# 在 psql 中执行以下查询
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
  (SELECT COUNT(*) FROM information_schema.tables 
   WHERE table_schema = schemaname AND table_name = tablename) as row_count
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### 5. 处理序列（Sequences）

如果表中有自增主键，需要重置序列：

```bash
# 连接到 SINK 数据库
psql -h SINK_HOST -p SINK_PORT -U SINK_USER -d SINK_DB

# 生成重置序列的 SQL（需要根据实际情况调整）
SELECT 'SELECT setval(''' || sequence_name || ''', (SELECT MAX(id) FROM ' || 
       replace(sequence_name, '_id_seq', '') || '));' as sql
FROM information_schema.sequences
WHERE sequence_schema = 'public';
```

执行生成的 SQL 语句来重置序列。

## 方法二：使用 Python 脚本（适用于需要数据转换的场景）

如果需要数据转换、过滤或验证，可以使用 Python 脚本。

### 优点
- 可以添加数据转换逻辑
- 可以添加数据验证
- 可以跳过某些表或记录
- 可以显示详细的迁移进度

### 步骤

#### 1. 使用项目提供的迁移脚本

项目已提供了一个完整的迁移脚本：`scripts/migrate_database.py`

#### 2. 运行迁移脚本

```bash
# 基本用法
python scripts/migrate_database.py \
  --source-url "postgresql+asyncpg://SOURCE_USER:SOURCE_PASSWORD@SOURCE_HOST:SOURCE_PORT/SOURCE_DB" \
  --sink-url "postgresql+asyncpg://SINK_USER:SINK_PASSWORD@SINK_HOST:SINK_PORT/SINK_DB"

# 自定义批量大小（默认 1000）
python scripts/migrate_database.py \
  --source-url "postgresql+asyncpg://..." \
  --sink-url "postgresql+asyncpg://..." \
  --batch-size 2000

# 保持外键约束（默认会禁用外键以加快迁移）
python scripts/migrate_database.py \
  --source-url "postgresql+asyncpg://..." \
  --sink-url "postgresql+asyncpg://..." \
  --keep-fk
```

#### 3. 脚本功能说明

脚本会自动执行以下操作：
- 自动发现所有表
- 批量迁移数据（可配置批量大小）
- 自动禁用/启用外键约束（加快迁移速度）
- 自动重置序列
- 验证迁移结果（比较行数）

#### 4. 查看脚本源码

完整的脚本实现请查看：`scripts/migrate_database.py`

脚本包含以下功能：
- 自动发现所有表
- 批量迁移数据
- 外键约束管理
- 序列重置
- 迁移结果验证
- 详细的日志输出

## 方法三：使用 COPY 命令（最快，适用于大数据量）

### 步骤

```bash
# 1. 导出到 CSV（针对每个表）
psql -h SOURCE_HOST -p SOURCE_PORT -U SOURCE_USER -d SOURCE_DB \
  -c "\COPY table_name TO 'table_name.csv' CSV HEADER"

# 2. 导入到 SINK
psql -h SINK_HOST -p SINK_PORT -U SINK_USER -d SINK_DB \
  -c "\COPY table_name FROM 'table_name.csv' CSV HEADER"
```

**注意**：需要为每个表分别执行，或编写脚本批量处理。

## 迁移后验证清单

完成迁移后，请执行以下验证：

### 1. 数据完整性检查

```sql
-- 比较两个数据库的表行数
-- 在 SOURCE 数据库执行
SELECT 
  schemaname,
  tablename,
  (SELECT COUNT(*) FROM information_schema.tables 
   WHERE table_schema = schemaname AND table_name = tablename) as row_count
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- 在 SINK 数据库执行相同的查询，对比结果
```

### 2. 关键表验证

```sql
-- 验证关键业务表的数据
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM agents;
SELECT COUNT(*) FROM chats;
SELECT COUNT(*) FROM messages;

-- 验证数据一致性（抽样检查）
SELECT id, created_at FROM users ORDER BY id LIMIT 10;
SELECT id, created_at FROM agents ORDER BY id LIMIT 10;
```

### 3. 外键完整性检查

```sql
-- 检查是否有外键约束违反
SELECT 
  conname as constraint_name,
  conrelid::regclass as table_name
FROM pg_constraint
WHERE contype = 'f'
AND NOT pg_check_constraint(oid);
```

### 4. 索引检查

```sql
-- 确保所有索引都已创建
SELECT 
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

### 5. 序列检查

```sql
-- 检查序列当前值
SELECT 
  sequence_name,
  last_value
FROM information_schema.sequences
WHERE sequence_schema = 'public';
```

## 常见问题处理

### 问题 1：外键约束错误

**错误信息**：`ERROR: insert or update on table "xxx" violates foreign key constraint`

**解决方案**：
- 方法一：按照外键依赖顺序迁移表（先迁移被引用表，再迁移引用表）
- 方法二：迁移前禁用外键约束，迁移后重新启用（见方法二）

### 问题 2：序列未重置

**错误信息**：插入数据时主键冲突

**解决方案**：重置序列（见方法一的步骤 5）

### 问题 3：字符编码问题

**错误信息**：`ERROR: invalid byte sequence for encoding "UTF8"`

**解决方案**：
```bash
# 确保数据库编码一致
psql -h SOURCE_HOST -U SOURCE_USER -d SOURCE_DB -c "SHOW server_encoding;"
psql -h SINK_HOST -U SINK_USER -d SINK_DB -c "SHOW server_encoding;"

# 如果不同，导出时指定编码
pg_dump ... --encoding=UTF8
```

### 问题 4：大事务超时

**错误信息**：`ERROR: canceling statement due to statement timeout`

**解决方案**：
- 增加超时时间：`SET statement_timeout = '1h';`
- 使用批量提交（Python 脚本方法）
- 使用并行恢复（pg_restore -j）

### 问题 5：磁盘空间不足

**解决方案**：
- 检查可用磁盘空间：`df -h`
- 使用压缩格式（pg_dump -Fc）
- 清理临时文件

## 性能优化建议

1. **并行处理**：使用 `pg_restore -j N` 并行恢复（N 为 CPU 核心数）
2. **批量大小**：Python 脚本中调整 `batch_size` 参数
3. **网络优化**：如果 SOURCE 和 SINK 在同一网络，使用内网地址
4. **禁用日志**：迁移期间可以临时禁用某些日志记录
5. **调整 PostgreSQL 配置**：
   - `shared_buffers`
   - `work_mem`
   - `maintenance_work_mem`

## 回滚方案

如果迁移失败需要回滚：

```bash
# 1. 清空 SINK 数据库所有表数据
psql -h SINK_HOST -p SINK_PORT -U SINK_USER -d SINK_DB << EOF
DO \$\$ 
DECLARE 
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END \$\$;
EOF

# 2. 重新执行迁移
```

## 联系与支持

如有问题，请查看：
- Alembic 迁移文档：`alembic/README.md`
- 数据库配置：`devops/config.yaml.example`
- 项目文档：`README.md`
