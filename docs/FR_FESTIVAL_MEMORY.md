# 节日记忆回忆提取功能

CREATED_BY_AGENT

## 概述

管理员在 evaluation 中配置节日（名称、日期）和提示词，定时任务或立即执行对「在节日当天 00:00 至次日 04:00（UTC）共 28 小时内，该 (用户, 角色) 用户消息数（排除开场白）≥ 30」的组合抽取节日回忆，并写入 `memory` 表。节日记忆通过角色详情接口的 `features.festival_memories` 返回给客户端。

## 数据与模型

- **memory 表**：沿用现有表，新增可选列 `festival_name`、`festival_date`；`memory_type` 取值增加 `festival`。节日记忆语义：`(user_id, agent_id, festival_name, festival_date)` 唯一确定一条，`content` 存该用户与该角色在该节日下的回忆摘要。
- **festival_memory_config 表**：节日记忆抽取配置，字段：`id`, `festival_name`, `festival_date`, `prompt`, `enabled`, `run_at_date`, `run_at_hour`, `last_run_at`, `created_at`, `updated_at`。其中 `run_at_date`（执行日期）、`run_at_hour`（UTC 小时 0–23）表示该配置的「可执行时间」，须满足 `run_at_date >= festival_date`；`last_run_at` 为该配置最近一次被定时任务执行的时间，用于避免同一执行时刻被重复执行。

## 接口

### 角色详情返回 features（节日记忆）

- **GET** `/api/v1/ai/agents/{agent_id}`  
  响应中增加可选字段 `features`；`features.festival_memories` 为当前用户与该角色的节日记忆列表，元素包含：`festival_date`（如 YYYY-MM-DD）、`festival_name`、`memory`（即 `Memory.content`）。

### 管理员 API（仅超级用户）

- **GET** `/api/v1/evaluation/admin/festival-memory-configs`：节日记忆配置列表（支持 skip/limit）。
- **POST** `/api/v1/evaluation/admin/festival-memory-configs`：创建配置（节日名称、节日日期、提示词、是否启用、执行日期、执行时刻 UTC 小时）；执行日期不能早于节日日期。
- **PUT** `/api/v1/evaluation/admin/festival-memory-configs/{config_id}`：更新配置（含执行日期、执行时刻）。
- **DELETE** `/api/v1/evaluation/admin/festival-memory-configs/{config_id}`：删除配置。
- **POST** `/api/v1/evaluation/admin/festival-memory-extraction/run`：立即执行抽取。请求体可传 `config_id` 或直接传 `festival_name`、`festival_date`、`prompt`。返回 `total_pairs`、`success_count`、`failed_count`。

## 抽取逻辑

1. **筛选**：对每条节日配置按其 `festival_date` 确定时间窗「节日当天 00:00 UTC 至次日 04:00 UTC」共 28 小时；从 `chats` 与 `chat_history` 统计在该时间窗内每个 (user_id, agent_id) 会话的用户消息数（排除开场白），仅对**该窗口内**消息数 ≥ 30 的组合进行抽取。
2. **拉取**：按 (user_id, agent_id) 拉取该用户与该角色的单会话消息，格式与现有记忆抽取一致。
3. **LLM**：使用配置的提示词 + 节日名称、日期作为上下文，调用 OpenRouter（默认模型 `mistralai/devstral-2512`）抽取该节日相关回忆摘要。
4. **写入**：同一 (user_id, agent_id, festival_name, festival_date) 先 DELETE 再 INSERT 一条 `memory`（整批替换）。
5. **提示消息**：抽取成功后，在该 (user_id, agent_id) 对应会话的 `chat_history` 中追加一条特殊 AI 消息，用于提示 App/Evaluation「心跳日记已写好，可点击查看」。详见下文「chat_history 提示消息约定」。

## chat_history 提示消息约定

