# 消息生图功能实现文档

## 概述

消息生图功能允许用户基于聊天上下文为 AI 回复生成图片。该功能使用 Gemini 2.5 Flash Image 模型，通过 Agent 的参考图（背景图或头像）和聊天上下文生成符合角色外观一致性的图片。

## 架构概览

```text
客户端请求 → API 验证（限额、权限） → 图片生成服务 → 用量记录 → 返回结果
                                              ↓
                      构建提示词 → Gemini API → 处理图片 → 上传GCS → 更新meta_data
```

## API 端点

### 生成聊天图片

**端点**: `POST /api/v1/chats/agents/{agent_id}/generate-image`

**请求参数**:

- `agent_id` (路径参数): Agent ID
- `message_id` (必填): 要生成图片的消息 ID（必须是最后一条 AI 回复）
- `history_count` (可选): 使用的历史消息数量，默认 10 条

**响应**:
```json
{
  "success": true,
  "data": {
    "message_id": 123,
    "image_url": "https://cdn.example.com/...",
    "image_metadata": {
      "width": 1024,
      "height": 1024,
      "format": "jpeg"
    },
    "prompt": "构建的提示词..."
  }
}
```

## 实现细节

### 1. API 端点实现

位置: `app/api/v1/endpoints/chats.py`

主要流程：

1. **验证 Agent 和用户**
   - 验证 Agent 是否存在
   - 获取或创建聊天会话
   - 验证 Agent ID 一致性

2. **检查图片生成限额**
   - 超级用户无限制
   - 游客用户不允许生成
   - 付费/免费用户检查 24 小时内的生成次数
   - 限额配置在 `app.limits.free_user_image_gen_24h_limit` 和 `app.limits.subscribed_user_image_gen_24h_limit`

3. **验证消息**
   - 确保只能对最后一条 AI 回复生成图片
   - 获取消息内容用于构建提示词

4. **调用图片生成服务**
   - 传入消息 ID、Agent 数据、消息内容、历史数量

5. **记录用量**
   - 使用 `subscription_service.record_usage()` 记录图片生成用量

### 2. 图片生成服务

位置: `app/services/image_generation_service.py`

核心类: `ImageGenerationService`

#### 2.1 提示词构建

`build_image_prompt()` 方法负责构建生图提示词：

- **输入**:
  - `agent_data`: Agent 数据（personality、scenario 等）
  - `chat_history`: 聊天历史记录列表
  - `user_message`: 触发消息的内容

- **处理**:
  - 提取 Agent 的 `scenario`（背景设定），若无则使用 `intro`
  - 提取 Agent 的 `personality`（性格）
  - 格式化聊天历史为文本（用户/AI 对话）
  - 使用配置的提示词模板进行变量替换

- **模板变量**:

  - `{agent_background}`: 角色背景设定
  - `{agent_personality}`: 角色性格
  - `{chat_history}`: 格式化的聊天历史
  - `{user_message}`: 用户消息内容

- **提示词模板**（默认）:

```text
保持图片中角色的外观完全一致（发型、脸型、服装风格、身材特征等），
但根据以下场景调整姿势、表情和背景：

角色性格：{agent_personality}
角色背景设定：{agent_background}

最近的对话：
{chat_history}

用户要求：{user_message}

请生成一张符合上述场景的图片，确保角色外观与参考图保持高度一致。
```

提示词模板可通过配置修改：`agent.image_generation_prompt_template`

#### 2.2 图片生成流程

`generate_chat_image_with_gemini()` 方法实现完整的图片生成流程：

1. **确定历史消息数量**
   - 使用请求中的 `history_count`，或默认值（`agent.image_generation_default_history_count`，默认 10）

2. **获取聊天历史**
   - 调用 `chat_history_service.get_messages_paginated()`（同步函数）获取最近 N 条消息

3. **构建提示词**
   - 调用 `build_image_prompt()` 生成完整提示词

4. **获取参考图**
   - 优先使用 Agent 的 `background`（背景图）
   - 若无背景图，使用 `avatar`（头像）
   - 将参考图 URL 转换为完整 HTTP URL（支持 `gs://` 到 HTTPS 的转换）

5. **调用 Gemini 2.5 Flash Image**
   - 使用 `google.genai` SDK
   - 模型：`gemini-2.5-flash-image`
   - 输入格式：
     - 参考图（`types.Part.from_uri()`）
     - 文字提示词（`types.Part.from_text()`）
   - 配置参数：
     - `temperature`: 1.0
     - `top_p`: 0.95
     - `max_output_tokens`: 8192
     - `response_modalities`: ["IMAGE"]
     - 安全设置：各种有害内容类别设置为 `BLOCK_MEDIUM_AND_ABOVE`

6. **提取图片数据**
   - 从响应中提取 `candidate.content.parts` 中的 `inline_data`
   - 处理 base64 解码（如果数据是字符串格式）
   - 验证数据格式（JPEG/PNG/GIF/WEBP）

7. **解析图片尺寸**
   - 使用 PIL 打开图片获取宽度、高度、格式

8. **上传到 GCS**
   - 生成唯一路径：`chat_images/{timestamp}_{uuid}.jpg`
   - 上传到配置的 GCS bucket
   - 获取公开 URL

9. **转换为 CDN URL**
   - 将 GCS URI 转换为 CDN URL（通过 `image_transform_service.transform_desktop()`）

