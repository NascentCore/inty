# 推送通知系统

## 概述

推送通知系统实现了 Firebase FCM 主动推送功能，当用户与角色发起聊天后，根据分阶段策略（10分钟、30分钟、2小时）主动发送系统通知，使用 Agent 生成个性化消息内容，以维持用户活跃度。

## 架构设计

### 核心组件

1. **推送历史模型** (`app/models/push_notification.py`)
   - `PushNotificationHistory`: 记录推送历史，避免重复发送
   - 唯一约束：`(chat_id, stage)` 确保每个聊天在每个阶段只发送一次

2. **推送服务** (`app/services/push_notification_service.py`)
   - `get_chats_needing_push()`: 查询需要推送的聊天会话
   - `generate_agent_message()`: 使用 Agent 生成主动消息
   - `send_push_notification()`: 发送 FCM 推送
   - `record_push_history()`: 记录推送历史

3. **定时任务调度** (`app/services/push_scheduler_service.py`)
   - 使用 APScheduler 实现分阶段聊天推送与节日记忆通知
   - 10分钟推送：每5分钟检查一次
   - 30分钟推送：每10分钟检查一次
   - 2小时推送：每30分钟检查一次
   - **节日记忆通知**（可选，`push_notification.festival_memory_enabled`）：每 15 分钟扫描未投递且未发过 system notification 的节日记忆，发送 FCM；点击进入该角色 Love Journal 并定位到对应记忆条目。`push_type = "festival_memory"`，`stage = "festival"`。

4. **独立服务入口** (`backend/push_worker/main.py`)
   - 可单独运行的服务进程
   - 初始化 Firebase、数据库连接和 AgentManager
   - 支持优雅关闭（SIGTERM/SIGINT）

5. **提示词模板** (`app/core/prompting/push_message_prompt.py`)
   - 构建主动推送消息的提示词
   - 支持根据推送阶段生成不同的提示词

## 推送策略

### 分阶段推送

系统实现了三个推送阶段：

- **10分钟推送**：用户最后一条消息后10分钟
- **30分钟推送**：用户最后一条消息后30分钟
- **2小时推送**：用户最后一条消息后2小时

### 推送条件

推送仅在以下条件满足时触发：

1. 聊天会话处于活跃状态（`is_active = true`）
2. Agent 未被删除（`deleted_at IS NULL`）
3. 用户未被删除（`deleted_at IS NULL`）
4. 聊天会话中存在用户消息（非仅开场白）
5. 距离最后一条用户消息的时间达到对应阶段阈值
6. 该阶段尚未发送过推送（通过 `push_notification_history` 表检查）

### 防重复发送

- 使用数据库唯一约束 `(chat_id, stage)` 确保每个聊天在每个阶段只发送一次
- 在发送前检查推送历史，避免重复发送

### 推送类型（push_type）

- `no_chat` / `recent_chat`：分阶段聊天推送，`stage` 为 10min / 30min / 2h / 24h / 48h 等。
- **`festival_memory`**：节日记忆通知。扫描存在「未投递且未发过 system notification」的节日记忆的 (user_id, agent_id)，发送 FCM；**按版本门控**：仅当用户 `last_android_app_version_code` ≥ `min_app_version_code_for_festival_memory` 时发送（与 in-app 节日记忆门控一致）。去重以 `memory.system_notification_sent_at` 为准，发送成功后更新该字段；可选并存 `PushNotificationHistory`（`push_type = "festival_memory"`，`stage = "festival"`）便于审计。点击通知进入该角色 Love Journal 页并定位到对应记忆条目。

## 消息生成

### Agent 消息生成

推送消息通过 Agent 生成，流程如下：

1. 获取 Agent 数据和实例
2. 获取用户信息（昵称等）
3. 构建提示词（使用 `build_simple_push_message_prompt()`）
4. 调用 `agent.chat()` 生成消息
5. 格式化消息内容（截取前100字符）

### 提示词模板

提示词模板位于 `app/core/prompting/push_message_prompt.py`，包含：

- 角色信息（名称、人设）
- 用户信息（昵称）
- 时间信息（距离上次聊天的时间）
- 主动发起对话的指令

示例提示词：

```
你是{agent_name}，向{user_name}主动发送一条简短、有趣的消息，
鼓励用户继续对话。消息应该符合你的性格特点，
考虑到距离上次聊天已经{time_since_last_message}了。
消息长度不超过50字。
```

