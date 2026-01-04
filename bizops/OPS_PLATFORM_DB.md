# GCP Datastream 与 BigQuery 数据复制

## 核心问题

**使用 Datastream 是否可以实现数据拷贝到 BigQuery，而无需在 BigQuery 查询期间持续访问数据库？**

**答案：是的。** 一旦数据通过 Datastream 复制到 BigQuery，BigQuery 查询操作完全独立于源数据库，不需要在查询期间访问源数据库。

## 工作原理

### 1. 数据同步阶段（Datastream 需要访问源数据库）

- **变更数据捕获（CDC）**：Datastream 通过日志机制（log-based）持续监控源数据库的变更（insert、update、delete）
- **数据流式传输**：变更事件实时或近实时地传输到 BigQuery
- **低影响**：使用日志机制，对源数据库性能影响最小

### 2. 查询阶段（BigQuery 独立运行）

- **数据已复制**：数据已经存储在 BigQuery 的数据集中
- **独立查询**：所有查询直接在 BigQuery 上执行，使用 BigQuery 的存储和计算资源
- **无需源数据库**：查询期间完全不需要访问源数据库
- **高性能**：BigQuery 使用列式存储和分布式查询引擎，查询性能独立于源数据库

## 架构优势

### 数据分离

```text
源数据库 (PostgreSQL/MySQL/Oracle)
    ↓ [Datastream CDC 同步]
BigQuery (数据副本)
    ↓ [查询操作]
分析结果
```

- **源数据库**：专注于 OLTP 工作负载（事务处理）
- **BigQuery**：专注于 OLAP 工作负载（分析查询）
- **解耦**：查询负载不会影响生产数据库性能

### 关键特性

1. **近实时同步**：数据变更通常在秒级内同步到 BigQuery
2. **自动恢复**：Datastream 具备强大的流恢复能力，最小化停机时间和数据丢失
3. **Schema 管理**：自动处理 Schema 变更（Schema drift resolution）
4. **安全传输**：数据在传输和存储时均加密

## 使用场景

### 适合的场景

- ✅ 需要将生产数据库数据复制到 BigQuery 进行分析
- ✅ 需要实时或近实时的数据分析，但不想影响生产数据库性能
- ✅ 需要将多个数据库的数据集中到 BigQuery 进行统一分析
- ✅ 需要历史数据保留和分析能力

### 注意事项

- **同步延迟**：虽然延迟很低（通常秒级），但不是完全实时
- **成本**：Datastream 按处理的数据量计费，BigQuery 按存储和查询计费
- **Schema 变更**：源数据库 Schema 变更会自动同步，但需要确保兼容性

## 与直接查询数据库的区别

| 方式                      | 查询时是否需要访问源数据库 | 对源数据库性能影响 | 查询性能         |
| ------------------------- | ------------------------- | ------------------ | ---------------- |
| **Datastream + BigQuery** | ❌ 不需要                 | 最小（仅同步时）   | 高（列式存储）   |
| **直接查询源数据库**      | ✅ 需要                   | 高（查询负载）     | 取决于源数据库   |

## Cloud SQL PostgreSQL 配置

### 问题：创建逻辑复制槽权限错误

在 Cloud SQL PostgreSQL 中，即使使用 `postgres` 用户，也可能遇到以下错误：

```sql
ERROR: must be superuser or replication role to use replication slots
```

### 原因

Cloud SQL 中的 `postgres` 用户**不是真正的 superuser**，因此无法直接创建逻辑复制槽。Datastream 需要逻辑复制槽来捕获变更。

### 解决方案

#### 方法 1：启用 Cloud SQL 逻辑解码标志（推荐）

在 Cloud SQL 实例上启用逻辑解码功能：

```bash
# 使用 gcloud CLI
gcloud sql instances patch INSTANCE_NAME \
    --database-flags=cloudsql.logical_decoding=on

# 或者通过 Cloud Console
# 1. 进入 Cloud SQL 实例页面
# 2. 点击 "Edit"
# 3. 在 "Flags" 部分添加：
#    cloudsql.logical_decoding = on
```

**重要提示**：

