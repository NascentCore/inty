# 数据库迁移指南：SOURCE → SINK

本指南用于将数据从源数据库服务器（SOURCE）迁移到目标数据库服务器（SINK），两者具有相同的 schema 结构。

## 前置条件

- ✅ SINK 数据库已创建所有表结构（schema 与 SOURCE 完全一致）
- ✅ SINK 数据库为空（无数据）
- ✅ 拥有两个数据库的超级用户或足够权限
- ✅ 网络连接稳定，两个服务器可互相访问或可通过中间机器访问
- ✅ 有足够的磁盘空间存储导出文件

## 迁移策略选择

根据数据量和停机时间要求选择合适的方案：

### 方案 A：pg_dump/pg_restore（推荐，适合中小型数据库）
- **优点**：最可靠、最安全、自动处理依赖关系
- **适用**：数据量 < 100GB，可接受短暂停机

### 方案 B：逻辑复制（适合大型数据库，需要最小停机）
- **优点**：近实时同步，停机时间最短
- **适用**：数据量 > 100GB，要求最小停机时间

### 方案 C：表级 COPY（适合特定场景）
- **优点**：灵活可控
- **适用**：只需迁移部分表，或需要数据转换

---

## 🎯 方案 A：使用 pg_dump/pg_restore（推荐）

### 第 1 步：准备工作

#### 1.1 确认环境信息
```bash
# 记录数据库连接信息
SOURCE_HOST="source-db.example.com"
SOURCE_PORT="5432"
SOURCE_DB="devdb"
SOURCE_USER="postgres"

SINK_HOST="sink-db.example.com"
SINK_PORT="5432"
SINK_DB="devdb"
SINK_USER="postgres"
```

#### 1.2 检查 SOURCE 数据库大小
```bash
psql -h $SOURCE_HOST -p $SOURCE_PORT -U $SOURCE_USER -d $SOURCE_DB -c "
SELECT 
    pg_size_pretty(pg_database_size('$SOURCE_DB')) as db_size,
    (SELECT count(*) FROM pg_stat_user_tables) as table_count;
"
```

#### 1.3 检查 SINK 数据库是否为空
```bash
psql -h $SINK_HOST -p $SINK_PORT -U $SINK_USER -d $SINK_DB -c "
SELECT schemaname, tablename, 
       (xpath('/row/cnt/text()', xml_count))[1]::text::int as row_count
FROM (
  SELECT schemaname, tablename, 
         query_to_xml(format('select count(*) as cnt from %I.%I', schemaname, tablename), false, true, '') as xml_count
  FROM pg_tables
  WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
) sub
ORDER BY schemaname, tablename;
"
```

> ⚠️ **重要**：如果 SINK 有数据，请先清理或确认是否可以覆盖

#### 1.4 创建备份目录
```bash
BACKUP_DIR="/tmp/db_migration_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
cd $BACKUP_DIR
```

### 第 2 步：从 SOURCE 导出数据

#### 2.1 导出完整数据（仅数据，不含 schema）
```bash
# 使用 custom 格式，支持并行恢复和选择性恢复
pg_dump -h $SOURCE_HOST -p $SOURCE_PORT -U $SOURCE_USER \
    --format=custom \
    --data-only \
    --verbose \
    --file="${BACKUP_DIR}/data_only.dump" \
    $SOURCE_DB
```

**参数说明**：
- `--format=custom`：使用自定义格式，支持压缩和并行
- `--data-only`：只导出数据，不导出 schema（因为 SINK 已有 schema）
- `--verbose`：显示详细进度
- `--file`：输出文件路径

#### 2.2 导出序列（sequences）当前值
```bash
pg_dump -h $SOURCE_HOST -p $SOURCE_PORT -U $SOURCE_USER \
    --format=plain \
    --data-only \
    --table='*_seq' \
    --file="${BACKUP_DIR}/sequences.sql" \
    $SOURCE_DB
```

