# FR_LIVE_CHAT_AUDIO_GCS - Live Chat 音频保存到 GCS

CREATED_BY_AGENT

## 功能概述

在开启「保存到聊天历史」的 live chat 会话中，将整段对话的音频按**单路、对话顺序**（用户–AI–用户–AI…）保存为一个 WAV 文件，先写入可配置的本地临时目录，再上传到 GCS，并在 `chat_history` 表中为当次会话的用户消息与 AI 消息记录同一 `audio_url` 和总时长。上传完成后删除本地临时文件。

## 存储形式

- **单文件**：每个会话对应一个 WAV 文件，内容为按时间顺序交织的用户与 AI 音频（用户 16k PCM 重采样为 24k 后与 AI 24k PCM 拼接）。
- **GCS 路径**：`live_chat/{user_id}/{agent_id}/{session_id}.wav`。
- **表记录**：当次会话产生的两条消息（一条用户、一条 AI）的 `audio_url` 字段均指向该 GCS URL；`meta_data.audioDuration` 为整段 WAV 的总时长（秒）。

## 流程简述

1. 会话进行中：在发送/接收路径按发生顺序累积 `("user", data)` / `("ai", data)` 到 `conversation_audio_chunks`（仅当 `config.save_history` 为 True）。
2. 会话结束：先按现有逻辑写转录并得到 `user_message_id`、`ai_message_id`；若有 `conversation_audio_chunks`，则按序拼接并重采样得到 24k PCM → 生成 WAV → 写入可配置本地目录 → 上传 GCS → 对两条消息各调用 `update_message_audio_url`（同一 `gcs_url`、同一 `total_duration`）→ 在 finally 中删除本地临时文件。

## 配置

- **gemini_live.audio_temp_dir**（可选）：live chat 音频落盘临时目录；未配置或为空时使用 `tempfile.gettempdir()`。

## 相关代码

- 音频缓冲与顺序：`app/services/live_chat_service.py`（`LiveSession.conversation_audio_chunks`，发送/接收路径 append）。
- 重采样与拼接：`app/utils/audio.py`（`resample_pcm_16k_to_24k`、`build_interleaved_pcm_24k`）。
- WAV 生成：复用 `app.core.voice.tts_api._pcm_to_wav`。
- 上传：`app/services/gcs_service.py`（`upload_live_chat_audio`）。
- 写表：`app/services/chat_history_service.update_message_audio_url`。
