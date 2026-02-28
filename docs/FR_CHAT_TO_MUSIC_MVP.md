# FR_CHAT_TO_MUSIC_MVP

## 背景

为 IntelliMate 增加「chat to music」能力：基于对话上下文，为指定 AI 回复生成一段背景音乐，并落库到现有消息结构中，供 Android 端复用已有音频播放链路。

## 本次 MVP 范围

### Backend

- 新增 API：`POST /api/v1/chat/music/{agent_id}`
- 新增请求/响应 schema：
  - `ChatMusicGenerationRequest`
  - `ChatMusicGenerationResponse`
- 新增服务：
  - `app/services/music_generation_service.py`
  - 当前 provider：`fal`（模型 ID 默认 `fal-ai/stable-audio`）
- 新增限额检查：
  - `SubscriptionService.check_music_gen_limit`
  - usage type：`music_generation`
- 消息写入：
  - `chat_history.audio_url` 写入生成音乐 URL
  - `chat_history.meta_data.generated_music` 写入生成元数据（prompt/model/时长等）

### Android API 类型同步

- 新增 `ChatMusicGenerationRequest/ApiResponse/Payload`
- `MsgMetaData` 新增 `generated_music` 结构
- `IChatApi` 新增 `generateMessageMusic()`

> 说明：本次为协议与后端能力先行，不包含 Android UI 卡片与交互闭环。

## API 草案（与本次实现一致）

### Request

`POST /api/v1/chat/music/{agent_id}`

```json
{
  "message_id": 123,
  "history_count": 10,
  "model": "fal-ai/stable-audio"
}
```

### Success Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "audio_url": "https://...",
    "audio_metadata": {
      "duration_sec": 21.5,
      "format": "mp3",
      "provider": "fal"
    },
    "prompt": "...",
    "message_id": 123,
    "model": "fal-ai/stable-audio",
    "generation_time_ms": 1840
  }
}
```

### Limit Response（示例）

```json
{
  "code": 10001001,
  "message": "Subscription required",
  "data": {
    "code": 10001001,
    "error_code": "SUBSCRIPTION_REQUIRED",
    "message": "Subscription required",
    "used_count": 2,
    "daily_limit": 2
  }
}
```

## generated_music 元数据结构

写入 `chat_history.meta_data.generated_music`：

```json
{
  "audio_url": "https://...",
  "prompt": "...",
  "model": "fal-ai/stable-audio",
  "generation_time_ms": 1840,
  "generated_at": "2026-02-28T00:00:00.000000",
  "duration_sec": 21.5,
  "format": "mp3",
  "provider": "fal"
}
```

## 后续建议

1. Android 侧补齐 Chat Item 音乐卡片（播放控制、加载态、失败态）。
2. 增加 provider 抽象层（fal / Vertex Lyria 2）并做订阅分层模型路由。
3. 增加观测面板：成功率、生成时长、平均片段时长、按模型成本统计。