- **写入时机**：每次 `extract_festival_and_save` 成功提交 memory 后，向该会话插入一条提示消息（由 `chat_history_service.add_festival_memory_prompt_message_sync` 写入）。
- **消息结构**：
  - `message.type`：`"ai"`（与现有 AI 消息一致，role 为 assistant）。
  - `message.data.content`：固定模板，当前为 `"{char} 为你写了一份秘密心跳日记。静静查看"`。前端/App 展示时需将 `{char}` 替换为当前角色名。
  - `meta_data`：`agentId` 为角色 ID；`messageType` 为 `"festival_memory_prompt"`；`festivalMemoryId` 为该条提示消息对应的 memory 记录主键 id（写入时由 `add_festival_memory_prompt_message_sync` 写入），用于识别该条为「节日记忆/心跳日记」提示，从而分支渲染与点击行为。
- **消息列表 API**：`GET /api/v1/chats/agents/{agent_id}/messages` 返回的每条消息中，若为上述提示消息，则 `type` 字段为 `"festival_memory_prompt"`（由 `get_messages_paginated` 根据 `meta_data.messageType` 设置），并附带 `festival_memory_id`：该条提示消息对应的 memory 记录 id（整型），来自 meta_data.festivalMemoryId，便于客户端按 id 引用或跳转。App 与 Evaluation 据此展示「{char} 为你写了一份秘密心跳日记。静静查看」，并将「静静查看」作为可点击入口，跳转或弹窗展示对应节日记忆。
- **统计口径**：与统计相关的指标（对话轮数、消息数、会话消息条数等）在计数时**排除**此类记忆提取型消息（即 `meta_data.messageType === 'festival_memory_prompt'` 的 chat_history 记录），后端统计查询与 evaluation 前端展示的条数均不包含该类型消息。

## 定时任务

- 在 `push_scheduler_service` 中注册「节日记忆抽取」任务，使用 **每 5 分钟** 的 `IntervalTrigger` 扫描（启动后立即执行一次，之后每 5 分钟执行一次）。
- 每轮扫描：取当前 UTC 时间 `now`，查询 `festival_memory_config` 中 `enabled = true` 且 `run_at_date`、`run_at_hour` 均非空的配置；对每条配置计算执行时刻 `run_at_datetime = run_at_date + run_at_hour:00`（UTC），仅当 `now >= run_at_datetime` 且（`last_run_at` 为 NULL 或 `last_run_at < run_at_datetime`）时视为「到点」；对到点配置按该配置的节日日期计算 28 小时窗口，筛选该窗口内 (user, agent) 用户消息数 ≥ 30，逐个调用抽取并写入 memory，**执行成功后更新该配置的 `last_run_at = now()`**，从而同一执行时刻只会在某次 5 分钟扫描中执行一次。执行时间不早于节日日期（由创建/更新接口校验 `run_at_date >= festival_date`）。

## Evaluation 页面

- 路径：evaluation 侧边栏「节日记忆提取」。
- 功能：节日配置列表（名称、节日日期、执行日期、执行时刻 UTC、最近执行时间、提示词摘要、启用状态）、新建/编辑/删除配置（表单含执行日期、执行时刻，校验执行日期不早于节日日期）、单条配置「立即执行」、说明「定时任务每 5 分钟扫描，按每条配置的执行时间与 last_run_at 决定是否执行」。

## 关键文件

| 模块       | 文件 |
|------------|------|
| 模型       | `app/models/memory.py`（Memory 扩展、FestivalMemoryConfig） |
| 迁移       | `alembic/versions/20260204_120000_add_festival_memory_fields_and_config.py` |
| 抽取/筛选  | `app/services/festival_memory_service.py`（含抽取成功后写入 chat_history 提示消息） |
| 聊天历史   | `app/services/chat_history_service.py`（add_festival_memory_prompt_message_sync、get_messages_paginated 返回 type festival_memory_prompt） |
| 记忆读取   | `app/services/memory_service.py`（get_festival_memories_for_user_agent） |
| 角色详情   | `app/api/v1/endpoints/agents.py`（GET /{agent_id} 附加 features） |
| Schema     | `app/schemas/agent.py`（AgentFeatures、FestivalMemoryItem）、`app/schemas/festival_memory.py` |
| 管理员 API | `app/api/v1/endpoints/festival_memory.py` |
| 定时任务   | `app/services/push_scheduler_service.py`（_run_festival_memory_extraction） |
| 前端页面   | `evaluation/pages/FestivalMemoryPage.tsx`、`evaluation/App.tsx` |
| API 封装   | `evaluation/services/api.ts`（festivalMemoryApi） |