- 启用此标志后，Cloud SQL 会自动管理逻辑复制槽
- **不需要手动创建复制槽**，Datastream 会在需要时自动创建
- 这是 Cloud SQL 的推荐方式

#### 方法 2：授予 replication 权限（如果方法 1 不可用）

如果必须手动创建，需要授予 replication 权限：

```sql
-- 注意：在 Cloud SQL 中，这通常需要特殊权限或通过 Cloud SQL Admin API
-- 通常不推荐手动操作，因为 Cloud SQL 会自动管理
ALTER USER postgres WITH REPLICATION;
```

**注意**：在 Cloud SQL 中，通常无法直接执行此操作，因为 Cloud SQL 限制了某些管理操作。

### 验证配置

1. **检查逻辑解码是否启用**：

   ```sql
   SHOW cloudsql.logical_decoding;
   -- 应该返回 'on'
   ```

2. **检查 pgoutput 插件是否可用**：

   ```sql
   SELECT * FROM pg_available_extensions WHERE name = 'pgoutput';
   ```

3. **查看现有复制槽**（如果已创建）：

   ```sql
   SELECT * FROM pg_replication_slots;
   ```

### 最佳实践

1. ✅ **使用 Cloud SQL 标志**：通过 `cloudsql.logical_decoding=on` 标志启用，让 Cloud SQL 自动管理
2. ✅ **让 Datastream 自动创建**：在 Datastream 配置向导中，它会自动处理复制槽的创建
3. ❌ **避免手动创建**：不要手动创建复制槽，除非有特殊需求
4. ⚠️ **注意性能影响**：逻辑解码会略微增加数据库负载，但通常影响很小

### 常见错误排查

| 错误信息                              | 原因                     | 解决方法                           |
| ------------------------------------- | ------------------------ | ---------------------------------- |
| `must be superuser or replication role` | 未启用逻辑解码或权限不足 | 启用 `cloudsql.logical_decoding=on` 标志 |
| `extension "pgoutput" does not exist` | PostgreSQL 版本过低      | 确保使用 PostgreSQL 10+           |
| `replication slot already exists`     | 复制槽已存在             | 检查现有槽，或删除后重新创建       |

## Cloud SQL 实例迁移方案：使用 Clone 切换

### 场景：主数据库实例需要重启

当主数据库实例需要重启（例如启用 `cloudsql.logical_decoding=on` 标志需要重启）时，可以考虑先创建 clone，然后切换数据。

### 可行性分析

**✅ 可行，但需要注意以下关键点：**

1. **Clone 是时间点快照**：Clone 创建时捕获的是创建时刻的数据状态
2. **数据差异处理**：Clone 创建后到切换之间会有数据差异，需要处理
3. **Datastream 需要重新配置**：需要在新实例上重新配置 Datastream
4. **应用连接切换**：需要更新应用配置指向新实例

### 迁移方案

#### 方案 A：零停机迁移（推荐）

适用于可以短暂停止写入的场景：

**步骤 1：准备阶段**

```bash
# 1. 创建 clone（在低峰期执行）
gcloud sql instances clone SOURCE_INSTANCE_NAME \
    CLONE_INSTANCE_NAME \
    --backup-id=BACKUP_ID  # 可选：指定备份点

# 2. 等待 clone 创建完成（通常几分钟到几十分钟，取决于数据量）
gcloud sql instances describe CLONE_INSTANCE_NAME
```

**步骤 2：配置新实例**

```bash
# 1. 在新实例上启用逻辑解码（如果需要）
gcloud sql instances patch CLONE_INSTANCE_NAME \
    --database-flags=cloudsql.logical_decoding=on

# 2. 验证配置
gcloud sql connect CLONE_INSTANCE_NAME --user=postgres
# 在 psql 中执行：
SHOW cloudsql.logical_decoding;
```

**步骤 3：数据同步（处理差异）**

由于 clone 是时间点快照，需要同步 clone 创建后的数据变更：

