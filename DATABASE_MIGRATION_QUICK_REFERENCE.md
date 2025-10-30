# 数据库迁移快速参考卡

> 详细文档请查看 `DATABASE_MIGRATION_GUIDE.md`

## 🚀 快速开始

### 方式 1：使用自动化脚本（推荐）

```bash
./scripts/migrate_database.sh \
    --source-host source-db.example.com \
    --source-db devdb \
    --source-user postgres \
    --sink-host sink-db.example.com \
    --sink-db devdb \
    --sink-user postgres \
    --parallel-jobs 4
```

### 方式 2：手动执行关键步骤

```bash
# 1. 导出数据
pg_dump -h SOURCE_HOST -p 5432 -U postgres \
    --format=custom --data-only --verbose \
    --file=data_only.dump devdb

# 2. 导入数据
pg_restore -h SINK_HOST -p 5432 -U postgres \
    --dbname=devdb --jobs=4 --verbose \
    --data-only --disable-triggers data_only.dump

# 3. 重置序列
psql -h SINK_HOST -U postgres -d devdb -c "
SELECT setval(sequence_name, (SELECT MAX(id) FROM table_name))
FROM information_schema.sequences;
"

# 4. 优化
psql -h SINK_HOST -U postgres -d devdb -c "ANALYZE; VACUUM;"
```

---

## 📋 常用命令

### 检查数据库大小
```bash
psql -h HOST -U USER -d DB -c "
SELECT pg_size_pretty(pg_database_size('DB'));
"
```

### 查看所有表的行数
```bash
psql -h HOST -U USER -d DB -c "
SELECT schemaname, tablename, n_live_tup 
FROM pg_stat_user_tables 
ORDER BY n_live_tup DESC;
"
```

### 比对两个数据库的行数
```bash
# SOURCE
psql -h SOURCE_HOST -U USER -d DB -c "
SELECT SUM(n_live_tup) FROM pg_stat_user_tables;
"

# SINK
psql -h SINK_HOST -U USER -d DB -c "
SELECT SUM(n_live_tup) FROM pg_stat_user_tables;
"
```

### 检查序列值
```bash
psql -h HOST -U USER -d DB -c "
SELECT sequence_name, last_value 
FROM information_schema.sequences seq
JOIN pg_sequences pgs ON seq.sequence_name = pgs.sequencename;
"
```

### 清空数据库（保留结构）
```bash
psql -h HOST -U USER -d DB << 'EOF'
DO $$ 
DECLARE r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
    LOOP
        EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $$;
EOF
```

---

## 🔧 故障排除

### 问题 1：外键约束违反
```bash
# 临时禁用约束
psql -h HOST -U USER -d DB -c "SET session_replication_role = 'replica';"

# 导入数据...

# 恢复约束
psql -h HOST -U USER -d DB -c "SET session_replication_role = 'origin';"
```

### 问题 2：序列值错误导致主键冲突
```bash
# 重置所有序列到表的最大 ID
psql -h HOST -U USER -d DB << 'EOF'
DO $$
DECLARE
    r RECORD;
    max_id BIGINT;
BEGIN
    FOR r IN (
        SELECT c.relname as seq_name, 
               t.relname as table_name,
               a.attname as column_name
        FROM pg_class c
        JOIN pg_depend d ON c.oid = d.objid
        JOIN pg_class t ON d.refobjid = t.oid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
        WHERE c.relkind = 'S'
    ) LOOP
        EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I', 
                      r.column_name, r.table_name) INTO max_id;
        EXECUTE format('SELECT setval(%L, %s, true)', r.seq_name, max_id + 1);
        RAISE NOTICE '已重置序列 % 到 %', r.seq_name, max_id + 1;
    END LOOP;
END $$;
EOF
```

### 问题 3：磁盘空间不足
```bash
# 使用管道直接传输，不保存中间文件
pg_dump -h SOURCE_HOST -U USER SOURCE_DB --data-only | \
    psql -h SINK_HOST -U USER SINK_DB

# 或使用压缩
pg_dump -h SOURCE_HOST -U USER SOURCE_DB --data-only | \
    gzip -c | ssh SINK_HOST "gunzip -c | psql -U USER SINK_DB"
```

### 问题 4：大表导入缓慢
```bash
# 临时调整 SINK 配置（在 psql 会话中）
SET maintenance_work_mem = '2GB';
SET max_wal_size = '10GB';
SET checkpoint_timeout = '30min';

# 然后导入数据...
```

---

## ⏱️ 性能优化技巧

