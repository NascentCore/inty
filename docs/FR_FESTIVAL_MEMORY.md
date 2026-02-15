# 节日记忆回忆提取功能

CREATED_BY_AGENT

## 概述

管理员在 evaluation 中配置节日（名称、日期）、时区和提示词，定时任务或立即执行对「在配置时区下节日自然日 00:00 至次日 04:00 共 28 小时（换算为 UTC）内，该 (用户, 角色) 用户消息数（排除开场白）≥ 配置的 `min_rounds_in_window`（可选，默认 15）」的组合抽取节日回忆，并写入 `memory` 表。节日记忆通过角色详情接口的 `features.festival_memories` 返回给客户端。

## 数据与模型

- **memory 表**：沿用现有表，新增可选列 `festival_name`、`festival_date`、**`delivery_at`**；`memory_type` 取值增加 `festival`。节日记忆语义：`(user_id, agent_id, festival_name, festival_date)` 唯一确定一条，`content` 存该用户与该角色在该节日下的回忆摘要。**`delivery_at`**（DateTime with timezone，可空）：节日记忆提示**首次**投递到会话的时间；`NULL` 表示尚未投递，仅在用户发起聊天或拉取消息列表时按需写入 chat_history 并更新该字段。
- **festival_memory_config 表**：节日记忆抽取配置，字段：`id`, `festival_name`, `festival_date`, `prompt`, `enabled`, **`timezone`**（节日与执行时间所属时区，IANA 名如 Asia/Shanghai，默认 UTC）, `run_at_date`, `run_at_hour`, **`min_rounds_in_window`**（窗口内最少用户消息轮数，可选，NULL 表示默认 15）, `last_run_at`, `created_at`, `updated_at`。其中 **节日日期与执行日期/时刻均为该 timezone 下的本地值**：`festival_date` 为「该时区下的自然日」，`run_at_date`（执行日期）、`run_at_hour`（该时区下本地小时 0–23）表示该配置的「可执行时间」，须满足 `run_at_date >= festival_date`；定时任务到点判断时将 (run_at_date, run_at_hour, timezone) 转为 UTC 后与当前时间比较。`last_run_at` 为该配置最近一次被定时任务执行的时间（UTC），用于避免同一执行时刻被重复执行。

## 接口

### 角色详情返回 features（节日记忆）

- **GET** `/api/v1/ai/agents/{agent_id}`  
  响应中增加可选字段 `features`；`features.festival_memories` 为当前用户与该角色的节日记忆列表，每项包含：**memory_id**（memory 表主键 id，便于客户端按 id 引用）、`festival_date`（如 YYYY-MM-DD）、`festival_name`、`memory`（即 `Memory.content`）。

### 按版本隐藏记忆提醒

- 配置项 **min_app_version_code_for_festival_memory**（`app.min_app_version_code_for_festival_memory`，默认 0）：仅当请求头 **appVersionCode** 大于等于此值时，才返回「记忆提醒」相关数据。
- 当请求头 **appVersionCode** **小于**该配置时：
  - **消息列表**（`GET /agents/{agent_id}/messages`、`GET /agents/{agent_id}/detail`、`GET /{chat_id}/detail`）：不返回 `type === "festival_memory_prompt"` 的消息（仅过滤当前页，total 不减少，旧版客户端看到的 total 可能包含被隐藏的条数）。
  - **角色详情**（`GET /api/v1/ai/agents/{agent_id}`）：不返回 `features.festival_memories`（或返回空列表）。
- **版本号未传**时视为不限制，照常返回（避免未带版本的客户端被误判为旧版）。

### 管理员 API（仅超级用户）