```bash
# 方法 1：使用逻辑复制（推荐，适用于 PostgreSQL）
# 在主实例上创建发布
psql -h SOURCE_INSTANCE_IP -U postgres -d inty
CREATE PUBLICATION migration_pub FOR ALL TABLES;

# 在 clone 实例上创建订阅
psql -h CLONE_INSTANCE_IP -U postgres -d inty
CREATE SUBSCRIPTION migration_sub
CONNECTION 'host=SOURCE_INSTANCE_IP port=5432 user=postgres password=PASSWORD dbname=inty'
PUBLICATION migration_pub;

# 等待同步完成
SELECT * FROM pg_subscription;
```

**步骤 4：切换应用连接**

```bash
# 1. 停止应用写入（短暂维护窗口）
# 2. 确认数据同步完成
# 3. 更新应用配置指向新实例
# 4. 重启应用
```

**步骤 5：配置 Datastream**

```bash
# 1. 停止旧的 Datastream（如果存在）
# 2. 在新实例上创建新的 Datastream 连接
# 3. 配置 Datastream 指向新实例
# 4. 启动 Datastream
```

**步骤 6：清理**

```bash
# 1. 删除旧实例上的逻辑复制订阅（如果使用）
# 2. 删除旧实例（确认新实例运行正常后）
# 3. 更新监控和告警配置
```

#### 方案 B：最小停机迁移

适用于需要最小化停机时间的场景：

**步骤 1-2：同方案 A**

**步骤 3：切换流程**

```bash
# 1. 在维护窗口开始
# 2. 停止应用写入
# 3. 使用 pg_dump/pg_restore 同步最后的数据差异
pg_dump -h SOURCE_INSTANCE_IP -U postgres -d inty \
    --data-only --exclude-table=pg_* \
    > final_diff.sql

psql -h CLONE_INSTANCE_IP -U postgres -d inty < final_diff.sql

# 4. 验证数据一致性
# 5. 切换应用连接
# 6. 重启应用
```

### 关键注意事项

#### 1. Datastream 处理

**重要**：切换实例后，Datastream 需要重新配置：

- ❌ **不能直接切换**：Datastream 绑定到特定的数据库实例
- ✅ **需要重新创建**：在新实例上创建新的 Datastream 连接
- ⚠️ **数据连续性**：切换期间会有短暂的数据同步中断

**处理建议**：

```bash
# 1. 在切换前，记录当前 Datastream 的 LSN（Log Sequence Number）
# 2. 在新实例上创建 Datastream 时，可以指定起始点（如果支持）
# 3. 或者接受短暂的数据差异，后续通过其他方式补齐
```

#### 2. 数据一致性

- **时间窗口**：Clone 创建后到切换之间的数据变更需要处理
- **事务完整性**：确保所有事务都已提交
- **验证步骤**：切换前验证关键表的数据一致性

#### 3. 应用连接

- **连接字符串**：更新所有应用的数据库连接配置
- **连接池**：重启应用以刷新连接池
- **DNS/负载均衡**：如果使用 DNS 或负载均衡，需要更新指向

#### 4. 监控和告警

- **监控新实例**：确保新实例正常运行
- **性能对比**：对比新旧实例的性能指标
- **数据验证**：定期验证数据完整性

### 风险与缓解

| 风险               | 影响 | 缓解措施                                                           |
| ------------------ | ---- | ------------------------------------------------------------------ |
| 数据丢失           | 高   | 使用逻辑复制同步差异数据；在维护窗口执行                           |
| Datastream 中断    | 中   | 提前准备 Datastream 配置；接受短暂中断或使用其他同步方式           |
| 应用连接失败       | 高   | 提前测试连接；准备回滚方案                                         |
| 性能下降           | 中   | 监控新实例性能；准备扩容方案                                       |

### 回滚方案

如果切换失败，可以快速回滚：

```bash
# 1. 立即将应用连接切回原实例
# 2. 检查原实例状态
# 3. 分析失败原因
# 4. 修复问题后重新尝试
```

### 替代方案

如果 clone 方案风险过高，可以考虑：

1. **直接重启主实例**：
   - 在维护窗口直接重启
   - 应用会有短暂中断
   - 但操作简单，风险低

