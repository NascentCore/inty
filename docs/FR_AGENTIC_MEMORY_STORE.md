# FR_AGENTIC_MEMORY_STORE

## 中文执行计划

本 FR 目标：为 **AGENTIC kernel**（`app/core/agentic_kernel/` 下的 companion 运行时）提供**专用**长期记忆：可持久化的命名记忆、可审计来源、层次结构、PostgreSQL + pgvector 与全文混合检索、进程内运行时缓存，以及与其它提示词切片统一的 LLM 上下文组装能力。

**与 legacy 记忆系统的关系（强制边界）**

- **Legacy** 指：既有 PostgreSQL `memory` 表、节日/日常记忆抽取与推送、`memory_extraction_log` 等主 App 管线；**本 FR 不沿用、不扩展、不在读写路径上耦合**该表或该管线。
- **Agentic kernel 记忆** 使用**独立表名与独立 Repository/服务**（例如 `agentic_kernel_ltm` + `agentic_kernel_ltm_provenance`，名称以最终实现为准），仅由 kernel 编排层与可选的后台任务访问。
- 主 App 的 legacy 记忆可继续服务旧客户端；agentic 路径是否**并行展示**由产品另定，但**存储与代码边界保持分离**。

### 前置决策（阶段 0）

- 固化 **新表前缀与模块布局**（全部落在 agentic kernel 或明确标注的 `backend` 子模块，禁止混入 legacy `memory` 的 ORM 模型）。
- 固化 **作用域键**：`user_id` 必选；`agent_id` / `chat_id` / `workspace` 或 kernel 会话键是否参与过滤与唯一约束写清。
- 固化 **嵌入合同**：模型 id、向量维度、是否归一化、距离算子（与 HNSW opclass 一致）、`embedding_version` 升级与全量重算策略。

### 分阶段交付

| 阶段 | 中文说明 | 主要产出 |
|------|----------|----------|
| 0 | 决策与契约 | 表前缀、作用域键、嵌入合同、与 legacy 的隔离清单（代码路径级） |
| 1 | 数据库 | Alembic：`CREATE EXTENSION vector`、新表、B-tree / HNSW / GIN 索引 |
| 2 | 数据访问层 | SQLAlchemy 模型、Repository、嵌入失败状态与重试钩子 |
| 3 | 写入流水线 | 提炼 -> 归一化/去重 -> 调嵌入 API -> 同事务写主表与 provenance -> 通知缓存失效 |
| 4 | 运行时内存 | 工作集、热点 LRU、写合并；**以 PG 为准**，进程可冷启动重建 |
| 5 | 检索服务 | 过滤后向量 Top-K + 全文 Top-K -> RRF/加权融合 -> 可选重排；层次打包进 token 预算 |
| 6 | 提示词组装 | 记忆单独成块注入；顺序：静态系统 -> 工具策略 -> **记忆** -> 近期对话；各层 max_tokens |
| 7 | 对外 API（若需要） | HTTP 契约；同步 `app/schemas` 与 Kotlin `api/model` |
| 8 | 质量与观测 | 集成测试；**断言** agentic 读写从不触及 legacy `memory` 表；延迟与嵌入失败率指标 |
| 9 | 上线 | 功能开关、重嵌入与索引重建运维说明 |

### 关键依赖与风险

- **依赖**：带 pgvector 的 Postgres 镜像或实例；嵌入服务配额与密钥；DSN 可与现网 PG **同实例不同表**，但连接与配置须**独立**于 legacy 记忆服务（避免共享 Repository）。
- **风险**：大表 HNSW 构建窗口；过滤过窄时预过滤与召回需调参；来源字段含 PII 须与聊天记录同等留存与权限；检索需防跨租户（禁止仅按向量查）。

### 详细规格说明（与实现对齐）

以下与上文「分阶段交付」一致，补充字段级与流水线级说明。

## 目标与非目标

**目标**（仅 `app/core/agentic_kernel/` 使用）：