- **GET** `/api/v1/evaluation/admin/festival-memory-configs`：节日记忆配置列表（支持 skip/limit）。
- **POST** `/api/v1/evaluation/admin/festival-memory-configs`：创建配置（节日名称、节日日期、提示词、是否启用、**timezone**（默认 UTC）、执行日期、执行时刻（该时区下本地小时）、可选 **min_rounds_in_window**（窗口内最少用户消息轮数，不传则默认 15））；执行日期不能早于节日日期。
- **PUT** `/api/v1/evaluation/admin/festival-memory-configs/{config_id}`：更新配置（含 timezone、执行日期、执行时刻、min_rounds_in_window）。
- **DELETE** `/api/v1/evaluation/admin/festival-memory-configs/{config_id}`：删除配置。
- **POST** `/api/v1/evaluation/admin/festival-memory-extraction/run`：立即执行抽取。请求体可传 `config_id` 或直接传 `festival_name`、`festival_date`、`prompt`、可选 `timezone`（未传 config_id 时用于窗口计算，默认 UTC）、可选 `min_rounds_in_window`（未传 config_id 时生效，不传则默认 15）。返回 `total_pairs`、`success_count`、`failed_count`。

## 抽取逻辑

1. **筛选**：对每条节日配置按其 `timezone` 与 `festival_date` 确定时间窗：**该时区下节日自然日 00:00 至次日 04:00**（共 28 小时）换算为 UTC 的区间；从 `chats` 与 `chat_history` 统计在该时间窗内每个 (user_id, agent_id) 会话的用户消息数（排除开场白），仅对**该窗口内**消息数 ≥ 配置的 `min_rounds_in_window`（可选，默认 15）的组合进行抽取。
2. **拉取**：按 (user_id, agent_id) 拉取该用户与该角色的单会话消息，格式与现有记忆抽取一致。
3. **LLM**：使用配置的提示词 + 节日名称、日期作为上下文，调用 OpenRouter（默认模型 `mistralai/devstral-2512`）抽取该节日相关回忆摘要。
4. **写入**：同一 (user_id, agent_id, festival_name, festival_date) 先 DELETE 再 INSERT 一条 `memory`（整批替换），**不**在此处写入 chat_history；`delivery_at` 保持 NULL。
5. **提示消息**：改为按需投递。在用户**发起聊天**或**拉取消息列表**时，对 (user_id, agent_id) 下 `delivery_at IS NULL` 的节日记忆执行投递（写入 chat_history 并更新 `memory.delivery_at`）。详见下文「chat_history 提示消息约定」。

## chat_history 提示消息约定

- **写入时机**：在用户**发起聊天**（`POST /chat/completions/{agent_id}`）或**拉取消息列表**（`GET /api/v1/chats/agents/{agent_id}/messages`）时按需投递：对 (user_id, agent_id) 下 `delivery_at IS NULL` 的节日记忆执行投递（调用 `chat_history_service.add_festival_memory_prompt_message_sync` 写入 chat_history，并更新 `memory.delivery_at`）。发起聊天时，当次响应的 **choices** 中会在主 AI 回复之后追加本次投递的节日提醒（与消息列表中的 `festival_memory_prompt` 结构一致）。
- **幂等**：按 (session_id, agent_id, festival_name, festival_date) 幂等：若该会话下已存在同角色、同节日的提示消息则不再插入，直接返回已有消息 id；已投递（`delivery_at` 非空）的 memory 不再重复写入 chat_history。
- **消息结构**：
  - `message.type`：`"ai"`（与现有 AI 消息一致，role 为 assistant）。
  - `message.data.content`：固定模板，当前为 `"{char} wrote you a secret heartbeat diary. Take a quiet look."`。前端/App 展示时需将 `{char}` 替换为当前角色名。
  - `meta_data`：`agentId` 为角色 ID；`messageType` 为 `"festival_memory_prompt"`；`festivalMemoryId` 为该条提示消息对应的 memory 记录主键 id；**`festivalName`**、**`festivalDate`**（ISO 日期字符串）用于幂等查询与前端展示。
