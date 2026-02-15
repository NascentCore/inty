# 记忆功能实现总结

CREATED_BY_AGENT

## 功能概述

从用户与多角色 AI 的会话中提取记忆，通过定时任务写入数据库，并在**对话**和**生图**时把记忆（仅 Part 1 用户画像摘要）注入到 `##User Memory` 段，供模型使用。设计参考飞书《记忆提取执行策略》；提示词为英文，强调跨角色一致、用户偏好与 AI 输出规则分离，仅 Part 1 嵌入。

## 实现模块

### 1. 库表与迁移

- **ORM**：`app/models/memory.py`
  - **Memory**：`user_id`, `memory_type`（如 `user_common`）, `agent_id`（`user_common` 为 `NULL`）, `content`, `extracted_at`；按每次抽取整批替换，仅保留最新。
  - **MemoryExtractionLog**：`user_id`, `memory_type`, `extracted_at`, `messages_processed_count`, `memory_items_count`, `status`（`success` | `partial` | `failed`），`duration_seconds`（当次抽取总耗时秒）、`prompt_tokens`（LLM 输入 token 数）、`completion_tokens`（LLM 输出 token 数）；用于触发判断与可观测、监控与成本分析。
- **迁移**：`alembic/versions/20260127_120000_add_memory_tables.py`（revision `a7b8c9d0e1f2`）；`alembic/versions/20260127_140000_add_memory_extraction_log_metrics.py`（revision `b8c9d0e1f2a3`，为 `memory_extraction_log` 增加上述三列）。

### 2. 配置

- **位置**：`app/core/config.py` — `MemoryExtractionConfig`
- **字段**：
  - `enabled`：是否启用记忆抽取定时任务，默认 `True`
  - `model`：OpenRouter 模型 id（如 `mistralai/devstral-2512`），为空时使用代码内默认 `mistralai/devstral-2512`
  - `cron_hour`：UTC 小时，每日执行，默认 `3`
  - `trigger_new_user_messages`：新用户总消息数阈值，默认 `30`
  - `trigger_incremental_messages`：已提取用户自上次后新增消息数阈值，默认 `30`
- 记忆抽取使用 OpenRouter（`app.utils.openai_client.chat_completion_for_extraction()`，基于 AsyncOpenAI，`agent.base_url` 与 `agent.api_key`）。

### 3. 记忆读取服务（`app/services/memory_service.py`）

- **get_user_memory_for_prompt_sync(user_id, memory_type)**：同步从 `memory` 表读取，条件：`user_id`、`memory_type`、`agent_id IS NULL`，按 `extracted_at DESC` 取最新，多条用 `\n\n` 拼接；供对话注入。
- **get_user_memory_for_prompt_async(db, user_id, memory_type)**：异步版本，供生图 `build_user_info_prompt_block` 使用。
- 当前仅使用 `user_common`、`agent_id IS NULL` 的记忆。

### 4. 记忆抽取服务（`app/services/memory_extraction_service.py`）

- **get_users_to_extract(db)**：筛选待抽取用户：
  - 新用户：总消息数 ≥ `trigger_new_user_messages`
  - 已提取用户：自上次 `extracted_at` 后新增消息数 ≥ `trigger_incremental_messages`
- **get_all_messages_for_user(user_id)**：拉取该用户在所有会话中的全部消息 `(role, content)`，按 `created_at` 升序；不按 agent 过滤，不限制条数。
- **extract_and_save(db, user_id)**：拉取全量消息、拼接 `# User chat history` 与提示词、使用 **OpenRouter**（`app.utils.openai_client.chat_completion_for_extraction`，默认模型 `mistralai/devstral-2512`）调用 LLM、从响应 `usage` 读取 token 消耗、记录端到端耗时、解析 Part 1、`DELETE` 该用户 `user_common` 且 `agent_id IS NULL` 的旧记忆后 `INSERT` 新记忆与 `memory_extraction_log`（含 `duration_seconds`、`prompt_tokens`、`completion_tokens`）。
- **提示词**：`app/core/prompting/memory_extraction_prompt.txt`（英文）。
- **\_extract_part1_summary(full_analysis)**：从 LLM 完整回复中解析 Part 1；支持 `Part 1`、`**About this user**`、`**关于这位用户**` 等中英文 fallback 正则；Part 1 过短（≤50 字）时回退到约 2000 字或全文。

### 5. 定时任务（`app/services/push_scheduler_service.py`）

- 当 `memory_extraction.enabled` 为真时，注册 `CronTrigger(hour=cron_hour, minute=0)` 的 `_run_memory_extraction` 任务（id: `run_memory_extraction`），并设置 `next_run_time=datetime.datetime.now()`，故**启动后立即执行一次**，之后每日 UTC `cron_hour:00` 执行。
- `_run_memory_extraction`：调用 `get_users_to_extract` 后对每个 `user_id` 执行 `extract_and_save`；与 push 调度、`backend/push_worker/start_push_worker.sh` 等同进程。

### 6. 对话与生图注入

- **对话**：`app/core/agent/agent.py` 的 `_get_user_profile_sync` 在 `##User Information` 后追加 `\n\n##User Memory\n` + `get_user_memory_for_prompt_sync(user_id)`。基础用户信息块可缓存，记忆不缓存。
- **生图**：`app/services/user_service.py` 的 `build_user_info_prompt_block` 在 `##User Information` 后追加 `\n\n##User Memory\n` + `get_user_memory_for_prompt_async(db, user_id)`；同上，记忆不缓存。

