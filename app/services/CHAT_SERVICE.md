# Chat Service 文档

> CREATED_BY_AGENT

本文档说明 `chat_service.py` 中的核心概念和实现细节，特别是 Session ID 的定义、生成方式以及在聊天服务中的作用。

## 目录

- [Session ID 概述](#session-id-概述)
- [Session ID 生成](#session-id-生成)
- [Session ID 的作用](#session-id-的作用)
- [get_or_create_chat_by_agent 函数](#get_or_create_chat_by_agent-函数)
- [数据关系](#数据关系)

## Session ID 概述

`session_id` 是聊天会话的唯一标识符，用于在 `chat_history` 表中存储和检索消息。它是连接 `Chat` 表和 `chat_history` 表的关键桥梁。

### 核心特点

- **确定性生成**：同一个 `chat_id` 总是生成相同的 `session_id`
- **唯一性**：不同的 `chat_id` 对应不同的 `session_id`
- **一致性保证**：确保创建聊天和发送消息时使用相同的 `session_id`

## Session ID 生成

### 生成函数

```python
def generate_session_id(chat_id: str) -> str:
    """
    Generate consistent session_id based on chat_id
    Ensure the same session_id is used when creating chat and chatting
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chat_id))
```

### 生成原理

- 使用 **UUID5** 算法基于 `chat_id` 生成
- 使用 `uuid.NAMESPACE_DNS` 作为命名空间
- 确保相同输入总是产生相同输出（确定性哈希）

### 使用示例

```python
# 从 chat_id 生成 session_id
chat_id = "abc123-def456-ghi789"
session_id = generate_session_id(chat_id)
# session_id 将是一个基于 chat_id 的确定性 UUID5 值
```

## Session ID 的作用

### 1. 消息存储

所有聊天消息都通过 `session_id` 存储在 `chat_history` 表中：

```python
# 添加用户消息
chat_history_service.add_user_message(session_id, message)

# 添加 AI 消息
await chat_history_service.add_ai_message(
    db, session_id, message, agent_id=agent_id
)
```

### 2. 消息检索

通过 `session_id` 查询特定会话的所有消息：

```python
# 分页获取消息
messages_data = chat_history_service.get_messages_paginated(
    session_id=session_id, limit=20, offset=0
)

# 获取最后一条消息
last_message_data = chat_history_service.get_last_message_with_timestamp(session_id)
```

### 3. 会话隔离

不同的 `chat_id` 对应不同的 `session_id`，实现会话之间的完全隔离。

### 4. 一致性保证

通过确定性生成，确保同一 `chat_id` 在整个应用生命周期中始终使用相同的 `session_id`。

## get_or_create_chat_by_agent 函数

### 函数签名

```python
async def get_or_create_chat_by_agent(
    db: AsyncSession, user_id: str, agent_id: str
) -> models.Chat:
    """
    根据用户ID和Agent ID获取或创建唯一的聊天会话（高性能优化版）
    每个用户和每个Agent只能有一个会话
    """
```

### 工作流程

#### 1. 缓存检查

首先检查会话缓存，如果存在则直接返回：

```python
session_key = f"{user_id}:{agent_id}"
cached_session = cache_service.get_session_info(session_key)
if cached_session:
    # 从缓存构建 Chat 对象并返回
    return chat
```

#### 2. 数据库查询

如果缓存未命中，查询数据库中是否已存在会话：

```python
result = await db.execute(
    select(models.Chat).where(
        models.Chat.user_id == user_id,
        models.Chat.agent_id == agent_id,
        models.Chat.is_active == True,
    )
)
existing_chat = result.scalar_one_or_none()
```

#### 3. 处理已存在的会话

如果找到已存在的会话：

- **验证 Agent ID 一致性**：确保数据库中的 `agent_id` 与传入参数一致
- **加载 Agent 信息**：从缓存或数据库获取 Agent 的详细信息
- **检查并添加开场白**：如果会话为空，自动添加 Agent 的开场白消息
- **缓存会话信息**：将会话信息写入缓存以便后续快速访问

```python
if existing_chat:
    # 验证 agent_id 一致性
    if existing_chat.agent_id != agent_id:
        raise HTTPException(...)
    
    # 生成 session_id 并检查消息
    session_id = generate_session_id(existing_chat.id)
    existing_messages = chat_history_service.get_messages_paginated(
        session_id=session_id, limit=1, offset=0
    )
    
    # 如果会话为空，添加 Agent 开场白
    if existing_messages.get("total", 0) == 0:
        await chat_history_service.add_agent_opening_message(...)
```

#### 4. 创建新会话

如果不存在，创建新的聊天会话：

- **验证 Agent 存在**：确保 `agent_id` 对应的 Agent 存在
- **创建 Chat 记录**：在数据库中创建新的 `Chat` 记录
- **生成 session_id**：为新创建的 `chat_id` 生成对应的 `session_id`
- **添加开场白**：如果 Agent 有开场白，自动添加到聊天历史
- **缓存会话信息**：将新会话信息写入缓存

```python
# 创建新的聊天会话
chat_id = str(uuid.uuid4())
db_chat = models.Chat(id=chat_id, user_id=user_id, agent_id=agent_id)
db.add(db_chat)
await db.commit()

# 生成 session_id 并添加开场白
if agent_opening:
    session_id = generate_session_id(chat_id)
    await chat_history_service.add_agent_opening_message(
        db, session_id, agent_opening, ...
    )
```

### 性能优化

1. **缓存优先**：优先从缓存获取会话信息，减少数据库查询
2. **延迟加载**：跳过耗时的消息查询，仅在需要时单独查询
3. **并发处理**：使用异步操作处理 Agent 信息加载和开场白添加
4. **错误重试**：处理并发创建冲突，自动重试查询

### 错误处理

- **IntegrityError**：处理并发创建导致的重复，自动重试查询
- **SQLAlchemyError**：数据库操作错误，回滚并抛出 HTTPException
- **HTTPException**：直接向上抛出，由调用方处理

## 数据关系

### 表关系图

```
Chat (数据库表)
  ├─ id (chat_id) - UUID4
  ├─ user_id
  ├─ agent_id
  └─ is_active
  
  └─ generate_session_id(chat_id)
      └─ session_id (UUID5) - 确定性哈希值
          └─ chat_history (数据库表)
              ├─ session_id (外键)
              ├─ message (JSON)
              ├─ meta_data (JSON)
              ├─ audio_url
              └─ created_at
```

### 关键映射

| 概念 | 类型 | 说明 |
|------|------|------|
| `chat_id` | UUID4 | Chat 表的主键，随机生成 |
| `session_id` | UUID5 | 基于 `chat_id` 的确定性哈希值 |
| `user_id` | String | 用户标识 |
| `agent_id` | String | Agent 标识 |

### 使用场景

1. **创建聊天时**：
   ```python
   chat = await get_or_create_chat_by_agent(db, user_id, agent_id)
   session_id = generate_session_id(chat.id)
   ```

2. **发送消息时**：
   ```python
   chat = await get_or_create_chat_by_agent(db, user_id, agent_id)
   session_id = generate_session_id(chat.id)
   await chat_history_service.add_user_message(session_id, message)
   ```

3. **查询消息时**：
   ```python
   chat = await get_chat(db, chat_id)
   session_id = generate_session_id(chat.id)
   messages = chat_history_service.get_messages_paginated(session_id, ...)
   ```

## 注意事项

1. **一致性要求**：确保在整个应用中使用 `generate_session_id()` 函数生成 `session_id`，不要手动构造
   - 该函数在 `chat_service.py` 和 `user_analytics_service.py` 中都有定义，实现完全一致
   - 使用 UUID5 确保相同 `chat_id` 总是生成相同的 `session_id`

2. **缓存失效**：当 Chat 或 Agent 信息更新时，需要清除相关缓存
   - 缓存键格式：`f"{user_id}:{agent_id}"`
   - 缓存包含：chat_id、agent 信息、时间戳等

3. **并发安全**：`get_or_create_chat_by_agent` 函数已处理并发创建的情况
   - 通过 `IntegrityError` 捕获并发冲突
   - 自动重试查询已存在的会话

4. **性能考虑**：
   - 大量使用缓存减少数据库查询
   - 在高并发场景下需要注意缓存一致性
   - 延迟加载消息查询，仅在需要时单独查询

5. **唯一性约束**：每个用户和每个 Agent 只能有一个活跃会话（`is_active=True`）

## 相关文件

- `app/services/chat_service.py` - 聊天服务主文件
- `app/services/chat_history_service.py` - 聊天历史服务
- `app/services/cache_service.py` - 缓存服务
- `app/services/user_analytics_service.py` - 用户分析服务（也包含 `generate_session_id` 函数）
- `app/models/chat.py` - Chat 数据模型
- `app/models/chat_history.py` - ChatHistory 数据模型

## 其他重要函数

### get_chat

根据 `chat_id` 获取聊天会话，并加载最后一条消息：

```python
async def get_chat(db: AsyncSession, chat_id: str) -> Optional[models.Chat]:
    """
    Get chat by ID
    """
    # 使用 session_id 查询最后一条消息
    session_id = generate_session_id(chat.id)
    last_message_data = chat_history_service.get_last_message_with_timestamp(session_id)
```

### generate_chat_image

基于聊天上下文生成图片，也使用 `session_id` 来获取历史消息：

```python
async def generate_chat_image(
    db: AsyncSession,
    agent_id: str,
    user_id: str,
    message_id: int,
    history_count: Optional[int] = None,
) -> Union[schemas.ChatImageGenerationResponse, UsageLimitExceeded, BizError]:
    """
    基于聊天上下文生成图片（公共函数）
    """
    chat = await get_or_create_chat_by_agent(db=db, user_id=user_id, agent_id=agent_id)
    session_id = generate_session_id(chat.id)
    # 使用 session_id 获取历史消息用于图片生成
```

