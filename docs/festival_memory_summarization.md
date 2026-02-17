# 节日记忆抽取：关键数据结构与处理 API 摘要

本文档汇总节日记忆抽取流程中的**核心数据表/模型**与**处理 API（HTTP、服务层、定时任务）**，便于快速查阅。完整需求与行为说明见 [FR_FESTIVAL_MEMORY.md](FR_FESTIVAL_MEMORY.md)。

---

## 1. 关键数据结构

### 1.1 配置表：`festival_memory_config`

- **ORM**：`app.models.memory.FestivalMemoryConfig`
- **用途**：描述一条「节日记忆抽取」定时任务配置；evaluation 新建/编辑的「配置」即写入此表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | int | 主键 |
| `festival_name` | str | 节日名称 |
| `festival_date` | date | 节日日期（配置时区下的自然日） |
| `prompt` | text | 抽取用 LLM 提示词 |
| `enabled` | bool | 是否启用 |
| `timezone` | str | IANA 时区（如 Asia/Shanghai），节日日期与执行时间均按此时区 |
| `run_at_date` | date | 执行日期（该时区下），须 ≥ festival_date |
| `run_at_hour` | int | 执行时刻（该时区下本地小时 0–23） |
| `min_rounds_in_window` | int \| NULL | 窗口内最少用户消息轮数，NULL 表示默认 15 |
| `last_run_at` | datetime(tz) \| NULL | 最近一次被定时任务执行的时间（UTC），用于到点判断与占位防重 |
| `created_at` / `updated_at` | datetime(tz) | 创建/更新时间 |

- **Pydantic**：`app.schemas.festival_memory`
  - 创建：`FestivalMemoryConfigCreate`
  - 更新：`FestivalMemoryConfigUpdate`
  - 库表返回：`FestivalMemoryConfigInDB`

### 1.2 记忆表：`memory`（节日记忆行）

- **ORM**：`app.models.memory.Memory`
- **用途**：存储抽取出的节日回忆摘要；每条记录对应一个 (user_id, agent_id, festival_name, festival_date) 的 LLM 摘要。

与节日记忆相关的字段：

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | int | 主键 |
| `user_id` | str | 用户 ID |
| `agent_id` | str | 角色 ID |
| `memory_type` | str | 节日记忆为 `"festival"` |
| `content` | text | 抽取得到的摘要正文 |
| `extracted_at` | datetime(tz) | 抽取时间 |
| `festival_name` | str | 节日名称 |
| `festival_date` | date | 节日日期 |
| `delivery_at` | datetime(tz) \| NULL | 首次投递到会话的时间，NULL 表示未投递 |
| `system_notification_sent_at` | datetime(tz) \| NULL | 节日记忆 system 推送发送时间 |

- **metadata**（JSON）：节日记忆含 `festival_name`、`festival_data`；可选 **`llm_config`**（对象：`model`、`temperature`、`max_tokens`，抽取时使用的 LLM 配置）。
- 同一 (user_id, agent_id, festival_name, festival_date) 在抽取时**先 DELETE 再 INSERT**，仅保留最新一条。
- **离线脚本输出格式（breaking change）**：`run_festival_memory_extraction_to_json.py` 导出的每条记忆及 `query_festival_memories_from_db`（`--query`）返回的每条记录为 `{ user_id, agent_id, memory_type, content, metadata, user_name?, agent_name? }`。**`metadata`** 为单一对象（FestivalMemoryMetadata：`festival_name`、`festival_date`、`llm_config`）；顶级的 `festival_name`、`festival_date`、`llm_config` 已移除，消费者需从 `metadata` 读取。

---

## 2. 处理 API

### 2.1 管理员 HTTP API（evaluation 配置与立即执行）

- **路由**：`app.api.v1.endpoints.festival_memory`，前缀 `/evaluation/admin`，需超级用户。

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET | `/festival-memory-configs` | 配置列表（skip/limit） |
| POST | `/festival-memory-configs` | 创建配置 → 写入 `festival_memory_config` |
| PUT | `/festival-memory-configs/{config_id}` | 更新配置 |
| DELETE | `/festival-memory-configs/{config_id}` | 删除配置 |
| POST | `/festival-memory-extraction/run` | 立即执行抽取（可传 `config_id` 或独立参数） |

- 创建/更新请求体使用 `FestivalMemoryConfigCreate` / `FestivalMemoryConfigUpdate`；返回使用 `FestivalMemoryConfigInDB`。
- 立即执行返回：`FestivalMemoryExtractionRunResponse`（`total_pairs`、`success_count`、`failed_count`）。