或者手动导出序列值：
```bash
psql -h $SOURCE_HOST -p $SOURCE_PORT -U $SOURCE_USER -d $SOURCE_DB -t -A -F"," -c "
SELECT 'SELECT setval(''' || sequence_schema || '.' || sequence_name || ''', ' || 
       '(SELECT max(' || column_name || ') FROM ' || table_schema || '.' || table_name || '), true);'
FROM information_schema.sequences
WHERE sequence_schema NOT IN ('pg_catalog', 'information_schema');
" > ${BACKUP_DIR}/sequences_reset.sql
```

#### 2.3 验证导出文件
```bash
# 检查文件大小
ls -lh ${BACKUP_DIR}/

# 验证 dump 文件完整性
pg_restore --list ${BACKUP_DIR}/data_only.dump | head -20
pg_restore --list ${BACKUP_DIR}/data_only.dump | wc -l
```

### 第 3 步：准备 SINK 数据库

#### 3.1 禁用触发器和约束（加速导入）
```bash
cat > ${BACKUP_DIR}/disable_constraints.sql << 'EOF'
-- 禁用所有外键约束
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT conname, conrelid::regclass AS table_name
        FROM pg_constraint
        WHERE contype = 'f'
    ) LOOP
        EXECUTE format('ALTER TABLE %s DISABLE TRIGGER ALL;', r.table_name);
    END LOOP;
END $$;

-- 记录当前设置
SET session_replication_role = 'replica';
EOF

psql -h $SINK_HOST -p $SINK_PORT -U $SINK_USER -d $SINK_DB \
    -f ${BACKUP_DIR}/disable_constraints.sql
```

### 第 4 步：导入数据到 SINK

#### 4.1 并行导入数据
```bash
# 使用 4 个并行任务（根据服务器性能调整）
pg_restore -h $SINK_HOST -p $SINK_PORT -U $SINK_USER \
    --dbname=$SINK_DB \
    --jobs=4 \
    --verbose \
    --data-only \
    --disable-triggers \
    ${BACKUP_DIR}/data_only.dump

# 检查返回码
if [ $? -eq 0 ]; then
    echo "✅ 数据导入成功"
else
    echo "❌ 数据导入失败，请检查错误信息"
    exit 1
fi
```

**参数说明**：
- `--jobs=4`：使用 4 个并行任务
- `--disable-triggers`：导入时禁用触发器
- `--data-only`：只导入数据

#### 4.2 重置序列值
```bash
psql -h $SINK_HOST -p $SINK_PORT -U $SINK_USER -d $SINK_DB \
    -f ${BACKUP_DIR}/sequences_reset.sql
```

### 第 5 步：恢复约束和触发器

#### 5.1 启用所有触发器和约束
```bash
cat > ${BACKUP_DIR}/enable_constraints.sql << 'EOF'
-- 恢复正常模式
RESET session_replication_role;

-- 启用所有触发器
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT conrelid::regclass AS table_name
        FROM pg_constraint
        WHERE contype = 'f'
    ) LOOP
        EXECUTE format('ALTER TABLE %s ENABLE TRIGGER ALL;', r.table_name);
    END LOOP;
END $$;
EOF

psql -h $SINK_HOST -p $SINK_PORT -U $SINK_USER -d $SINK_DB \
    -f ${BACKUP_DIR}/enable_constraints.sql
```

#### 5.2 验证外键约束
```bash
psql -h $SINK_HOST -p $SINK_PORT -U $SINK_USER -d $SINK_DB -c "
DO $$
DECLARE
    r RECORD;
    v_count INTEGER;
BEGIN
    FOR r IN (
        SELECT conname, conrelid::regclass AS table_name, 
               pg_get_constraintdef(oid) AS definition
        FROM pg_constraint
        WHERE contype = 'f'
    ) LOOP
        -- 这里只是列出外键，不检查违反情况
        RAISE NOTICE '外键: % on %', r.conname, r.table_name;
    END LOOP;
END $$;
"
```