### 7. 手动测试脚本（`scripts/run_memory_extraction.py`）

- **用法**（仓库根目录，`PYTHONPATH=.`）：
  - `python scripts/run_memory_extraction.py --user-id <USER_UUID>`：对指定用户执行抽取并写入 DB。
  - `python scripts/run_memory_extraction.py --user-id <USER_UUID> --dry-run`：仅拉取该用户消息并打印条数与示例，不调 LLM、不写 memory。

## 提示词与 Part 1 解析

- **memory_extraction_prompt.txt**：英文，要求从多角色会话中抽取跨角色一致的用户信息；明确区分「用户偏好」与「AI 输出规则」，仅前者进入 Part 1。
- **输出结构**：Part 1（用户画像，用于嵌入）、Part 2（逐维详细表+是否跨角色一致）、Part 3（仅单角色有用信息，不嵌入）、Part 4（置信度）。**仅 Part 1 持久化并注入到 `##User Memory`。**
- **Part 1 解析**：`_extract_part1_summary` 通过多种正则匹配 `Part 1`、`**About this user**`、`**关于这位用户**` 等，并裁剪首尾 `---`；若均未命中或结果过短，则回退到 `**关于这位用户**` / `**About this user**` 段或全文前 2000 字。

## 文件结构

```
app/
├── core/
│   ├── config.py                    # MemoryExtractionConfig 及 load_config 集成
│   ├── prompting/
│   │   └── memory_extraction_prompt.txt   # 记忆抽取提示词（英文）
│   └── agent/
│       └── agent.py                 # _get_user_profile_sync 中注入 ##User Memory
├── models/
│   └── memory.py                    # Memory, MemoryExtractionLog
└── services/
    ├── memory_service.py            # get_user_memory_for_prompt_sync/async
    ├── memory_extraction_service.py # get_users_to_extract, get_all_messages_for_user, extract_and_save, _extract_part1_summary
    ├── push_scheduler_service.py    # 记忆抽取 Cron 任务 _run_memory_extraction
    └── user_service.py              # build_user_info_prompt_block 中注入 ##User Memory

alembic/versions/
├── 20260127_120000_add_memory_tables.py   # revision a7b8c9d0e1f2
└── 20260127_140000_add_memory_extraction_log_metrics.py   # revision b8c9d0e1f2a3，duration_seconds/prompt_tokens/completion_tokens

scripts/
└── run_memory_extraction.py         # --user-id 必填，--dry-run 仅拉消息打条数
```

## 使用与测试

1. **配置**：在 `config.yaml` 的 `memory_extraction` 下设置 `enabled`、`cron_hour`、`trigger_new_user_messages`、`trigger_incremental_messages`，可选 `model`。
2. **迁移**：执行 `alembic upgrade head` 以创建 `memory`、`memory_extraction_log` 表。
3. **定时任务**：启动 push worker（含 scheduler）后，在 `memory_extraction.enabled=true` 时**启动后立即执行一次**记忆抽取，之后每日 UTC `cron_hour:00` 自动执行。
4. **手动抽取**：`PYTHONPATH=. python scripts/run_memory_extraction.py --user-id <UUID>`；`--dry-run` 可用于验证消息拉取与条数。
5. **监控与成本**：`memory_extraction_log` 的 `duration_seconds`、`prompt_tokens`、`completion_tokens` 可用于监控单用户抽取耗时与 LLM token 消耗、成本分析。

## 节日记忆提取（Festival Memory）

- 管理员在 evaluation 侧边栏「节日记忆提取」页面配置节日（名称、节日日期）与提示词，以及**执行日期**、**执行时刻（UTC 小时 0–23）**、可选**窗口内最少用户消息数**（默认 15）、可选**模型配置**（llm_config JSON，不配则使用默认模型）；执行日期不能早于节日日期。可立即执行或由定时任务对「在节日当天 0 点至次日 4 点（UTC）28 小时内用户消息达到配置的窗口内最少条数（默认 15）以上」的 (用户, 角色) 组合抽取节日回忆并写入 `memory` 表。
- **定时任务**：每 **5 分钟** 扫描一次；仅处理 `run_at_date`、`run_at_hour` 均已配置且「当前 UTC 时间 ≥ 执行时刻」且「该配置尚未在此执行时刻跑过」（通过 `last_run_at` 判断）的配置；对每条到点配置按该节日日期计算 28 小时窗口并筛选该窗口内用户消息 ≥ 配置的 `min_rounds_in_window`（默认 15）的 (user, agent)，执行成功后更新该配置的 `last_run_at`，保证同一执行时刻只执行一次。
- 节日记忆通过角色详情接口 `GET /api/v1/ai/agents/{agent_id}` 的响应字段 `features.festival_memories` 返回。
- 后端功能说明见仓库根目录 `docs/FR_FESTIVAL_MEMORY.md`。

## 后续扩展（参考）

- 支持 `user_agent` 类型及按 `agent_id` 的记忆与注入策略。
- 调整 Part 1 解析或提示词以支持更多输出格式。
- 在 `memory_extraction_log` 基础上增加监控与告警（如聚合报表、告警阈值）。