- **消息列表 API**：`GET /api/v1/chats/agents/{agent_id}/messages` 返回的每条消息中，若为上述提示消息，则 `type` 字段为 `"festival_memory_prompt"`（由 `get_messages_paginated` 根据 `meta_data.messageType` 设置），并附带 `festival_memory_id`：该条提示消息对应的 memory 记录 id（整型），来自 meta_data.festivalMemoryId，便于客户端按 id 引用或跳转。该类消息的 **role** 与 **sender_type** 接口返回为 **null**，以便不识别的旧版客户端不将其当作普通 AI 消息展示；新版客户端应以 type 为准进行渲染。App 与 Evaluation 据此展示「{char} wrote you a secret heartbeat diary. Take a quiet look.」，并将「Take a quiet look」作为可点击入口，跳转或弹窗展示对应节日记忆。
- **统计口径**：与统计相关的指标（对话轮数、消息数、会话消息条数等）在计数时**排除**此类记忆提取型消息（即 `meta_data.messageType === 'festival_memory_prompt'` 的 chat_history 记录），后端统计查询与 evaluation 前端展示的条数均不包含该类型消息。

## 定时任务

- 在 `push_scheduler_service` 中注册「节日记忆抽取」任务，使用 **每 5 分钟** 的 `IntervalTrigger` 扫描（启动后立即执行一次，之后每 5 分钟执行一次）。
- **节日记忆通知**：push worker 中新增「节日记忆通知」任务（可选配置 `push_notification.festival_memory_enabled`，默认 true）。每 15 分钟扫描存在「未投递且未发过 system notification」的节日记忆的 (user_id, agent_id)，发送 FCM 推送；点击通知进入该角色 **Love Journal 页并定位到对应记忆条目**。投递仍由 GET messages / POST completions 完成，不在 push worker 内写 chat_history。
- 每轮扫描：取当前 UTC 时间 `now`，查询 `festival_memory_config` 中 `enabled = true` 且 `run_at_date`、`run_at_hour` 均非空的配置；对每条配置将 **(run_at_date, run_at_hour)** 按该配置的 **timezone** 解释为本地日期+时刻，换算为 UTC 得到 `run_at_dt_utc`，仅当 `now >= run_at_dt_utc` 且（`last_run_at` 为 NULL 或 `last_run_at < run_at_dt_utc`）时视为「到点」。对到点配置采用 **先占位再执行**：先执行 `UPDATE festival_memory_config SET last_run_at = now() WHERE id = ? AND (last_run_at IS NULL OR last_run_at < run_at_dt_utc)`，仅当更新行数为 1 时表示本实例抢到执行权，再按该配置的 **timezone** 与 **festival_date** 计算 28 小时窗口、筛选该窗口内 (user, agent) 用户消息数 ≥ `min_rounds_in_window` 的组合并逐个调用抽取；若更新行数不为 1 则跳过该配置（已被其他实例执行或已执行过）。从而多实例下同一 config 在同一执行时刻只会被一个实例执行一次。执行时间不早于节日日期（由创建/更新接口校验 `run_at_date >= festival_date`）。

## Evaluation 页面

- 路径：evaluation 侧边栏「节日记忆提取」。
- 功能：节日配置列表（名称、节日日期、执行日期、执行时刻 UTC、最近执行时间、提示词摘要、启用状态）、新建/编辑/删除配置（表单含执行日期、执行时刻，校验执行日期不早于节日日期）、单条配置「立即执行」、说明「定时任务每 5 分钟扫描，按每条配置的执行时间与 last_run_at 决定是否执行」。

## 服务层重构与离线脚本（实现变更记录）

### festival_memory_service 重构