2. **使用 Cloud SQL 高可用配置**：
   - 配置主从复制
   - 在从实例上启用逻辑解码
   - 切换 Datastream 到从实例
   - 然后重启主实例

3. **分阶段迁移**：
   - 先创建 clone 用于测试
   - 验证 Datastream 配置
   - 再执行正式切换

### 最佳实践

1. ✅ **在测试环境先验证**：完整测试迁移流程
2. ✅ **选择低峰期**：在业务低峰期执行
3. ✅ **准备回滚方案**：确保可以快速回滚
4. ✅ **监控关键指标**：实时监控数据库和应用状态
5. ✅ **文档化流程**：记录详细的迁移步骤和检查点

## 运营平台数据库分离方案

### 问题：运营平台查询对生产数据库造成压力

运营平台（如 `eval_app/`）通常需要执行大量的分析查询、报表生成、数据统计等操作，这些操作可能会：

- 消耗大量数据库资源（CPU、内存、I/O）
- 影响生产环境的查询性能
- 导致连接池耗尽
- 影响用户体验

### 解决方案对比

| 方案                         | 实时性             | 成本             | 复杂度 | 适用场景                                   |
| ---------------------------- | ------------------ | ---------------- | ------ | ------------------------------------------ |
| **BigQuery（Datastream 同步）** | 近实时（秒级延迟） | 按查询和存储计费 | 低     | 分析查询、报表、数据统计（推荐）           |
| **Cloud SQL Read Replica**   | 实时（毫秒级延迟） | 按实例计费       | 中     | 需要实时性的复杂查询                       |
| **独立分析数据库**           | 实时               | 按实例计费       | 高     | 需要复杂 SQL 和实时性的场景                |

### 方案 1：使用 BigQuery（推荐）

**优势**：

- ✅ **完全隔离**：查询不影响生产数据库
- ✅ **高性能**：列式存储，适合分析查询
- ✅ **自动扩展**：无需管理资源
- ✅ **成本优化**：按实际使用计费
- ✅ **近实时同步**：通过 Datastream 秒级同步

**架构**：

```text
生产数据库 (Cloud SQL)
    ↓ [Datastream CDC]
BigQuery (数据仓库)
    ↓ [运营平台查询]
运营分析结果
```

**实施步骤**：

1. **配置 Datastream**（如前面章节所述）

2. **修改运营平台代码**，使用 BigQuery 客户端：

   ```python
   # eval_app/services/analytics_service.py
   from google.cloud import bigquery
   
   client = bigquery.Client()
   
   async def get_user_statistics():
       query = """
       SELECT 
           DATE(created_at) as date,
           COUNT(*) as user_count,
           COUNT(DISTINCT user_id) as unique_users
       FROM `project.dataset.users`
       WHERE created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
       GROUP BY date
       ORDER BY date DESC
       """
       results = client.query(query)
       return [dict(row) for row in results]
   ```

3. **配置 BigQuery 访问权限**：

   ```bash
   # 为运营平台服务账号授予 BigQuery 访问权限
   gcloud projects add-iam-policy-binding PROJECT_ID \
       --member="serviceAccount:ops-platform@PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/bigquery.dataViewer"
   ```

4. **更新配置文件**：

   ```yaml
   # config.yaml
   operations_platform:
     use_bigquery: true
     bigquery_project: "your-project-id"
     bigquery_dataset: "inty_analytics"
     # 可选：保留直接数据库连接作为备用
     fallback_to_database: false
   ```

**注意事项**：

- ⚠️ **SQL 语法差异**：BigQuery 使用标准 SQL，部分 PostgreSQL 语法需要调整
- ⚠️ **延迟**：数据有秒级延迟，不适合需要完全实时的场景
- ⚠️ **成本**：大量查询会产生费用，需要监控使用量

### 方案 2：使用 Cloud SQL Read Replica

**优势**：

- ✅ **实时数据**：毫秒级延迟
- ✅ **完全兼容**：PostgreSQL 语法完全兼容
- ✅ **隔离读操作**：不影响主实例写入性能

**架构**：

