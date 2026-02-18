# Users API 端点文档

本文档对应 `users.py` 中的端点及与用户、推送相关的后端行为摘要。

---

## FCM Token 如何被记录

- **入口**：`POST /api/v1/users/device/register`（需登录）。
- **请求体**：`DeviceTokenRegister`：`token`（必填，FCM 设备 token）、`request_id`（可选，不落库）。
- **流程**：Handler 取 `device_in.token` 与 `current_user.id`，调用 `user_service.register_device_token(db, token, user_id)`。
- **持久化**（`user_service.register_device_token`）：
  1. 按 `token` 在 `device_tokens` 表中查询。
  2. 若存在：更新该行的 `user_id`（及 `updated_at`）；若不存在：插入新行 `DeviceToken(token=token, user_id=user_id)`。
  3. 若该用户曾被打标为 FCM 无效，则清除：`users.fcm_token_invalid_at = NULL`。
  4. `commit`。
- **存储位置**：表 `device_tokens`（`token` 唯一、`user_id`、`created_at`、`updated_at`）。这是后端记录 FCM token 的唯一路径。

---

## 应用版本代码如何被记录

- **入口**：`POST /api/v1/version/check`（实现于 `version.py`）。
- **行为**：客户端通过 Header `appVersionCode` 上报 Android 应用版本代码；后端将其写入 `users.last_android_app_version_code`，供 **push worker 做 feature gating**（例如按版本决定是否发送或如何构造某类 push）。字段命名仅针对 Android，因后端未来可能服务 iOS。

---

## 节日记忆系统通知（Festival Memory System Notification）

- **发送方**：**Push worker**（`backend/push_worker`），不是 inty 主后端 API 服务。Push worker 启动时调用 `push_scheduler_service.start()`，调度器内注册“节日记忆通知”任务。
- **是否按版本号门控**：**否**。节日记忆的 **系统 push（FCM）** 当前不按 app version code 过滤；只要用户有待推送的节日记忆且满足下文条件就会发。按版本门控的是 **应用内投递**（GET messages、chat completions、agent detail 等），使用 `min_app_version_code_for_festival_memory` 与 `is_festival_memory_enabled(app_version_code)`。
- **何时发送**：每 15 分钟执行一次 + 调度器启动时执行一次；且需 `push_notification.enabled` 与 `push_notification.festival_memory_enabled`（默认 true）为真。
- **对单次发送的条件**（对每个 (user_id, agent_id)）：
  - 存在未投递且未发过 system notification 的节日记忆（`memory_type == festival`，`delivery_at` 与 `system_notification_sent_at` 均为 NULL）；
  - 用户有有效 device token（见下）；
  - 尚未对该 (user_id, agent_id) 发过节日记忆 push（无对应 `PushNotificationHistory`）；
  - Agent 存在；
  - FCM 发送成功。
  - 每批最多处理 `festival_memory_batch_size`（默认 50）对。

---

## 有效 Device Token 的判定（push 侧）

- **实现**：`push_notification_service._check_user_has_device_token(db, user_id)`。
- **逻辑**：  
  1. 查 `users.fcm_token_invalid_at`；若非 NULL，视为该用户 FCM 无效，返回 False。  
  2. 查 `device_tokens` 中是否存在该 `user_id` 的任意一行（按 `updated_at` 降序取一条即可）；存在则返回 True，否则 False。
- **与版本号**：该函数本身不读、不写 app version。若要支持“按记录的应用版本做 push 门控”，可在现有数据上扩展：例如在 `device_tokens` 或 `users` 上增加版本字段，在 token 注册或 version/check 时写入；push 逻辑在判断“有 token”之后，再根据该版本与 `min_app_version_code_for_*` 等决定是否发送或如何构造推送。