## 配置

### 配置文件

推送服务配置位于 `config.yaml` 的 `push_notification` 部分：

```yaml
push_notification:
  enabled: false  # 是否启用推送服务
  batch_size: 50  # 每批处理的聊天数量
  max_retries: 3  # 最大重试次数
  intervals:
    10min: 10  # 10分钟推送
    30min: 30  # 30分钟推送
    2h: 120  # 2小时推送
```

### 配置项说明

- `enabled`: 是否启用推送服务（默认：`false`）
- `batch_size`: 每批处理的聊天数量（默认：`50`）
- `festival_memory_enabled`: 是否启用节日记忆通知推送（默认：`true`）
- `festival_memory_batch_size`: 节日记忆通知每批处理的 (user_id, agent_id) 数量（默认：`50`）
- `max_retries`: 最大重试次数（默认：`3`）
- `intervals`: 推送时间间隔配置（分钟）

## 部署

### 独立服务运行

推送服务可以作为独立进程运行：

```bash
python -m backend.push_worker.main
```

### 依赖要求

- Firebase Admin SDK 已初始化
- 数据库连接已配置
- AgentManager 已初始化
- APScheduler 已安装（`apscheduler==3.10.4`）

### 环境变量

推送服务使用与主应用相同的配置文件和环境变量。

## 数据库迁移

推送服务需要创建 `push_notification_history` 表，运行迁移：

```bash
alembic upgrade head
```

迁移文件：`backend/alembic/versions/20251111_140711_create_push_notification_history.py`

## 监控与日志

### 日志输出

推送服务会输出以下日志：

- 初始化日志：服务启动、Firebase 初始化、AgentManager 初始化
- 任务执行日志：每个推送阶段的处理结果（成功/失败数量）
- 错误日志：推送失败、消息生成失败等错误信息

### 日志级别

- `INFO`: 服务启动、任务执行结果
- `WARNING`: 推送失败、消息生成失败
- `ERROR`: 严重错误、异常堆栈

## 错误处理

### 重试机制

- 配置了 `max_retries` 参数，但当前版本未实现自动重试
- 失败的任务会记录日志，但不影响其他任务的执行

### 异常处理

- 单个聊天推送失败不影响其他聊天
- 单个阶段任务失败不影响其他阶段
- 所有异常都会记录详细日志

## 性能优化

### 批量处理

- 使用 `batch_size` 限制每批处理的聊天数量
- 避免一次性查询过多数据

### 查询优化

- 使用数据库索引加速查询（`chat_id`, `user_id`, `agent_id`, `sent_at`）
- 使用唯一约束避免重复检查

### 缓存

- Agent 数据通过 AgentManager 缓存
- 用户信息通过缓存服务缓存

## 限制与注意事项

### 当前限制

1. 推送消息长度限制为100字符（超出部分会被截断）
2. 每批处理的聊天数量有限制（默认50个）
3. 不支持自定义推送时间间隔（固定为10分钟、30分钟、2小时）

### 注意事项

1. 推送服务需要 Firebase 服务账号配置
2. 需要确保用户设备已注册 FCM token
3. 推送服务独立运行，不影响主应用
4. 建议在生产环境中使用进程管理器（如 systemd、supervisor）管理服务

## 未来改进

1. **重试机制**：实现自动重试失败的推送
2. **推送统计**：记录推送成功率、用户响应率等指标
3. **个性化策略**：根据用户行为调整推送时间间隔
4. **A/B 测试**：测试不同的推送策略效果
5. **推送模板**：支持多种推送消息模板
6. **用户偏好**：允许用户设置推送偏好（关闭推送、调整频率等）

## 相关文件

- `app/models/push_notification.py` - 推送历史模型
- `app/services/push_notification_service.py` - 推送服务核心逻辑
- `app/services/push_scheduler_service.py` - 定时任务调度
- `backend/push_worker/main.py` - 独立服务入口
- `app/core/prompting/push_message_prompt.py` - 提示词模板
- `backend/alembic/versions/20251111_140711_create_push_notification_history.py` - 数据库迁移

## 参考文档

- [Firebase Cloud Messaging](https://firebase.google.com/docs/cloud-messaging)
- [APScheduler 文档](https://apscheduler.readthedocs.io/)
- [Agent 系统文档](../docs/AGENTS.md)
- [通知服务文档](../../app/services/README.md)