1. 每条记忆有稳定 **命名**（作用域内 slug）与 **来源**（provenance：哪些对话片段与元数据支撑提炼）。
2. **层次化**：`parent_id` 树，可选 `agentic_kernel_ltm_edge` 表达 DAG（关联、替代、派生）。
3. **持久化**：PostgreSQL + **pgvector** 语义检索，配合 **全文**（`tsvector` + GIN）做混合排序。
4. **进程内运行时**：工作集、热点缓存、写合并；**PostgreSQL 为权威数据源**。
5. **提示词组装**：独立「记忆切片」，与静态系统切片、工具策略切片、近期对话等拼装为发给 LLM 的上下文。

**非目标**：复用、迁移或扩展 legacy `memory` 表及其抽取管线；向 legacy 表双写 kernel LTM。

表名与列名为提案，**禁止**与 legacy `memory` 同名冲突。

## 与现有系统的关系

### Legacy `memory`（本设计不触碰）

- 历史主 App 能力：`memory` 表（见 `alembic/versions/20260127_120000_add_memory_tables.py`）、节日/日常抽取与推送等。
- **本 FR 不读不写** legacy `memory`：不共享 ORM、不共享 Repository、LTM 行不 `FOREIGN KEY` 指向 `memory.id`。

### Agentic kernel 工作区存储（正交）

- 代码：`app/core/agentic_kernel/companion/memory_store.py`、`memory_registry.py`、`turn_engine.py`。
- 现状：工作区级状态（如 compaction），**不是** kernel LTM。职责拆分：**工作区 store** 与 **`AgenticKernelLtmStore`**（示例名，以代码为准）及新表。

**集成**：在 **kernel 回合组装** 路径上引入专用 **读穿/写穿** `AgenticKernelLtmRuntime`（示例名）。DSN 可与业务共用同一 PG 集群，但 **LTM 迁移与代码归 kernel 侧拥有**；进程重启后从 PG 重建内存侧索引。

### 编排边界

- `companion_chat_service.py` 仅可传入 **DSN 或 session 工厂**；不得把 kernel LTM 路由到 legacy 记忆服务。嵌入可异步/延迟，**不得**调用 legacy 抽取任务。

### 提示词组装

- 对齐 `docs/FR_CLEAN_AGENT_PROMPTS_SYSTEM.md`（类型化切片边界）。
- 记忆块由单一入口生成（如小型 `PromptAssembler`），避免多处字符串拼接。

## 存储选型

- **PostgreSQL + pgvector**：元数据、来源、租户过滤与向量同事务；与 `backend/ARCH.md`、`backend/AGENTS.md`、`docker compose up pgvector` 一致。
- **混合检索**：向量距离（如 `<=>` / `<->`，与归一化及 HNSW **opclass** 一致）+ `tsvector` 全文通道，RRF 或加权融合。

## 逻辑数据模型

### 表 `agentic_kernel_ltm`（示例名，非 legacy `memory`）

| 列名 | 说明 |
|------|------|
| `id` | 主键 UUID 或 BIGSERIAL |
| `user_id` | 租户；每条查询必选过滤条件 |
| `agent_id` | 可空：用户全局记忆；否则绑定角色/ companion |
| `chat_id` | 可空：会话级更细粒度 |
| `parent_id` | 层次；根为 NULL |
| `name` | slug；在 `(user_id, agent_id, chat_id)` 等作用域内唯一（迁移中写死规则） |
| `content` | 写入 LLM 提示的正文 |
| `embedding` | `vector(N)`，`N` 与 `embedding_model` 绑定 |
| `embedding_model` | 模型 id 字符串 |
| `embedding_version` | 重嵌入批次标识 |
| `content_tsv` | 由 `content`（及可选 `name`）生成的 `tsvector` |
| `valid_from` / `valid_to` | 软删或替代 |
| `created_at` / `updated_at` | 审计 |

**索引（示例）**

- B-tree：`user_id`，`(user_id, agent_id)`，`(user_id, agent_id, parent_id)`。
- 唯一：`(user_id, agent_id, name)`；`agent_id` 可空时用部分索引或 surrogate scope。
- `embedding` 上 HNSW，**opclass 与查询距离一致**。
- `content_tsv` 上 GIN。

### 表 `agentic_kernel_ltm_provenance`