### 第 6 步：验证数据完整性

#### 6.1 比对表行数
```bash
cat > ${BACKUP_DIR}/count_rows.sql << 'EOF'
SELECT 
    schemaname, 
    tablename, 
    (xpath('/row/cnt/text()', xml_count))[1]::text::int as row_count
FROM (
    SELECT schemaname, tablename, 
           query_to_xml(format('select count(*) as cnt from %I.%I', schemaname, tablename), false, true, '') as xml_count
    FROM pg_tables
    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
) sub
ORDER BY schemaname, tablename;
EOF

echo "=== SOURCE 数据库行数 ===" > ${BACKUP_DIR}/row_count_comparison.txt
psql -h $SOURCE_HOST -p $SOURCE_PORT -U $SOURCE_USER -d $SOURCE_DB \
    -f ${BACKUP_DIR}/count_rows.sql >> ${BACKUP_DIR}/row_count_comparison.txt

echo -e "\n=== SINK 数据库行数 ===" >> ${BACKUP_DIR}/row_count_comparison.txt
psql -h $SINK_HOST -p $SINK_PORT -U $SINK_USER -d $SINK_DB \
    -f ${BACKUP_DIR}/count_rows.sql >> ${BACKUP_DIR}/row_count_comparison.txt

cat ${BACKUP_DIR}/row_count_comparison.txt
```

#### 6.2 比对关键表的数据校验和（可选）
```bash
# 比对 users 表
psql -h $SOURCE_HOST -p $SOURCE_PORT -U $SOURCE_USER -d $SOURCE_DB -t -c "
SELECT COUNT(*), SUM(id::bigint) as id_sum, 
       md5(string_agg(id::text, ',' ORDER BY id)) as id_hash
FROM users;
" > ${BACKUP_DIR}/source_users_check.txt

psql -h $SINK_HOST -p $SINK_PORT -U $SINK_USER -d $SINK_DB -t -c "
SELECT COUNT(*), SUM(id::bigint) as id_sum,
       md5(string_agg(id::text, ',' ORDER BY id)) as id_hash
FROM users;
" > ${BACKUP_DIR}/sink_users_check.txt

echo "=== Users 表校验 ==="
diff ${BACKUP_DIR}/source_users_check.txt ${BACKUP_DIR}/sink_users_check.txt
if [ $? -eq 0 ]; then
    echo "✅ users 表数据一致"
else
    echo "❌ users 表数据不一致，请检查"
fi
```

#### 6.3 检查序列值
```bash
psql -h $SINK_HOST -p $SINK_PORT -U $SINK_USER -d $SINK_DB -c "
SELECT sequence_schema, sequence_name, last_value
FROM information_schema.sequences seq
JOIN pg_sequences pgs ON seq.sequence_name = pgs.sequencename
WHERE sequence_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY sequence_schema, sequence_name;
"
```

### 第 7 步：性能优化（推荐）

#### 7.1 重建索引
```bash
psql -h $SINK_HOST -p $SINK_PORT -U $SINK_USER -d $SINK_DB -c "
REINDEX DATABASE $SINK_DB;
"
```

#### 7.2 更新统计信息
```bash
psql -h $SINK_HOST -p $SINK_PORT -U $SINK_USER -d $SINK_DB -c "
ANALYZE VERBOSE;
"
```

#### 7.3 清理
```bash
psql -h $SINK_HOST -p $SINK_PORT -U $SINK_USER -d $SINK_DB -c "
VACUUM ANALYZE;
"
```

### 第 8 步：应用测试

#### 8.1 测试应用连接
```bash
# 临时修改 config.yaml 指向 SINK 数据库
# 或使用环境变量覆盖
export DATABASE_URL="postgresql://${SINK_USER}:password@${SINK_HOST}:${SINK_PORT}/${SINK_DB}"

# 运行健康检查
curl http://localhost:8000/health
```

