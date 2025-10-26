# 代理管理脚本

## 复制代理。py

将代理从一个 PostgreSQL 数据库复制到另一个数据库。＃＃＃最合适```bash
python copy_agent.py --name "Amber" \
  --source-pg "postgresql://user:pass@host:port/db" \
  --dest-pg "postgresql://user:pass@host:port/db"
```＃＃＃ 选项

-`--name`：要复制的代理人姓名（必填）
-`--source-pg`：源 PostgreSQL URL（简单）
-`--dest-pg`：目标PostgreSQL URL（必填）
-`--force`：如果代理已存在于目的地，则覆盖（可选）

### 示例```bash
# Copy agent from dev to production
python copy_agent.py --name "Amber" \
  --source-pg "postgresql://postgres:sxwl666!@localhost:15432/devdb" \
  --dest-pg "postgresql://postgres:sxwl666!@localhost:5432/inty"

# Copy with force overwrite
python copy_agent.py --name "Amber" --force \
  --source-pg "postgresql://postgres:sxwl666!@localhost:15432/devdb" \
  --dest-pg "postgresql://postgres:sxwl666!@localhost:5432/inty"
```### 注释

- 该脚本使用 SQLAlchemy 和异步会话进行数据库操作
- 复制所有代理字段，包括角色卡数据、设置等。- 该脚本检查目标数据库中的现有代理
- 使用`--force`标志覆盖现有代理