# 数据库迁移实战示例

## 场景说明

**背景**：我们需要将生产数据库从旧服务器迁移到新服务器

- **SOURCE（旧服务器）**
  - 主机: `old-db.inty.com`
  - 端口: `5432`
  - 数据库: `inty_prod`
  - 用户: `postgres`
  - 数据量: ~50GB
  - 表数量: 20+

- **SINK（新服务器）**
  - 主机: `new-db.inty.com`
  - 端口: `5432`
  - 数据库: `inty_prod`
  - 用户: `postgres`
  - 状态: 已运行 Alembic 迁移，schema 就绪，无数据

- **迁移窗口**: 周六凌晨 2:00-6:00（预计 4 小时）

---

## 方案一：使用自动化脚本（推荐）

### 步骤 1：准备工作（周五下班前完成）

```bash
# 1. 登录到跳板机或有权访问两个数据库的服务器
ssh ops@jumphost.inty.com

# 2. 检查脚本存在
cd /opt/inty/
ls -l scripts/migrate_database.sh

# 3. 测试数据库连接
export PGPASSWORD='your_password'

# 测试 SOURCE
psql -h old-db.inty.com -p 5432 -U postgres -d inty_prod -c "SELECT version();"

# 测试 SINK
psql -h new-db.inty.com -p 5432 -U postgres -d inty_prod -c "SELECT version();"

# 4. 检查 SOURCE 数据量
psql -h old-db.inty.com -p 5432 -U postgres -d inty_prod -c "
SELECT 
    pg_size_pretty(pg_database_size('inty_prod')) as db_size,
    (SELECT count(*) FROM pg_stat_user_tables) as table_count,
    (SELECT sum(n_live_tup) FROM pg_stat_user_tables) as total_rows;
"

# 输出示例：
#  db_size | table_count | total_rows 
# ---------+-------------+------------
#  48 GB   |          22 |   15234891

# 5. 确认 SINK 为空
psql -h new-db.inty.com -p 5432 -U postgres -d inty_prod -c "
SELECT sum(n_live_tup) FROM pg_stat_user_tables;
"
# 应该返回 0 或 NULL

# 6. 检查磁盘空间
df -h /tmp
# 确保至少有 100GB 可用空间（数据量的 2 倍）
```

### 步骤 2：Dry Run 演练（周五下班前）

```bash
# 执行 Dry Run，测试流程但不实际迁移
./scripts/migrate_database.sh \
    --source-host old-db.inty.com \
    --source-port 5432 \
    --source-db inty_prod \
    --source-user postgres \
    --sink-host new-db.inty.com \
    --sink-port 5432 \
    --sink-db inty_prod \
    --sink-user postgres \
    --backup-dir /data/db_migration_test \
    --parallel-jobs 8 \
    --dry-run

# 检查输出，确保所有检查都通过
# ✅ 依赖检查通过
# ✅ SOURCE 连接成功
# ✅ SINK 连接成功
```

### 步骤 3：执行迁移（周六凌晨）

```bash
# 1. 设置密码环境变量（避免多次输入）
export PGPASSWORD='your_password'

# 2. 停止应用服务器写入（重要！）
# 方式 A：停止应用
ssh app-server-1.inty.com "sudo systemctl stop inty-backend"
ssh app-server-2.inty.com "sudo systemctl stop inty-backend"

# 方式 B：将应用置于维护模式（如果支持）
# curl -X POST http://admin.inty.com/api/maintenance -d '{"enabled": true}'

# 3. 最后检查 SOURCE 数据
psql -h old-db.inty.com -p 5432 -U postgres -d inty_prod -c "
SELECT NOW() as snapshot_time, sum(n_live_tup) as total_rows 
FROM pg_stat_user_tables;
"
# 记录这个时间和行数，用于后续验证

# 4. 执行迁移脚本
./scripts/migrate_database.sh \
    --source-host old-db.inty.com \
    --source-port 5432 \
    --source-db inty_prod \
    --source-user postgres \
    --sink-host new-db.inty.com \
    --sink-port 5432 \
    --sink-db inty_prod \
    --sink-user postgres \
    --backup-dir /data/db_migration_$(date +%Y%m%d_%H%M%S) \
    --parallel-jobs 8

# 预计输出：
# ==========================================
#    数据库迁移工具 v1.0
# ==========================================
# 
# [INFO] 检查依赖工具...
# [SUCCESS] 依赖检查通过
# [INFO] 测试 SOURCE 数据库连接...
# [SUCCESS] SOURCE 连接成功
# [INFO] 测试 SINK 数据库连接...
# [SUCCESS] SINK 连接成功
# ...
# [INFO] 从 SOURCE 导出数据...
# [INFO] 数据库大小: 48 GB
# [INFO] 表数量: 22
# ... (导出进度，约 30-45 分钟)
# [SUCCESS] 数据导出完成
# [INFO] 导出文件大小: 28G
# ...
# [INFO] 导入数据到 SINK...
# [INFO] 使用 8 个并行任务
# ... (导入进度，约 45-60 分钟)
# [SUCCESS] 数据导入完成
# ...
# [INFO] 验证数据完整性...
# [INFO] SOURCE 总行数: 15234891
# [INFO] SINK 总行数: 15234891
# [SUCCESS] ✅ 总行数匹配
# ...
# [INFO] 优化目标数据库...
# [SUCCESS] 统计信息更新完成
# [SUCCESS] VACUUM 完成
# ...
# ==========================================
# [SUCCESS] 🎉 迁移完成！
# [INFO] 总耗时: 127 分 35 秒
# [INFO] 备份目录: /data/db_migration_20251030_020000
# ==========================================

# 5. 保存迁移报告
MIGRATION_DIR=$(ls -td /data/db_migration_* | head -1)
cat ${MIGRATION_DIR}/migration_report.txt
cat ${MIGRATION_DIR}/row_count_comparison.txt > /data/migration_report_$(date +%Y%m%d).txt
```