- **可组合函数**：拉消息、拼 prompt、调 LLM、写库 拆分为可复用单元，便于写库与「只出 JSON」两种路径共用。
- **`assemble_args(messages, festival_name, festival_date, prompt_template)`**：根据会话消息与节日参数组装 `chat_completion_for_extraction`（openai_client）的 (full_prompt, model, max_tokens, temperature)，供 `extract_festival_and_save` 与 `extract_festival_to_dict` 复用。
- **`summarize_memory_from_messages_between_user_and_agent(user_id, agent_id, festival_name, festival_date, prompt_template)`**：拉取该 (user_id, agent_id) 会话消息 → 调用 LLM 抽取摘要 → 返回**未持久化**的 `Memory` 对象；无消息、摘要过短或 LLM 异常时返回 `None`。写库与 to_dict 均先调此函数再分别做「delete + add + commit」或「转 dict」。
- **`extract_festival_and_save`**：先 `summarize_memory_from_messages_between_user_and_agent`，若得 `Memory` 则对同 (user_id, agent_id, festival_name, festival_date) 做 DELETE 后 INSERT 并 commit。
- **`extract_festival_to_dict`**：仅用于离线脚本；先 `summarize_memory_from_messages_between_user_and_agent`，再转为与下文 query 一致的 dict 结构，可选附带 user_name、agent_name。
- **`query_festival_memories_from_db(db, festival_name, festival_date)`**：从主库 `memory` 表按节日名称与日期查询已有节日记忆，返回与 `extract_festival_to_dict` 相同结构的 dict 列表（含 user_name、agent_name）。不写库、不调 LLM，供离线 `--query` 使用。
- **移除**：`get_session_id_for_user_agent_sync`（无其他引用）。

### 离线脚本

- **run_festival_memory_extraction_to_json.py**  
  - 必填 `--festival-name`、`--festival-date`、`--output`；抽取模式需 `--prompt` 或 `--prompt-file`；可选 `--timezone`、`--min-rounds`、`--limit`、`--config`。  
  - **`--query`**：仅从 memory 表查询已有节日记忆并写入 JSON，不执行抽取。输出中 `memories` 按 (user_name, agent_name) 排序。  
  - 示例（仅查询）：`python scripts/run_festival_memory_extraction_to_json.py --festival-name "测试节日20260201" --festival-date 2026-02-01 --prompt-file festival_memory_prompt.txt --output tmp/backend_out.json --timezone America/Los_Angeles --min-rounds 50 --query`

- **sort_festival_memory_json.py**（新）  
  - 对 `run_festival_memory_extraction_to_json` 或 `--query` 输出的 JSON，按 (user_name, agent_name) 排序其中的 `memories` 并写回原文件。  
  - 用法：`python scripts/sort_festival_memory_json.py tmp/out.json` 或 `python scripts/sort_festival_memory_json.py --input tmp/out.json`

## 关键文件

|模块|文件|
|----|----|
|模型|`app/models/memory.py`（Memory 扩展、FestivalMemoryConfig）|
|迁移|`alembic/versions/20260204_120000_add_festival_memory_fields_and_config.py`、`alembic/versions/20260213_120000_add_delivery_at_to_memory.py`|
|抽取/筛选|`app/services/festival_memory_service.py`（assemble_args、summarize_memory_from_messages_between_user_and_agent、extract_festival_and_save、extract_festival_to_dict、query_festival_memories_from_db；抽取成功后仅写 memory，不写 chat_history）|
|投递服务|`app/services/memory_service.py`（get_undelivered_festival_memories、deliver_festival_memories_for_user_agent）|
|聊天历史|`app/services/chat_history_service.py`（add_festival_memory_prompt_message_sync、get_festival_memory_prompt_content_for_agent_sync、get_messages_paginated）|
|记忆读取|`app/services/memory_service.py`（get_festival_memories_for_user_agent）|
|角色详情|`app/api/v1/endpoints/agents.py`（GET /{agent_id} 附加 features）|
|Schema|`app/schemas/agent.py`（AgentFeatures、FestivalMemoryItem）、`app/schemas/festival_memory.py`|
|管理员 API|`app/api/v1/endpoints/festival_memory.py`|
|定时任务|`app/services/push_scheduler_service.py`（\_run_festival_memory_extraction）|
|前端页面|`evaluation/pages/FestivalMemoryPage.tsx`、`evaluation/App.tsx`|
|API 封装|`evaluation/services/api.ts`（festivalMemoryApi）|
|离线脚本|`scripts/run_festival_memory_extraction_to_json.py`（抽取或 --query 写 JSON）、`scripts/sort_festival_memory_json.py`（按 user_name、agent_name 排序 JSON）|
