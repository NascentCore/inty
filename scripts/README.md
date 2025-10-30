# Scripts - 工具脚本

This directory contains utility scripts for the Inty backend.

## migrate_database.py

数据库迁移工具：从 SOURCE 数据库迁移数据到 SINK 数据库。

### 使用场景

适用于两个具有相同 schema 的数据库之间的数据迁移。SINK 数据库应该已经创建了所有表结构（通过 Alembic 迁移），但数据为空。

### 使用方法

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

### 选项说明

- `--source-url`: SOURCE 数据库连接 URL（必需）
- `--sink-url`: SINK 数据库连接 URL（必需）
- `--batch-size`: 批量处理大小，默认 1000
- `--keep-fk`: 保持外键约束（默认会禁用外键以加快迁移速度）

### 功能特性

- 自动发现所有表
- 批量迁移数据（避免内存溢出）
- 自动禁用/启用外键约束（加快迁移速度）
- 自动重置序列
- 迁移结果验证（比较行数）
- 详细的日志输出

### 注意事项

1. **备份数据**：迁移前请备份 SOURCE 和 SINK 数据库
2. **Schema 一致性**：确保两个数据库的 schema 完全一致
3. **网络连接**：确保能同时访问两个数据库服务器
4. **权限要求**：SOURCE 需要 SELECT 权限，SINK 需要 INSERT/UPDATE/DELETE 权限

### 详细文档

完整的迁移指南请参考：`DATABASE_MIGRATION_GUIDE.md`

## compress_agent_avatar_image.py

Compresses PNG avatar images to JPEG format and updates the database records.

### Usage

```bash
python scripts/compress_agent_avatar_image.py --pg_url "postgresql://user:password@host:port/database"
```

### Options

- `--pg_url`: PostgreSQL connection URL (required)
- `--quality`: JPEG compression quality 1-100 (default: 80)

### What it does

1. Connects to PostgreSQL database using the provided URL
2. Queries the `agents` table for records with PNG avatar URLs
3. Downloads each PNG image
4. Compresses PNG to JPEG with specified quality
5. Uploads JPEG to Google Cloud Storage in the same directory structure
6. Updates the database record with the new JPEG URL
7. Generates detailed logs of the process

### Requirements

- Valid `config.yaml` with GCS credentials configured
- PostgreSQL database access
- Internet access to download images
- PIL (Pillow) for image processing

### Example

```bash
# Compress with default quality (80)
python scripts/compress_agent_avatar_image.py --pg_url "postgresql://postgres:password@localhost:5432/inty_db"

# Compress with custom quality
python scripts/compress_agent_avatar_image.py --pg_url "postgresql://postgres:password@localhost:5432/inty_db" --quality 90
```