### 步骤 4：验证数据（迁移后立即执行）

```bash
# 1. 详细比对关键表
psql -h old-db.inty.com -U postgres -d inty_prod -c "
SELECT 'users' as table_name, COUNT(*) as count, 
       MIN(created_at) as earliest, MAX(created_at) as latest
FROM users
UNION ALL
SELECT 'agents', COUNT(*), MIN(created_at), MAX(created_at) FROM agents
UNION ALL
SELECT 'chats', COUNT(*), MIN(created_at), MAX(created_at) FROM chats
UNION ALL
SELECT 'messages', COUNT(*), MIN(created_at), MAX(created_at) FROM messages;
" > /tmp/source_key_tables.txt

psql -h new-db.inty.com -U postgres -d inty_prod -c "
SELECT 'users' as table_name, COUNT(*) as count, 
       MIN(created_at) as earliest, MAX(created_at) as latest
FROM users
UNION ALL
SELECT 'agents', COUNT(*), MIN(created_at), MAX(created_at) FROM agents
UNION ALL
SELECT 'chats', COUNT(*), MIN(created_at), MAX(created_at) FROM chats
UNION ALL
SELECT 'messages', COUNT(*), MIN(created_at), MAX(created_at) FROM messages;
" > /tmp/sink_key_tables.txt

diff /tmp/source_key_tables.txt /tmp/sink_key_tables.txt
# 应该没有差异

# 2. 验证外键完整性
psql -h new-db.inty.com -U postgres -d inty_prod << 'EOF'
-- 检查是否有孤立的外键引用
SELECT 'chats' as table_name, COUNT(*) as orphaned_records
FROM chats c
LEFT JOIN users u ON c.user_id = u.id
WHERE u.id IS NULL

UNION ALL

SELECT 'chats', COUNT(*)
FROM chats c
LEFT JOIN agents a ON c.agent_id = a.id
WHERE a.id IS NULL

UNION ALL

SELECT 'messages', COUNT(*)
FROM messages m
LEFT JOIN chats c ON m.chat_id = c.id
WHERE c.id IS NULL;
EOF
# 所有结果应该是 0

# 3. 验证序列值
psql -h new-db.inty.com -U postgres -d inty_prod << 'EOF'
SELECT 
    seq.sequence_name,
    pgs.last_value as current_seq_value,
    (SELECT MAX(id) FROM users WHERE seq.sequence_name = 'users_id_seq') as max_table_id,
    CASE 
        WHEN pgs.last_value >= COALESCE((SELECT MAX(id) FROM users WHERE seq.sequence_name = 'users_id_seq'), 0)
        THEN '✅ OK'
        ELSE '❌ ERROR'
    END as status
FROM information_schema.sequences seq
JOIN pg_sequences pgs ON seq.sequence_name = pgs.sequencename
WHERE sequence_schema = 'public'
ORDER BY sequence_name;
EOF
# 所有状态应该是 ✅ OK
```

### 步骤 5：应用测试（迁移后）