#### 8.2 测试基本功能
- 用户登录
- 创建/读取 Agent
- 发送消息
- 查看聊天历史

### 第 9 步：切换到生产（如适用）

#### 9.1 停止应用写入 SOURCE
```bash
# 根据部署方式停止应用
# Docker: docker-compose down
# Systemd: systemctl stop inty-backend
```

#### 9.2 最后一次增量同步（如果 SOURCE 有新数据）
```bash
# 重复步骤 2-6，但只导出在第一次导出后新增/修改的数据
# 这需要根据表中的时间戳字段进行筛选
```

#### 9.3 更新配置，指向 SINK
```bash
# 修改 devops/config.yaml.prod
# 将 database.host 改为 SINK_HOST
```

#### 9.4 启动应用
```bash
# 重启应用，指向 SINK 数据库
```

---

## 🔄 方案 B：使用逻辑复制（高级）

适合大型数据库，需要最小停机时间。

### 前置要求
- PostgreSQL 10+ 版本
- SOURCE 数据库启用了 `wal_level = logical`
- 复制用户具有 `REPLICATION` 权限

### 步骤概览

1. **在 SOURCE 创建发布（Publication）**
```sql
-- 在 SOURCE 数据库执行
CREATE PUBLICATION my_pub FOR ALL TABLES;
```

2. **在 SINK 创建订阅（Subscription）**
```sql
-- 在 SINK 数据库执行
CREATE SUBSCRIPTION my_sub
CONNECTION 'host=SOURCE_HOST port=5432 dbname=devdb user=repl_user password=xxx'
PUBLICATION my_pub;
```

3. **监控同步进度**
```sql
-- 在 SINK 数据库查询
SELECT * FROM pg_stat_subscription;
SELECT * FROM pg_replication_slots;
```

4. **等待同步完成**
```bash
# 等待所有表同步完成（may take hours for large databases）
```

5. **切换应用到 SINK**
- 停止应用写入 SOURCE
- 等待最后的变更同步到 SINK
- 更新应用配置指向 SINK
- 启动应用

6. **清理**
```sql
-- 在 SINK 删除订阅
DROP SUBSCRIPTION my_sub;

-- 在 SOURCE 删除发布
DROP PUBLICATION my_pub;
```

---

## 🛠️ 方案 C：表级 COPY（灵活方案）

适合需要精细控制或只迁移部分表的场景。

### 导出单个表
```bash
psql -h $SOURCE_HOST -U $SOURCE_USER -d $SOURCE_DB -c "\COPY users TO '/tmp/users.csv' WITH (FORMAT CSV, HEADER)"
```

### 导入单个表
```bash
psql -h $SINK_HOST -U $SINK_USER -d $SINK_DB -c "\COPY users FROM '/tmp/users.csv' WITH (FORMAT CSV, HEADER)"
```

### 批量处理所有表
```bash
# 获取所有表名
TABLES=$(psql -h $SOURCE_HOST -U $SOURCE_USER -d $SOURCE_DB -t -c "
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
")

# 导出所有表
for TABLE in $TABLES; do
    echo "导出表: $TABLE"
    psql -h $SOURCE_HOST -U $SOURCE_USER -d $SOURCE_DB \
        -c "\COPY $TABLE TO '/tmp/${TABLE}.csv' WITH (FORMAT CSV, HEADER)"
done

# 导入所有表
for TABLE in $TABLES; do
    echo "导入表: $TABLE"
    psql -h $SINK_HOST -U $SINK_USER -d $SINK_DB \
        -c "\COPY $TABLE FROM '/tmp/${TABLE}.csv' WITH (FORMAT CSV, HEADER)"
done
```

---

## ⚠️ 常见问题与故障排除

### 1. 外键约束违反
**错误**：`ERROR: insert or update on table "XXX" violates foreign key constraint`