### 2.2 服务层：节日记忆抽取

- **模块**：`app.services.festival_memory_service`

| 函数 | 说明 |
| ---- | ---- |
| `get_pairs_with_min_rounds_in_window_sync(festival_date, db_url, min_rounds, timezone_str)` | 按配置时区与节日日期计算 28 小时窗口（节日 00:00–次日 04:00），在窗口内统计每 (user_id, agent_id) 的用户消息数（排除开场白），返回消息数 ≥ min_rounds 的 (user_id, agent_id) 列表。 |
| `extract_festival_and_save(db, user_id, agent_id, festival_name, festival_date, prompt_template)` | 拉取该会话消息 → 拼装提示词 → 调用 OpenRouter 抽取摘要 → 删除同 (user_id, agent_id, festival_name, festival_date) 的旧 Memory → 插入一条新 `Memory`（memory_type=festival），写入 `memory` 表。 |

- 抽取结果写入 **`memory`** 表；不在此处写 chat_history，投递由 GET messages / POST completions 按需触发。

### 2.3 定时任务：push worker 如何「接单」

- **入口**：`backend/push_worker/main.py` 启动 `push_scheduler_service.start()`，不直接读队列；任务由调度器周期性执行。
- **调度**：`app.services.push_scheduler_service.PushSchedulerService`
  - 注册任务：`_run_festival_memory_extraction`，`IntervalTrigger(minutes=5)`，启动后立即执行一次，之后每 5 分钟一次。
- **接单逻辑**（`_run_festival_memory_extraction`）：
  1. 查询 `festival_memory_config` 中 `enabled=True` 且 `run_at_date`、`run_at_hour` 非空的配置。
  2. 将每条配置的 (run_at_date, run_at_hour) 按该配置的 `timezone` 转为 UTC 得到 `run_at_dt`。
  3. 仅当当前 UTC 时间 ≥ run_at_dt 且（`last_run_at` 为 NULL 或 `last_run_at` < run_at_dt）时视为「到点」。
  4. **占位**：`UPDATE festival_memory_config SET last_run_at = now() WHERE id = ? AND (last_run_at IS NULL OR last_run_at < run_at_dt)`；仅当更新行数为 1 时表示本实例抢到执行权。
  5. 对抢到执行权的配置：用其 `timezone`、`festival_date`、`min_rounds_in_window` 调用 `get_pairs_with_min_rounds_in_window_sync`，再对每个 (user_id, agent_id) 调用 `extract_festival_and_save(..., config.festival_name, config.festival_date, config.prompt)`。

**描述一条「任务」的数据结构**：即表 `festival_memory_config` 的一行（ORM `FestivalMemoryConfig`）；没有独立的任务队列表，到点判断与防重均基于该行的 `run_at_*` 与 `last_run_at`。

### 2.4 其他相关服务（投递与推送）

- **投递**：`app.services.memory_service`  
  - `get_undelivered_festival_memories`、`deliver_festival_memories_for_user_agent`：在 GET messages / POST completions 时按需把未投递节日记忆写入 chat_history 并更新 `memory.delivery_at`。
- **节日记忆通知**：`app.services.push_notification_service`  
  - `process_festival_memory_push_batch`：由 push 调度器每 15 分钟调用，扫描未投递且未发过 system notification 的节日记忆并发送 FCM。

---

## 3. 数据流简图

```text
evaluation UI 新建/编辑配置
    → POST/PUT /evaluation/admin/festival-memory-configs
    → festival_memory_config 表

push worker 每 5 分钟
    → 读 festival_memory_config（enabled, run_at_*）
    → 到点且占位成功 → get_pairs_with_min_rounds_in_window_sync
    → 对每对 (user_id, agent_id) → extract_festival_and_save
    → 删除旧 Memory + INSERT 新 Memory → memory 表

用户拉消息/发起聊天
    → deliver_festival_memories_for_user_agent
    → 写 chat_history（festival_memory_prompt）+ 更新 memory.delivery_at
```

---

## 4. 关键文件索引

| 职责 | 文件 |
| ---- | ---- |
| 表模型 | `app/models/memory.py`（Memory、FestivalMemoryConfig） |
| Schema | `app/schemas/festival_memory.py` |
| 管理员 API | `app/api/v1/endpoints/festival_memory.py` |
| 抽取与筛选 | `app/services/festival_memory_service.py` |
| 定时任务 | `app/services/push_scheduler_service.py`（_run_festival_memory_extraction） |
| push 进程入口 | `backend/push_worker/main.py` |
| 投递与推送 | `app/services/memory_service.py`、`app/services/push_notification_service.py` |
