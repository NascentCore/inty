# Surprise Snap 功能文档

## 概述

Surprise Snap 指在用户与角色对话达到**可配置轮数**（用户消息数）时，系统自动插入一条「专属角色照」消息（`surprise_snap` 类型）。该消息来自角色运营配置的 `exclusive_photos` 图库，按顺序发放。**是否展示为已解锁**：后端**仅根据 surprise_snap_unlock 表**（即 unlocked 消息 ID 集合）返回 `is_locked`，不依据订阅状态；订阅用户与超级管理员是否按已解锁展示由 **App 端**根据用户订阅状态（及超级管理员身份）判断并展示。免费用户需使用 credit 解锁（扣费在 App 端，后端仅记录解锁状态）。

## 数据与配置

### 角色侧：专属照图库

- **字段**：`agents.exclusive_photos`（JSON 数组）
- **单条结构**：`image_url`（GCS/CDN 地址）、`caption`（文案）、`credits_required`（解锁所需 credit 数，非负整数）
- **管理**：evaluation 角色管理页「专属角色照」区块可增删改；App 侧接口不返回该字段

### 配置：surprise_snap

在 `config.yaml`（或对应环境配置）中增加：

```yaml
surprise_snap:
  enabled_since: "2026-02-12T00:00:00"  # 只统计此时间之后的用户消息；不配或为空则不触发
  trigger_rounds: [3, 8, 15]            # 用户消息数达到这些轮数时触发（可改）
```

- **enabled_since**：仅统计该时间之后的用户（human）消息数；为 `null` 或未配置时功能关闭
- **trigger_rounds**：当「自 enabled_since 以来的用户消息数」等于其中某一值时，触发一次发放

## 后端实现要点

### 触发时机

- 在 **POST /api/v1/chat/completions/{agent_id}** 中，用户消息写入且 `record_usage` 之后调用 `try_trigger_surprise_snap(db, session_id, user_id, agent_id)`
- 若本次满足条件，会向 `chat_history` 插入一条 `type: "surprise_snap"` 的消息，并更新该 user+agent 的发放进度（`next_photo_index`）

### 发放规则

- 同一 **user + agent** 按 `exclusive_photos` 数组**顺序**发放，每条只发一次
- 若角色 `exclusive_photos` 为空或已发完（`next_photo_index >= len(photos)`），不再触发
- 统计的「用户消息数」为自 **enabled_since** 以来该会话中 type 为 human/HumanMessage 的消息条数；达到 `trigger_rounds` 中某一值且当前还有未发放的图时触发

### 数据库表

- **surprise_snap_progress**：`user_id`、`agent_id`、`next_photo_index`，唯一约束 (user_id, agent_id)，记录该用户与该角色已发到第几张图
- **surprise_snap_unlock**：`user_id`、`message_id`（FK chat_history.id），唯一约束 (user_id, message_id)，记录免费用户已解锁的 surprise_snap 消息

### 消息展示与解锁

- **GET /api/v1/chats/agents/{agent_id}/messages**：拉取消息列表时，对 `type === "surprise_snap"` 的消息补充 `media_url`（CDN）、`caption`、`price`、`is_locked`
  - **is_locked**：后端**仅根据 surprise_snap_unlock 表**（该 message_id 是否在已解锁集合中）计算，不依据订阅状态；**订阅用户与超级管理员的是否展示为已解锁由 App 端根据订阅状态/管理员身份判断**
- **POST /api/v1/chats/surprise-snap/unlock**：Body `{ "message_id": number }`，校验消息为 surprise_snap 且属于当前用户会话后写入 `surprise_snap_unlock`；扣 credit 由 App 完成，后端只记解锁状态。重复调用同一 message_id 视为成功（幂等）

### 聊天接口中的 choice 返回

- 当**本次**请求触发了 Surprise Snap 时，响应 `data.choices` 中会多一条 choice，`message.type === "surprise_snap"`，且含 `id`、`media_url`、`caption`、`price`、`is_locked`，与消息列表中的结构一致。`is_locked` 由后端**仅按 surprise_snap_unlock 表**计算；**订阅用户与超级管理员是否按已解锁展示由 App 端根据订阅状态/管理员身份处理**

## 接口汇总

| 接口 | 说明 |
|------|------|
| POST /api/v1/chat/completions/{agent_id} | 发消息后可能触发插入 surprise_snap，并在同次响应 choices 中返回该条（若触发） |
| GET /api/v1/chats/agents/{agent_id}/messages | 返回列表中包含 surprise_snap 消息，带 media_url、caption、price、is_locked |
| POST /api/v1/chats/surprise-snap/unlock | 免费用户解锁某条 surprise_snap（Body: message_id），后端记录解锁状态 |

## 相关代码位置

- 配置解析：`app/utils/config.py`（SurpriseSnapConfig、_parse_surprise_snap_config）
- 模型：`app/models/surprise_snap.py`、`app/models/agent.py`（exclusive_photos）
- 服务：`app/services/surprise_snap_service.py`（触发、解锁、已解锁 ID 查询）、`app/services/chat_history_service.py`（插入 surprise_snap、统计用户消息数、单条展示信息、get_messages_paginated 的 is_locked/media_url 等）
- 接口：`app/api/v1/endpoints/chat.py`（触发 + choice 追加）、`app/api/v1/endpoints/chats.py`（消息列表参数、unlock 路由）
- Schema：`app/schemas/agent.py`（ExclusivePhotoItem）、`app/schemas/evaluation.py`（SurpriseSnapUnlockRequest）

## 测试

- E2E：`tests/app/api/v1/endpoints/test_surprise_snap_e2e.py`，覆盖触发、消息列表、解锁成功/幂等/403、无 exclusive_photos 不触发等
- 测试环境需在 `devops/config.yaml.test` 中配置 `surprise_snap.enabled_since` 与 `trigger_rounds`（如 `trigger_rounds: [1]` 便于用例触发）