**解决**：
- 确保按依赖顺序导入表（pg_restore 会自动处理）
- 临时禁用约束：`SET session_replication_role = 'replica';`

### 2. 序列值不正确
**症状**：插入新记录时出现主键冲突

**解决**：
```sql
-- 重置序列到表的最大 ID
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));
```

### 3. 权限问题
**错误**：`ERROR: permission denied for table XXX`

**解决**：
```sql
-- 授予所有表的权限
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;
```

### 4. 磁盘空间不足
**症状**：导出/导入过程中磁盘已满

**解决**：
- 使用 `pg_dump` 的 `--compress=9` 参数压缩输出
- 直接管道传输，不保存中间文件：
```bash
pg_dump -h $SOURCE_HOST -U $SOURCE_USER $SOURCE_DB | \
    psql -h $SINK_HOST -U $SINK_USER $SINK_DB
```

### 5. 大表导入缓慢
**优化**：
- 增加 `--jobs` 参数（并行度）
- 临时调整 SINK 数据库配置：
```sql
SET maintenance_work_mem = '2GB';
SET max_wal_size = '10GB';
```

---

## 📋 迁移检查清单

**准备阶段**
- [ ] 记录 SOURCE 和 SINK 的连接信息
- [ ] 检查 SINK schema 是否与 SOURCE 一致
- [ ] 确认 SINK 数据库为空
- [ ] 评估数据量和预计迁移时间
- [ ] 准备足够的磁盘空间
- [ ] 通知相关人员（如需停机）

**导出阶段**
- [ ] 导出数据（pg_dump）
- [ ] 导出序列当前值
- [ ] 验证导出文件完整性
- [ ] 备份导出文件到安全位置

**导入阶段**
- [ ] 禁用 SINK 的触发器和约束
- [ ] 导入数据到 SINK
- [ ] 重置序列值
- [ ] 启用触发器和约束
- [ ] 验证外键约束

**验证阶段**
- [ ] 比对 SOURCE 和 SINK 的表行数
- [ ] 验证关键表的数据一致性
- [ ] 检查序列值是否正确
- [ ] 测试应用基本功能

**优化阶段**
- [ ] 重建索引（REINDEX）
- [ ] 更新统计信息（ANALYZE）
- [ ] 清理和优化（VACUUM）

**上线阶段**
- [ ] 停止应用写入 SOURCE（如需）
- [ ] 进行最后增量同步（如需）
- [ ] 更新应用配置指向 SINK
- [ ] 启动应用
- [ ] 监控应用和数据库状态
- [ ] 保留 SOURCE 作为备份（至少 7 天）

---

## 🔙 回滚计划

如果迁移失败或发现问题：

1. **立即回滚**
```bash
# 停止应用
# 恢复配置指向 SOURCE
# 重启应用
```

2. **清理 SINK 数据**
```sql
-- 删除所有数据但保留结构
DO $$ 
DECLARE 
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $$;
```

3. **分析失败原因**
- 检查日志文件
- 比对数据差异
- 修复问题后重新迁移

---

## 📊 性能参考

基于典型硬件（16 Core, 64GB RAM, SSD）：

| 数据量 | 预计导出时间 | 预计导入时间 | 推荐方案 |
|--------|--------------|--------------|----------|
| < 10GB | 5-10 分钟 | 10-20 分钟 | 方案 A |
| 10-50GB | 10-30 分钟 | 30-90 分钟 | 方案 A |
| 50-100GB | 30-60 分钟 | 90-180 分钟 | 方案 A |
| > 100GB | 1-3 小时 | 3-8 小时 | 方案 B |

> 实际时间取决于网络带宽、硬件性能、表结构复杂度等因素

---

## 📞 支持

如遇到问题，请收集以下信息：
- PostgreSQL 版本（`SELECT version();`）
- 数据库大小
- 错误日志
- 已执行的步骤

并联系 DBA 或开发团队寻求帮助。