```bash
# 1. 临时更新一台应用服务器的配置，指向 SINK
ssh app-server-1.inty.com

# 备份原配置
sudo cp /opt/inty/devops/config.yaml /opt/inty/devops/config.yaml.backup

# 更新数据库配置
sudo nano /opt/inty/devops/config.yaml
# 修改 database.host 为 new-db.inty.com

# 2. 启动应用（只启动一台服务器进行测试）
sudo systemctl start inty-backend

# 3. 检查日志
sudo journalctl -u inty-backend -f

# 4. 健康检查
curl http://localhost:8000/health
# 期望输出: {"status": "healthy", "database": "connected"}

# 5. 功能测试
# 登录测试
curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "test@example.com", "password": "xxx"}'

# 获取用户信息
TOKEN="xxx"  # 从登录响应获取
curl http://localhost:8000/api/v1/users/me \
    -H "Authorization: Bearer $TOKEN"

# 创建聊天（测试写入和序列）
curl -X POST http://localhost:8000/api/v1/chats \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"agent_id": "xxx"}'

# 发送消息
curl -X POST http://localhost:8000/api/v1/chats/{chat_id}/messages \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"content": "Hello, this is a test"}'

# 6. 如果测试失败，立即回滚
# sudo systemctl stop inty-backend
# sudo mv /opt/inty/devops/config.yaml.backup /opt/inty/devops/config.yaml
# sudo systemctl start inty-backend
```

### 步骤 6：全量上线（测试通过后）

```bash
# 1. 更新所有应用服务器配置
for server in app-server-1 app-server-2 app-server-3; do
    ssh $server.inty.com << 'EOF'
        sudo cp /opt/inty/devops/config.yaml /opt/inty/devops/config.yaml.backup
        sudo sed -i 's/old-db.inty.com/new-db.inty.com/g' /opt/inty/devops/config.yaml
        sudo systemctl restart inty-backend
EOF
done

# 2. 验证所有服务器
for server in app-server-1 app-server-2 app-server-3; do
    echo "检查 $server..."
    curl -s http://$server.inty.com:8000/health | jq .
done

# 3. 恢复负载均衡
# （如果之前移除了维护模式或停用了负载均衡）

# 4. 监控
# 查看应用日志
# 查看数据库连接数和性能
psql -h new-db.inty.com -U postgres -d inty_prod -c "
SELECT count(*) as connections, usename, application_name 
FROM pg_stat_activity 
WHERE datname = 'inty_prod'
GROUP BY usename, application_name;
"

# 5. 通知团队
# 发送邮件/Slack 通知迁移完成
```

### 步骤 7：后续跟踪（迁移后 1-7 天）

```bash
# Day 1: 密切监控
# - 检查应用错误日志
# - 监控数据库性能
# - 用户反馈

# Day 3: 中期检查
# - 确认没有数据不一致问题
# - 性能对比（新 vs 旧）
# - 备份验证

# Day 7: 最终清理
# - 如果一切正常，可以考虑下线旧数据库
# - 但建议保留至少 30 天作为终极备份
# - 更新文档和配置管理
```

---

## 方案二：手动执行（学习用途）

### 完整手动流程

```bash
# 环境变量
SOURCE_HOST="old-db.inty.com"
SOURCE_DB="inty_prod"
SINK_HOST="new-db.inty.com"
SINK_DB="inty_prod"
BACKUP_DIR="/data/manual_migration_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
cd $BACKUP_DIR

# 1. 导出数据
echo "[$(date)] 开始导出数据..."
time pg_dump -h $SOURCE_HOST -U postgres \
    --format=custom \
    --data-only \
    --verbose \
    --file=data.dump \
    $SOURCE_DB 2>&1 | tee export.log

# 2. 导出序列
echo "[$(date)] 导出序列..."
psql -h $SOURCE_HOST -U postgres -d $SOURCE_DB -t -A << 'EOF' > sequences.sql
SELECT 'SELECT setval(' || quote_literal(sequence_schema || '.' || sequence_name) || ', ' || 
       'COALESCE((SELECT MAX(' || column_name || ') FROM ' || table_schema || '.' || table_name || '), 1), true);'
FROM information_schema.sequences seq
LEFT JOIN information_schema.columns col 
    ON col.column_default LIKE '%' || seq.sequence_name || '%'
WHERE sequence_schema = 'public';
EOF

# 3. 禁用 SINK 约束
echo "[$(date)] 禁用约束..."
psql -h $SINK_HOST -U postgres -d $SINK_DB << 'EOF'
SET session_replication_role = 'replica';
EOF

# 4. 导入数据
echo "[$(date)] 开始导入数据..."
time pg_restore -h $SINK_HOST -U postgres \
    --dbname=$SINK_DB \
    --jobs=8 \
    --verbose \
    --data-only \
    --disable-triggers \
    data.dump 2>&1 | tee import.log

# 5. 重置序列
echo "[$(date)] 重置序列..."
psql -h $SINK_HOST -U postgres -d $SINK_DB -f sequences.sql

# 6. 启用约束
echo "[$(date)] 启用约束..."
psql -h $SINK_HOST -U postgres -d $SINK_DB << 'EOF'
SET session_replication_role = 'origin';
EOF

# 7. 验证
echo "[$(date)] 验证数据..."
psql -h $SOURCE_HOST -U postgres -d $SOURCE_DB -t -c "
    SELECT SUM(n_live_tup) FROM pg_stat_user_tables;
" > source_count.txt

psql -h $SINK_HOST -U postgres -d $SINK_DB -t -c "
    SELECT SUM(n_live_tup) FROM pg_stat_user_tables;
" > sink_count.txt

echo "SOURCE 总行数: $(cat source_count.txt)"
echo "SINK 总行数: $(cat sink_count.txt)"

if diff -q source_count.txt sink_count.txt > /dev/null; then
    echo "✅ 验证通过：行数匹配"
else
    echo "❌ 验证失败：行数不匹配"
fi

# 8. 优化
echo "[$(date)] 优化数据库..."
psql -h $SINK_HOST -U postgres -d $SINK_DB -c "ANALYZE VERBOSE;"
psql -h $SINK_HOST -U postgres -d $SINK_DB -c "VACUUM ANALYZE;"

echo "[$(date)] 迁移完成！"
```

