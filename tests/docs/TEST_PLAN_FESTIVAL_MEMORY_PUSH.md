# 节日记忆 System 推送 - 测试计划

## 概述

本测试计划覆盖 Push Worker「节日记忆通知」功能：定时扫描存在未投递且未发过 system notification 的节日记忆 (user_id, agent_id)，向用户发送 FCM 推送；用户点击后进入该角色 Love Journal 页并定位到对应记忆条目。

## 单元测试

### memory_service

- **get_pairs_with_undelivered_festival_memories**
  - 在给定 Memory 数据（含 `system_notification_sent_at`）下，返回预期 (user_id, agent_id) 列表。
  - 仅包含 `memory_type == "festival"`、`delivery_at IS NULL`、`system_notification_sent_at IS NULL` 的 (user_id, agent_id)。
  - 每个返回元素**必须**包含 `festival_memory_id`（该对中一条代表 memory id，如按 festival_date 升序第一条）。
  - 去重、limit 生效；无符合条件数据时返回空列表。

- **mark_system_notification_sent_for_user_agent**
  - 对该 (user_id, agent_id) 下所有 `memory_type == "festival"` 且 `delivery_at IS NULL` 的行更新 `system_notification_sent_at = now()`。
  - 验证更新行数/影响范围正确；不影响已投递或非 festival 行。

### push_notification_service

- **has_sent_festival_push_for_user_agent**
  - 当 PushNotificationHistory 中已存在 (user_id, agent_id, push_type=PUSH_TYPE_FESTIVAL_MEMORY) 时返回 True。
  - 当不存在时返回 False。

## 集成测试

- **process_festival_memory_push_batch**
  - Mock FCM 或使用测试 token，跑一次 `process_festival_memory_push_batch`。
  - 断言：`record_push_history` 被调用（push_type=festival_memory, stage=festival）。
  - 断言：memory 表中对应行的 `system_notification_sent_at` 被更新。
  - 断言：payload 含 `type=festival_memory` **且含 `festival_memory_id`**（当该对有未投递记忆时）。
  - 无 device_token 或已发过（system_notification_sent_at 非空）的用户不发送、不更新。

## E2E（可选）

- 本地 push worker 开启，插入未投递 festival memory（delivery_at IS NULL, system_notification_sent_at IS NULL）。
- 等待调度或手动触发一次「节日记忆通知」任务。
- 确认收到 FCM 推送，点击后进入该角色 **Love Journal 对应记忆条目**。
- 前置条件：config 启用、数据库迁移已跑、push worker 与后端共用 DB；断言要点：推送内容、跳转目标页与条目。

## Android 端测改动

- **通知展示**：收到 payload 含 `type: "festival_memory"`、`agent_id`（及可选 `festival_memory_id`）的推送时，通知栏展示服务端下发的 title/body。
- **点击跳转（前台/后台）**：点击后跳转到该角色的 Love Journal 页面并定位到对应记忆条目；若带 `festival_memory_id` 则打开该条详情或滚动到该条，若无则仅打开该角色 Love Journal 列表。
- **冷启动**：从该通知点击冷启动，MainActivity 根据 TYPE_FESTIVAL_MEMORY、agent_id、festival_memory_id 打开 Love Journal 页并定位到对应记忆条目。
- **边界**：缺少 `agent_id` 时与现有未知 type 处理一致（如跳转主页面），不崩溃；缺少 `festival_memory_id` 时仅打开该角色 Love Journal 列表。

**通过标准**：上述用例手测或 Instrumentation 通过，且测试计划文档中用例与标准一致。
