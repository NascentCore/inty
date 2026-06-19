# Agent Management Scripts - 角色管理脚本

## copy_agent.py

Copy an agent from one PostgreSQL database to another.

### Usage

```bash
python copy_agent.py --name "Amber" \
  --source-pg "postgresql://user:pass@host:port/db" \
  --dest-pg "postgresql://user:pass@host:port/db"
```

### Options

- `--name`: Name of the agent to copy (required)
- `--source-pg`: Source PostgreSQL URL (required)
- `--dest-pg`: Destination PostgreSQL URL (required)
- `--force`: Overwrite if agent already exists in destination (optional)

### Examples

```bash
# Copy agent from dev to production
python copy_agent.py --name "Amber" \
  --source-pg "postgresql://postgres:sxwl666!@localhost:15432/devdb" \
  --dest-pg "postgresql://postgres:sxwl666!@localhost:15432/inty"

# Copy with force overwrite
python copy_agent.py --name "Amber" --force \
  --source-pg "postgresql://postgres:sxwl666!@localhost:15432/devdb" \
  --dest-pg "postgresql://postgres:sxwl666!@localhost:15432/inty"
```

### Notes

- The script uses SQLAlchemy with async sessions for database operations
- All agent fields are copied including character card data, settings, etc.
- The script checks for existing agents in the destination database
- Use `--force` flag to overwrite existing agents

## cleanup_animated_backgrounds.py

清理所有存储动图（gif/avif）而不是视频的agent的background_animated字段。

### Usage

```bash
python cleanup_animated_backgrounds.py
```

### Description

此脚本用于在系统从存储动图改为存储视频后，清理历史数据。脚本会：

- 查找所有 `background_animated` 字段包含动图URL（.gif 或 .avif）的agent
- 将这些字段清空（设置为 NULL）

### 识别规则

脚本通过以下规则识别动图URL：

- URL 以 `.gif` 或 `.avif` 结尾
- URL 路径中包含 `animated_images`（之前存储动图的路径）
- URL 中包含 `.gif` 或 `.avif` 格式标识

### 安全特性

- 默认执行 DRY RUN（预览模式），只显示将要清理的agent，不实际修改
- 需要两次确认（输入 'CLEANUP'）才会执行实际清理
- 显示详细的清理统计信息

### Examples

```bash
# 执行清理（会先显示预览，然后要求确认）
python cleanup_animated_backgrounds.py
```

### Notes

- 脚本使用异步数据库会话进行操作
- 只清理未删除的agent（`deleted_at IS NULL`）
- 清理操作不可逆，请谨慎使用
- 建议在生产环境使用前先在测试环境验证