---

## 回滚场景示例

### 场景：发现迁移后数据不一致

```bash
# 1. 立即停止所有应用服务器
for server in app-server-1 app-server-2 app-server-3; do
    ssh $server.inty.com "sudo systemctl stop inty-backend"
done

# 2. 恢复配置指向 SOURCE
for server in app-server-1 app-server-2 app-server-3; do
    ssh $server.inty.com << 'EOF'
        sudo mv /opt/inty/devops/config.yaml.backup /opt/inty/devops/config.yaml
EOF
done

# 3. 重启应用
for server in app-server-1 app-server-2 app-server-3; do
    ssh $server.inty.com "sudo systemctl start inty-backend"
done

# 4. 验证回滚成功
curl http://app-server-1.inty.com:8000/health

# 5. 通知团队
echo "迁移已回滚到 SOURCE，系统已恢复正常"

# 6. 分析问题
# - 检查迁移日志
# - 比对数据差异
# - 修复问题后重新计划迁移
```

---

## 常见问题实战

### 问题 1：序列值导致插入失败

**症状**：
```
ERROR: duplicate key value violates unique constraint "users_pkey"
DETAIL: Key (id)=(12345) already exists.
```

**解决**：
```bash
psql -h new-db.inty.com -U postgres -d inty_prod << 'EOF'
-- 检查问题序列
SELECT sequence_name, last_value FROM pg_sequences WHERE sequencename = 'users_id_seq';

-- 检查表的最大 ID
SELECT MAX(id) FROM users;

-- 重置序列（假设最大 ID 是 15234891）
SELECT setval('users_id_seq', 15234891, true);

-- 验证
SELECT sequence_name, last_value FROM pg_sequences WHERE sequencename = 'users_id_seq';
EOF
```

### 问题 2：外键约束违反

**症状**：
```
ERROR: insert or update on table "messages" violates foreign key constraint "messages_chat_id_fkey"
```

**诊断**：
```bash
psql -h new-db.inty.com -U postgres -d inty_prod << 'EOF'
-- 查找孤立记录
SELECT m.id, m.chat_id, c.id as chat_exists
FROM messages m
LEFT JOIN chats c ON m.chat_id = c.id
WHERE c.id IS NULL
LIMIT 10;
EOF
```

**解决**：
```bash
# 如果发现孤立记录，需要重新迁移
# 或者删除孤立记录（慎重！）
```

---

## 性能监控

### 迁移过程中监控

```bash
# 终端 1: 监控导出进度
watch -n 5 "ls -lh /data/db_migration_*/data.dump"

# 终端 2: 监控数据库连接
watch -n 5 "psql -h new-db.inty.com -U postgres -d inty_prod -c '
SELECT count(*) as connections, state 
FROM pg_stat_activity 
WHERE datname = '\''inty_prod'\'' 
GROUP BY state;
'"

# 终端 3: 监控系统资源
watch -n 5 "free -h && echo && df -h /data && echo && top -bn1 | head -20"
```

### 迁移后性能对比

```bash
# 查询性能
psql -h old-db.inty.com -U postgres -d inty_prod -c "
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';
" > old_perf.txt

psql -h new-db.inty.com -U postgres -d inty_prod -c "
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';
" > new_perf.txt

diff old_perf.txt new_perf.txt
```

---

## 总结

本次迁移预计：
- **准备时间**: 1 小时
- **迁移时间**: 2-3 小时
- **验证时间**: 30 分钟
- **总停机时间**: ~4 小时

关键成功因素：
1. ✅ 充分的准备和演练
2. ✅ 详细的检查清单
3. ✅ 完善的回滚方案
4. ✅ 团队沟通和协作
5. ✅ 持续的监控和验证

**注意**: 这是一个真实场景的示例，实际执行时请根据具体情况调整参数和步骤。