```text
生产数据库 (Cloud SQL Primary)
    ↓ [流复制]
只读副本 (Cloud SQL Read Replica)
    ↓ [运营平台查询]
运营分析结果
```

**实施步骤**：

1. **创建 Read Replica**：

   ```bash
   gcloud sql instances create ops-platform-replica \
       --master-instance-name=production-instance \
       --tier=db-custom-4-16384 \
       --region=asia-east1
   ```

2. **配置运营平台连接**：

   ```yaml
   # config.yaml
   operations_platform:
     database:
       host: "ops-platform-replica-ip"
       port: 5432
       user: "postgres"
       password: "${OPS_DB_PASSWORD}"
       db: "inty"
       # 只读连接池配置
       pool_size: 20
       max_overflow: 10
   ```

3. **修改代码使用只读连接**：

   ```python
   # eval_app/db/session.py
   from app.core.config import global_config_loaded_from_config_yaml
   
   # 使用运营平台专用配置
   ops_db_config = global_config_loaded_from_config_yaml.operations_platform.database
   
   ops_async_engine = create_async_engine(
       ops_db_config.async_url,
       pool_size=ops_db_config.pool_size,
       # 只读模式
       connect_args={
           "server_settings": {
               "default_transaction_read_only": "on",
               "application_name": "inty_ops_platform",
           },
       },
   )
   ```

**注意事项**：

- ⚠️ **成本**：需要运行额外的数据库实例
- ⚠️ **延迟**：虽然延迟很低，但不是完全实时（通常 < 1 秒）
- ⚠️ **资源限制**：需要合理配置实例规格

### 方案 3：混合方案（推荐用于复杂场景）

结合 BigQuery 和 Read Replica 的优势：

- **BigQuery**：用于历史数据分析、报表生成、复杂聚合查询
- **Read Replica**：用于实时数据查询、需要最新数据的场景

**实施**：

```python
# eval_app/services/data_service.py
class DataService:
    def __init__(self):
        self.bigquery_client = bigquery.Client()
        self.replica_db = get_ops_db_session()
    
    async def get_historical_stats(self, days: int = 30):
        """使用 BigQuery 查询历史数据"""
        # 复杂分析查询使用 BigQuery
        ...
    
    async def get_realtime_data(self, user_id: str):
        """使用 Read Replica 查询实时数据"""
        # 需要最新数据的查询使用 Read Replica
        ...
```

### 推荐方案选择

**场景 1：主要是分析查询和报表**

- ✅ **推荐：BigQuery**
- 成本低、性能好、完全隔离

**场景 2：需要实时数据 + 复杂 SQL**

- ✅ **推荐：Read Replica**
- 实时性好、SQL 兼容

**场景 3：混合需求**

- ✅ **推荐：混合方案**
- BigQuery 用于分析，Read Replica 用于实时查询

### 迁移步骤

1. **评估现有查询**：
   - 分析运营平台的查询模式
   - 识别哪些适合 BigQuery，哪些需要实时性

2. **选择方案**：
   - 根据查询需求选择合适方案
   - 可以分阶段迁移

3. **实施**：
   - 配置数据源（Datastream 或 Read Replica）
   - 修改代码使用新数据源
   - 测试验证

4. **监控**：
   - 监控查询性能
   - 监控成本
   - 监控数据延迟

5. **优化**：
   - 根据使用情况调整配置
   - 优化查询性能
   - 优化成本

## 参考资源

- [Datastream 官方文档](https://cloud.google.com/datastream)
- [Datastream for BigQuery](https://cloud.google.com/datastream/docs/datastream-for-bigquery)
- [Cloud SQL PostgreSQL 逻辑解码](https://cloud.google.com/sql/docs/postgres/replication/logical-decoding)
- [Cloud SQL 实例克隆](https://cloud.google.com/sql/docs/postgres/create-clone)
- [Cloud SQL Read Replicas](https://cloud.google.com/sql/docs/postgres/replication/create-replica)
- [BigQuery 文档](https://cloud.google.com/bigquery/docs)
- [定价信息](https://cloud.google.com/datastream/pricing)

---

*CREATED_BY_AGENT*
