# 用户行为分析脚本测试指南

## 核心逻辑说明

### session_id 生成机制

根据 `app/services/chat_service.py`：

```python
def generate_session_id(chat_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))
```

**关键点**：

- `chats.id` 是字符串类型的 UUID
- `chat_history.session_id` 是 UUID 类型
- `session_id` = `uuid.uuid5(uuid.NAMESPACE_DNS, chats.id)`
- `uuid.NAMESPACE_DNS` = `'6ba7b810-9dad-11d1-80b4-00c04fd430c8'`

### 查询逻辑

1. **获取聊天会话**

   ```python
   # 从 chats 表获取 chat_id
   chat_ids = ["chat-id-1", "chat-id-2", ...]

   # 生成对应的 session_id
   session_ids = [generate_session_id(chat_id) for chat_id in chat_ids]

   # 查询 chat_history
   SELECT * FROM chat_history WHERE session_id::text IN (session_ids)
   ```

2. **消息关联**

   ```python
   # 建立 chat_id <-> session_id 映射
   chat_to_session = {chat_id: session_id}
   session_to_chat = {session_id: chat_id}

   # 查询后转换回 chat_id
   ```

## 测试步骤

### 1. 基础测试（Dry-Run）

```bash
cd experimental/user_analytics
python analyze_user_activity.py --last-days 3 --dry-run
```

**预期输出**：

- ✅ 显示新用户统计
- ✅ 显示活跃聊天用户数
- ✅ 显示 chat_history 表统计信息
- ✅ 显示找到的对话记录数量

### 2. 完整运行测试

```bash
python analyze_user_activity.py --last-days 3
```

**预期输出文件**：

- `reports/daily_new_users.csv`
- `reports/user_chat_activity.csv`
- `reports/user_sessions_detail.csv` ⭐ 包含 message_count 列
- `reports/popular_agents.csv`
- `reports/conversation_rounds_distribution.csv`
- `reports/conversations_detail.txt` ⭐ 包含完整对话内容
- `reports/user_analytics_report.html`

### 3. 验证关键数据

#### 验证 session_id 生成

```python
import uuid

chat_id = "5ec1f7b5-b5aa-4c76-a21b-69163fb57db0"
session_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))
print(f"Chat ID: {chat_id}")
print(f"Session ID: {session_id}")

# 可以在数据库中验证
# SELECT * FROM chat_history WHERE session_id::text = '{session_id}'
```

#### 验证数据库查询

```sql
-- 1. 查看 chats 表样本
SELECT id, user_id, agent_id, created_at
FROM chats
WHERE created_at >= NOW() - INTERVAL '3 days'
LIMIT 5;

-- 2. 查看 chat_history 表样本
SELECT session_id, COUNT(*) as message_count
FROM chat_history
GROUP BY session_id
LIMIT 5;

-- 3. 测试 session_id 生成和匹配
-- 假设 chat_id = 'abc-123'
-- Python: session_id = uuid.uuid5(uuid.NAMESPACE_DNS, 'abc-123')
SELECT *
FROM chat_history
WHERE session_id = '{生成的session_id}'::uuid;
```

## 常见问题

### Q1: "找到 0 个有对话记录的会话"

**可能原因**：

1. 时间范围内的 chats 确实没有消息
2. session_id 生成逻辑不正确

**调试方法**：

```bash
# 查看调试日志
python analyze_user_activity.py --last-days 3 2>&1 | grep -A 5 "chat_history 表统计"
```

### Q2: "未找到任何对话消息"

**可能原因**：

1. session_id 映射问题
2. 批量查询时的数据类型不匹配

**解决方法**：

- 检查脚本中的 `generate_session_id` 函数
- 确认与 `app/services/chat_service.py` 逻辑一致

### Q3: conversations_detail.txt 文件未生成

**可能原因**：

- 查询到的消息为空

**检查**：

```bash
# 查看日志中是否有 "找到 X 条对话消息"
# 如果是 0 条，说明查询有问题
```

## 性能优化建议

1. **限制时间范围**：分析大量数据时使用较短时间范围

   ```bash
   python analyze_user_activity.py --last-days 1
   ```

2. **批量大小**：脚本已内置批量查询（每批 500 个会话）

3. **输出目录**：使用独立目录避免覆盖
   ```bash
   python analyze_user_activity.py --last-days 7 --output-dir ./reports_weekly
   ```

## 数据示例

### user_sessions_detail.csv

```csv
user_id,auth_type,user_created_at,chat_id,agent_name,message_count
user-123,GUEST,2025-10-26 20:00:00,chat-456,Alice,25
user-123,GUEST,2025-10-26 20:00:00,chat-789,Bob,12
```

### conversations_detail.txt

```
================================================================================
用户ID: user-123
认证类型: GUEST
注册时间: 2025-10-26 20:00:00
Session 数量: 2
================================================================================

  Session 1:
  Chat ID: chat-456
  角色: Alice
  消息数: 25
  ----------------------------------------------------------------------------
  对话内容:
    [1] 用户 (2025-10-26 20:05:00):
        你好

    [2] AI (2025-10-26 20:05:02):
        你好！很高兴认识你...
```