### 1. 使用并行导入
```bash
pg_restore --jobs=8 ...  # 根据 CPU 核心数调整
```

### 2. 导入前禁用触发器
```bash
pg_restore --disable-triggers ...
```

### 3. 导入后重建索引和统计
```bash
psql -h HOST -U USER -d DB << 'EOF'
REINDEX DATABASE DB;
ANALYZE VERBOSE;
VACUUM ANALYZE;
EOF
```

### 4. 批量导出/导入特定表
```bash
# 导出
for table in users agents chats messages; do
    pg_dump -h SOURCE_HOST -U USER -d DB -t $table --data-only \
        --file=${table}.dump
done

# 导入
for table in users agents chats messages; do
    pg_restore -h SINK_HOST -U USER -d DB ${table}.dump
done
```

---

## 📊 验证检查清单

- [ ] 表行数一致
  ```bash
  # 对比 SOURCE 和 SINK 的总行数
  ```

- [ ] 序列值正确
  ```bash
  # 确保所有序列 > 表的最大 ID
  ```

- [ ] 外键约束有效
  ```bash
  psql -c "SELECT COUNT(*) FROM pg_constraint WHERE contype = 'f';"
  ```

- [ ] 应用功能测试
  - [ ] 用户登录
  - [ ] 创建新记录（测试序列）
  - [ ] 查询数据
  - [ ] 更新数据
  - [ ] 删除数据（如需要）

---

## 🔙 回滚操作

```bash
# 1. 停止应用
systemctl stop your-app

# 2. 恢复配置指向 SOURCE
# 编辑 config.yaml 或环境变量

# 3. 重启应用
systemctl start your-app

# 4. 清理 SINK（可选）
psql -h SINK_HOST -U USER -d DB << 'EOF'
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO USER;
EOF
```

---

## 📞 获取帮助

### 查看脚本帮助
```bash
./scripts/migrate_database.sh --help
```

### Dry Run 模式（测试不执行）
```bash
./scripts/migrate_database.sh --dry-run \
    --source-host ... --sink-host ...
```

### 跳过验证/优化（加快速度）
```bash
./scripts/migrate_database.sh --skip-verify --skip-optimize \
    --source-host ... --sink-host ...
```

---

## 📝 迁移前检查

```bash
# 1. 检查 PostgreSQL 版本一致性
psql -h SOURCE_HOST -c "SELECT version();"
psql -h SINK_HOST -c "SELECT version();"

# 2. 检查 schema 一致性
pg_dump -h SOURCE_HOST --schema-only --no-owner > source_schema.sql
pg_dump -h SINK_HOST --schema-only --no-owner > sink_schema.sql
diff source_schema.sql sink_schema.sql

# 3. 检查连接和权限
psql -h SOURCE_HOST -c "SELECT current_user, current_database();"
psql -h SINK_HOST -c "SELECT current_user, current_database();"

# 4. 估算迁移时间
# 数据量 < 10GB: ~30 分钟
# 数据量 10-50GB: ~1-2 小时
# 数据量 50-100GB: ~2-4 小时
# 数据量 > 100GB: ~4+ 小时
```

---

## 🎯 典型迁移流程

```
1. 准备阶段 (5-10 分钟)
   ├─ 检查环境
   ├─ 测试连接
   └─ 确认 SINK 为空

2. 导出阶段 (视数据量而定)
   ├─ 导出数据
   └─ 导出序列

3. 导入阶段 (视数据量而定)
   ├─ 禁用约束
   ├─ 导入数据
   ├─ 重置序列
   └─ 启用约束

4. 验证阶段 (5-10 分钟)
   ├─ 比对行数
   ├─ 检查序列
   └─ 验证约束

5. 优化阶段 (10-30 分钟)
   ├─ 更新统计
   └─ VACUUM

6. 测试阶段 (视应用复杂度)
   └─ 功能测试

总时间 = 数据导出时间 + 数据导入时间 + 1 小时（其他步骤）
```

---

## 💡 最佳实践

1. **在非高峰时段进行迁移**
2. **先在测试环境完整演练一次**
3. **保留 SOURCE 至少 7 天作为备份**
4. **记录所有操作和遇到的问题**
5. **准备回滚方案并测试**
6. **通知相关团队和用户（如需停机）**
7. **监控迁移过程的每个步骤**
8. **迁移后进行全面的功能测试**

---

**最后更新**: 2025-10-30
**维护者**: DevOps Team
**相关文档**: `DATABASE_MIGRATION_GUIDE.md`
