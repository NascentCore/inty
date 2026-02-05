# 节日记忆回忆提取功能

CREATED_BY_AGENT

## 概述

管理员在 evaluation 中配置节日（名称、日期）和提示词，定时任务或立即执行对「用户 + 角色」聊天轮数 ≥ 30 的组合抽取节日回忆，并写入 `memory` 表。节日记忆通过角色详情接口的 `features.festival_memories` 返回给客户端。

## 数据与模型

- **memory 表**：沿用现有表，新增可选列 `festival_name`、`festival_date`；`memory_type` 取值增加 `festival`。节日记忆语义：`(user_id, agent_id, festival_name, festival_date)` 唯一确定一条，`content` 存该用户与该角色在该节日下的回忆摘要。
- **festival_memory_config 表**：节日记忆抽取配置，字段：`id`, `festival_name`, `festival_date`, `prompt`, `enabled`, `created_at`, `updated_at`。

## 接口

### 角色详情返回 features（节日记忆）

- **GET** `/api/v1/ai/agents/{agent_id}`  
  响应中增加可选字段 `features`；`features.festival_memories` 为当前用户与该角色的节日记忆列表，元素包含：`festival_date`（如 YYYY-MM-DD）、`festival_name`、`memory`（即 `Memory.content`）。

### 管理员 API（仅超级用户）

- **GET** `/api/v1/evaluation/admin/festival-memory-configs`：节日记忆配置列表（支持 skip/limit）。
- **POST** `/api/v1/evaluation/admin/festival-memory-configs`：创建配置（节日名称、日期、提示词、是否启用）。
- **PUT** `/api/v1/evaluation/admin/festival-memory-configs/{config_id}`：更新配置。
- **DELETE** `/api/v1/evaluation/admin/festival-memory-configs/{config_id}`：删除配置。
- **POST** `/api/v1/evaluation/admin/festival-memory-extraction/run`：立即执行抽取。请求体可传 `config_id` 或直接传 `festival_name`、`festival_date`、`prompt`。返回 `total_pairs`、`success_count`、`failed_count`。

## 抽取逻辑

1. **筛选**：从 `chats` 与 `chat_history` 统计每个 (user_id, agent_id) 会话的用户消息数（排除开场白），仅对消息数 ≥ 30 的组合进行抽取。
2. **拉取**：按 (user_id, agent_id) 拉取该用户与该角色的单会话消息，格式与现有记忆抽取一致。
3. **LLM**：使用配置的提示词 + 节日名称、日期作为上下文，调用 OpenRouter（默认模型 `mistralai/devstral-2512`）抽取该节日相关回忆摘要。
4. **写入**：同一 (user_id, agent_id, festival_name, festival_date) 先 DELETE 再 INSERT 一条 `memory`（整批替换）。

## 定时任务

- 在 `push_scheduler_service` 中注册「节日记忆抽取」任务，每日 UTC 某时（默认在记忆抽取任务后 1 小时）执行。
- 任务读取 `festival_memory_config` 中 `enabled = true` 的配置，对每个配置筛选 (user, agent) 轮数 ≥ 30，逐个调用抽取并写入 memory。

## Evaluation 页面

- 路径：evaluation 侧边栏「节日记忆提取」。
- 功能：节日配置列表（名称、日期、提示词摘要、启用状态）、新建/编辑/删除配置、单条配置「立即执行」、说明「系统将按配置的定时任务自动执行提取」。

## 关键文件

| 模块       | 文件 |
|------------|------|
| 模型       | `app/models/memory.py`（Memory 扩展、FestivalMemoryConfig） |
| 迁移       | `alembic/versions/20260204_120000_add_festival_memory_fields_and_config.py` |
| 抽取/筛选  | `app/services/festival_memory_service.py` |
| 记忆读取   | `app/services/memory_service.py`（get_festival_memories_for_user_agent） |
| 角色详情   | `app/api/v1/endpoints/agents.py`（GET /{agent_id} 附加 features） |
| Schema     | `app/schemas/agent.py`（AgentFeatures、FestivalMemoryItem）、`app/schemas/festival_memory.py` |
| 管理员 API | `app/api/v1/endpoints/festival_memory.py` |
| 定时任务   | `app/services/push_scheduler_service.py`（_run_festival_memory_extraction） |
| 前端页面   | `evaluation/pages/FestivalMemoryPage.tsx`、`evaluation/App.tsx` |
| API 封装   | `evaluation/services/api.ts`（festivalMemoryApi） |
