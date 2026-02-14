# 节日记忆推送 - 测试数据插入步骤（本地 / dev）

## 用途

向 `memory` 表插入一条「未投递且未发过 system notification」的节日记忆，用于本地或 dev 环境验证 Push Worker 节日记忆通知：定时任务会扫描到该 (user_id, agent_id)，向该用户发送 FCM，点击后进入该角色 Love Journal。

## 前置条件

- 已执行迁移：`alembic upgrade head`（含 `system_notification_sent_at` 列）。
- **user_id**、**agent_id** 在目标库中必须存在（`users.id`、`agents.id`）；dev 若不同，请替换下面 SQL 中的两个占位值。
- 该用户已在 App 中登录并上报过 device_token（否则 Push Worker 会跳过「无 device_token」）。

## SQL（可直接在本地或 dev 执行）

```sql
-- 插入一条未投递、未发 system 推送的节日记忆，供节日记忆通知任务扫描
-- 请将 user_id / agent_id 替换为当前环境存在的用户 ID、角色 ID（dev 需用 dev 库中的值）
INSERT INTO memory (
    user_id,
    memory_type,
    agent_id,
    content,
    extracted_at,
    created_at,
    festival_name,
    festival_date,
    delivery_at
) VALUES (
    'user-01K99ASZ756T3XWC9VB0H4GGP8',   -- user_id，dev 请改为 dev 用户 ID
    'festival',
    '5679ca3b-b8f6-4253-a263-ed2714bc86df',  -- agent_id，dev 请改为 dev 中存在的角色 ID
    'Test festival memory for push.',
    NOW(),
    NOW(),
    NULL,
    NULL,
    NULL
);
-- delivery_at、system_notification_sent_at 均为 NULL，满足「未投递且未发过 system 推送」条件
```

## 执行方式

### 本地

```bash
# 使用与后端相同的 config（如 config.yaml 指向本地 DB）
psql -h <host> -U <user> -d <database> -f - <<'SQL'
INSERT INTO memory (
    user_id,
    memory_type,
    agent_id,
    content,
    extracted_at,
    created_at,
    festival_name,
    festival_date,
    delivery_at
) VALUES (
    'user-01K99ASZ756T3XWC9VB0H4GGP8',
    'festival',
    '5679ca3b-b8f6-4253-a263-ed2714bc86df',
    'Test festival memory for push.',
    NOW(),
    NOW(),
    NULL,
    NULL,
    NULL
);
SQL
```

### Dev 数据库

- 将上述 `INSERT` 中的 `user_id`、`agent_id` 替换为 dev 库中已有的用户 ID 和角色 ID。
- 在 dev 数据库上执行（通过 psql、DBeaver、或运维提供的 SQL 执行入口）。

## 验证

- 启动 Push Worker（或等待 15 分钟定时任务），日志中应出现 `[节日记忆通知] 开始...` 及该 (user_id, agent_id) 的发送记录。
- 对应用户在设备上应收到一条「Heartbeat Journal」推送，点击后进入该角色 Love Journal 页。