| 列名 | 说明 |
|------|------|
| `id` | 主键 |
| `memory_id` | 外键指向 `agentic_kernel_ltm` |
| `source_type` | 如 `chat_message`、`chat_window`、`tool`、`document` |
| `source_id` | 外部 id |
| `excerpt` | 可选截断原文 |
| `meta` | JSONB：提炼器版本、prompt 哈希、偏移等 |

### 可选表 `agentic_kernel_ltm_edge`

- 非树关系：`related_to`、`supersedes`、`derived_from`，行 `(from_id, to_id, kind)`。

## 进程内运行时子系统

**职责**

1. **工作集**：最近 N 轮或尚未对检索可见的待写数据。
2. **热点缓存**：当前 `user_id` / `agent_id` 下部分向量（LRU 或会话固定）。
3. **写队列**：按 `name` 去抖合并；安全时批量调用嵌入 API。

**规则**

- **以 PostgreSQL 为准**；内存结构可丢弃。
- PG 提交后按 `id` + 版本更新或失效缓存。
- 启动：不强制全量预热；按作用域首次检索懒加载。

## 写入流水线

1. **提炼**：LLM 或规则任务输出结构化字段（`name`、`content`、`parent_id`、多行 provenance）。
2. **归一化**：裁剪 `name`、唯一性策略、同名则合并或升版本。
3. **嵌入**：调用嵌入服务；失败则写 `embedding_status`（迁移中增加列）并入队重试。
4. **持久化**：单事务写 `agentic_kernel_ltm`、插入 provenance、若非生成列则更新 `content_tsv`。
5. **通知运行时**：失效或补丁式更新缓存。

异步：长耗时嵌入不阻塞用户可见回合完成；由 kernel 或调用方延迟，**不**走 legacy 抽取。

## 读取与检索流水线

1. 由最新用户话轮或聚合任务串生成 `query_embedding`。
2. SQL 过滤：`user_id = ?`，可选 `agent_id`、`chat_id`、`valid_to IS NULL`、层次条件。
3. 向量分支：`ORDER BY embedding <=> :q LIMIT k_vec`。
4. 全文分支：`ts_rank_cd` 或 `@@`，`LIMIT k_txt`。
5. 融合：RRF 或加权和；可选对 Top M 交叉编码器重排（特性开关）。
6. **层次感知打包**：在 token 预算内组合祖先摘要与叶子细节（可配置）。

## 提示词组装集成

建议消息顺序（与 clean prompt 体系统一时再对齐）：

1. 静态系统切片（人格、安全、格式）。
2. 工具与策略切片。
3. **记忆切片**：列表项含 `name`、`content`、一行来源引用（紧凑模式可仅 id）。
4. 近期对话窗口。

各切片在配置中设 `max_tokens`；记忆切片先丢融合分最低项。

## HTTP 与双端 schema

若移动端或 Ops 需列改记忆：更新 `app/schemas` 与 `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model`（仓库约定）。

## 安全

- 每条读路径必须带 **租户过滤**（`user_id`）；禁止仅靠向量检索。
- provenance 可能含 PII：留存与访问控制与聊天记录同级。
- 缓解记忆投毒：Top-K 多样性、置信度标记、高影响写入可选人工审核队列。

## 测试要点

1. 迁移：空库 `alembic upgrade head`，确认已安装 `vector` 扩展。
2. Repository 集成：插入、混合检索、唯一性、父链、替代。
3. **隔离**：静态分析或集成测试断言 kernel LTM 模块不 import legacy `memory` 模型或服务。
4. 负载烟测：固定行数，在 CI 体量 DB 上记录 p95 基线。

## 仓库路径索引

- `alembic/versions/20260127_120000_add_memory_tables.py`：legacy `memory`（仅对照，本 FR 不扩展）
- `alembic/AGENTS.md`：迁移流程
- `app/core/agentic_kernel/companion/memory_store.py`：工作区 store（与 LTM 正交）
- `app/core/agentic_kernel/companion/turn_engine.py`：kernel 回合与提示组装挂点
- `app/services/companion_chat_service.py`：可选 DSN 注入边界
- `docs/FR_CLEAN_AGENT_PROMPTS_SYSTEM.md`：提示词组装方向
- `backend/ARCH.md`、`backend/AGENTS.md`：pgvector 与 compose 说明
