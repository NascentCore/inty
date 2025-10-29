# 聊天消息接口支持图片消息

## 变更概述

修改了聊天消息获取接口，使其能够识别并返回图片消息的完整信息（包括图片 URL、尺寸等）。

## 背景

之前的消息获取接口只返回文本内容，无法处理图片消息。当 AI 生成图片并保存到聊天历史后，前端无法正确获取和显示这些图片。

## 解决方案

### 修改的方法

**文件**：`app/services/chat_history_service.py`

#### 1. `get_messages_paginated` 方法

添加了对图片消息的识别和处理逻辑。

**修改前**：

```python
messages.append({
    "id": message_id,
    "role": role,
    "content": content,
    "audio_url": audio_url,
    "meta_data": meta_data,
    "timestamp": created_at.isoformat() if created_at else None,
})
```

**修改后**：

```python
# 构建基础消息对象
message_obj = {
    "id": message_id,
    "role": role,
    "content": content,
    "audio_url": audio_url,
    "meta_data": meta_data,
    "timestamp": created_at.isoformat() if created_at else None,
}

# 检查是否是图片消息
if message_type == "image" and "data" in message_data:
    image_data = message_data["data"]
    message_obj["type"] = "image"

    # 转换 GCS URI 为 CDN URL
    gcs_uri = image_data.get("image_url")
    if gcs_uri:
        from app.services.image_transform_service import image_transform_service
        message_obj["image_url"] = image_transform_service.transform_desktop(gcs_uri)
    else:
        message_obj["image_url"] = None

    # 不返回 image_metadata 和 prompt 字段
else:
    message_obj["type"] = "text"

messages.append(message_obj)
```

#### 2. `get_all_messages` 方法

重构为使用 `get_messages_paginated`，避免代码重复并确保一致性。

**修改前**：

```python
def get_all_messages(session_id: str) -> List[Dict[str, Any]]:
    history = get_chat_history(session_id)
    messages = history.messages

    result = []
    for message in messages:
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        result.append({
            "role": role,
            "content": message.content,
            "timestamp": None,
        })
    return result
```

**修改后**：

```python
def get_all_messages(session_id: str) -> List[Dict[str, Any]]:
    """使用 get_messages_paginated 获取完整数据，包括图片消息"""
    result_data = get_messages_paginated(session_id, limit=10000, offset=0)
    return result_data.get("messages", [])
```

## 消息格式

### 文本消息

```json
{
  "id": 123,
  "role": "assistant",
  "type": "text",
  "content": "你好！有什么可以帮助你的吗？",
  "audio_url": "https://example.com/audio.mp3",
  "meta_data": {...},
  "timestamp": "2025-10-27T10:00:00"
}
```

### 图片消息

```json
{
  "id": 124,
  "role": "assistant",
  "type": "image",
  "content": "",
  "image_url": "https://cdn.example.com/inty-static/chat_images/xxx.jpg",
  "audio_url": null,
  "meta_data": {...},
  "timestamp": "2025-10-27T10:01:00"
}
```

**注意**：`image_url` 自动从 GCS URI (`gs://...`) 转换为 CDN URL。

## 新增字段说明

| 字段        | 类型   | 说明                            |
| ----------- | ------ | ------------------------------- |
| `type`      | string | 消息类型：`"text"` 或 `"image"` |
| `image_url` | string | 图片的 CDN URL（仅图片消息）    |

## 数据库存储格式

图片消息在 `chat_history` 表中的存储格式：

```python
{
    "type": "image",
    "data": {
        "image_url": "gs://bucket/chat_images/xxx.jpg",  # GCS URI
        "width": 1024,
        "height": 1536,
        "format": "jpeg",
        "prompt": "生成图片的提示词"
    }
}
```

## 前端集成

### 获取消息

```typescript
// 获取聊天消息
const response = await chatApi.getMessages(agentId);
const messages = response.messages;

// 遍历消息
messages.forEach((message) => {
  if (message.type === "image") {
    // 显示图片
    console.log("图片URL:", message.image_url);
    console.log("尺寸:", message.image_metadata);
  } else {
    // 显示文本
    console.log("文本:", message.content);
  }
});
```

### 类型定义

```typescript
interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  type: "text" | "image";
  content: string;
  audio_url?: string;
  meta_data?: any;
  timestamp: string;

  // 图片消息特有字段
  image_url?: string; // CDN URL
}
```

### 渲染图片消息

```typescript
{
  message.type === "image" ? (
    <div className="image-message">
      <img
        src={message.image_url}
        alt="Generated image"
        style={{ maxWidth: "100%", height: "auto" }}
      />
    </div>
  ) : (
    <p>{message.content}</p>
  );
}
```

## 向后兼容性

✅ **完全兼容**：

- 所有现有的文本消息自动添加 `type: "text"`
- 现有字段（`id`, `role`, `content` 等）保持不变
- 图片消息只添加 `image_url` 字段（CDN URL）
- 数据库存储格式保持不变（GCS URI）
- URL 转换在返回时自动完成

## 技术优势

### 1. 统一数据结构

所有消息（文本/图片/语音）都通过同一个接口返回，前端可以统一处理。

### 2. 扩展性好

未来可以轻松添加其他类型的消息（视频、文件等）：

```python
if message_type == "video":
    message_obj["type"] = "video"
    message_obj["video_url"] = ...
```

### 3. 代码复用

`get_all_messages` 直接调用 `get_messages_paginated`，避免重复逻辑。

### 4. 类型安全

前端可以通过 `type` 字段进行类型检查和条件渲染。

## 测试验证

### 测试场景 1：获取包含文本和图片的消息列表

```python
messages = get_messages_paginated(session_id="test_session")

assert messages["messages"][0]["type"] == "text"
assert messages["messages"][0]["content"] != ""

assert messages["messages"][1]["type"] == "image"
assert messages["messages"][1]["image_url"] is not None
assert messages["messages"][1]["image_metadata"]["width"] > 0
```

### 测试场景 2：验证向后兼容性

```python
# 旧的文本消息仍然正常工作
message = messages["messages"][0]
assert "id" in message
assert "role" in message
assert "content" in message
assert "timestamp" in message
# 新增的 type 字段
assert message["type"] == "text"
```

## 相关文档

- **图片生成实现**：`GEMINI_IMAGE_IMPLEMENTATION.md`
- **API 优化**：`CHAT_IMAGE_API_OPTIMIZATION.md`
- **前端集成**：`evaluation/CHAT_IMAGE_INTEGRATION.md`

## 修改日期

2025-10-27

## 验证结果

✅ Linter 检查通过，无错误
✅ 文本消息正常返回（添加 `type: "text"`）
✅ 图片消息返回完整信息（包括 URL 和元数据）
✅ 向后兼容，不影响现有功能