10. **更新消息 meta_data**
    - 将图片信息存入消息的 `meta_data.generated_image` 字段：

      ```json
      {
        "image_url": "gs://bucket/path",
        "width": 1024,
        "height": 1024,
        "format": "jpeg",
        "prompt": "构建的提示词",
        "generated_at": "2024-01-01T00:00:00"
      }
      ```

    - 调用 `chat_history_service.update_message_metadata()` 更新

### 3. 消息元数据存储与检索

位置: `app/services/chat_history_service.py`

**更新方法**: `update_message_metadata()`
- 查询指定 `session_id` 和 `message_id` 的消息
- 合并现有的 `meta_data` 和新数据
- 更新数据库记录

**存储格式** (`meta_data.generated_image`):

- `image_url`: GCS URI（`gs://` 格式）
- `width`, `height`: 图片尺寸
- `format`: 图片格式（jpeg/png 等）
- `prompt`: 使用的提示词
- `generated_at`: 生成时间（ISO 格式）

**检索方法**: `get_messages_paginated()`

- 自动识别消息的 `meta_data.generated_image` 字段
- 将 GCS URI 转换为 CDN URL 后返回给客户端
- 返回的图片信息不包含 `prompt` 字段

### 4. 用量记录

位置: `app/services/subscription_service.py`

方法: `check_image_gen_limit()` 和 `record_usage()`

**限额检查**:

- 超级用户：无限制
- 游客用户：不允许
- 付费用户：检查 `subscribed_user_image_gen_24h_limit`
- 免费用户：检查 `free_user_image_gen_24h_limit`
- 统计过去 24 小时内的 `background_generation` 类型用量

**用量记录**:

- 类型：`image_generation`
- 数量：1
- 额外数据：`agent_id`、`message_content`（前 100 字符）

**注意**: 检查限额时查询的是 `background_generation` 类型，记录时使用的是 `image_generation`，存在不一致。

### 5. CDN URL 转换

位置: `app/services/image_transform_service.py`

方法: `transform_desktop()`

- 将 GCS URI（`gs://bucket/path`）转换为 Cloudflare CDN URL
- 格式：`https://{domain}/{bucket/path}`
- 如果 CDN 未启用或转换失败，回退到原始 URL

### 6. 配置项

位置: `app/core/config.py`

相关配置：

```python
# Agent 配置
agent:
  # 图片生成提示词模板
  image_generation_prompt_template: str = "保持图片中角色的外观..."
  
  # 默认历史消息数量
  image_generation_default_history_count: int = 10

# 应用限制配置
app:
  limits:
    # 免费用户 24 小时图片生成限制
    free_user_image_gen_24h_limit: int
    
    # 付费用户 24 小时图片生成限制
    subscribed_user_image_gen_24h_limit: int

# GCS 配置
gcs:
  bucket: str  # GCS bucket 名称

# Cloudflare CDN 配置
cloudflare:
  enabled: bool  # 是否启用 CDN
  domain: str    # CDN 域名
```

## 关键特性

1. **角色外观一致性**: 通过 Agent 参考图（背景图或头像）确保生成图片中角色外观与参考图一致，同时根据聊天上下文调整姿势、表情和背景。

2. **上下文感知**: 提示词包含 Agent 性格/背景设定、最近 N 条聊天历史、触发消息内容，生成符合当前对话场景的图片。

3. **安全过滤**: Gemini API 安全设置对所有有害内容类别设置为 `BLOCK_MEDIUM_AND_ABOVE`。

4. **限额管理**: 按用户类型设置 24 小时限额，实时统计检查。

5. **存储策略**: 图片上传到 GCS 存储为 `gs://` URI，通过 CDN 加速访问，图片信息存储在消息 `meta_data` 中。

6. **重复生成**: 重复生成会直接覆盖 `meta_data.generated_image` 字段。

## 错误处理

1. **Agent 不存在**: 返回 404
2. **消息不存在**: 返回 404
3. **不是最后一条 AI 回复**: 返回 400
4. **达到生成限额**: 返回业务错误码（`IMAGE_GENERATION_LIMIT_REACHED` 或 `GUEST_LOGIN_REQUIRED`）
5. **Agent 没有参考图**: 抛出 `ValueError`
6. **Gemini API 错误**: 记录错误并抛出异常
7. **图片解析失败**: 记录错误并抛出异常

## 相关文件

- `app/api/v1/endpoints/chats.py`: API 端点实现
- `app/services/image_generation_service.py`: 图片生成服务核心逻辑
- `app/services/chat_history_service.py`: 消息历史服务（获取历史、更新元数据）
- `app/services/subscription_service.py`: 订阅和用量服务
- `app/services/image_transform_service.py`: CDN URL 转换服务
- `app/utils/gemini.py`: Gemini 客户端封装
- `app/external_services/gcs.py`: GCS 上传工具
- `app/schemas/chat.py`: 请求/响应模型定义
- `app/core/config.py`: 配置项定义

## 注意事项

1. **消息限制**: 只能对最后一条 AI 回复生成图片
2. **历史数量**: 默认 10 条，可通过 `history_count` 参数调整
3. **参考图要求**: Agent 必须至少有背景图或头像
4. **图片格式**: 统一为 JPEG，存储路径 `chat_images/{timestamp}_{uuid}.jpg`
5. **用量类型不一致**: 检查限额使用 `background_generation`，记录使用 `image_generation`

## 未来改进

1. 统一用量类型命名
2. 支持生成多张图片和自定义尺寸/比例
3. 异步生成和失败重试机制
