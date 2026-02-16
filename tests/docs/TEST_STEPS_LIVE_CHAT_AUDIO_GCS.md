# Live Chat 音频保存到 GCS - 测试步骤

本文描述对「Live Chat 音频保存到 GCS」功能（见 `docs/FR_LIVE_CHAT_AUDIO_GCS.md`）的测试方法。

## 1. 单元测试

### 1.1 音频工具（必跑）

```bash
pytest tests/app/utils/test_audio.py -v
```

覆盖：`resample_pcm_16k_to_24k`（空输入、奇数长度、2:3 比例、较多采样）、`build_interleaved_pcm_24k`（空列表、仅 user 16k/24k、仅 ai、交织）。

### 1.2 其他相关单测（回归）

```bash
pytest tests/app/services/test_live_chat_service.py -v
pytest tests/app/utils/test_gcs.py -v
pytest tests/app/services/test_gcs_service.py -v
```

其中 `test_gcs_service.py` 包含 `upload_live_chat_audio` 的 mock 测试及按返回 URL 用 FakeGCS 下载校验的端到端测试（`test_upload_live_chat_audio_e2e_download_by_url`）。

## 2. 集成 / 人工测试（端到端）

验证「真实会话 → 写库 + 落 GCS + 临时文件删除」需在真实或测试环境执行。

### 2.1 环境

- 后端运行（本地或测试环境），配置中开启 live chat 且 `save_voice_history` 为 true；可选配置 `gemini_live.audio_temp_dir`。
- GCS 使用测试 bucket 或可写 bucket。

### 2.2 操作

1. 使用评测平台或 Android 客户端，创建 live chat 会话并开启「保存到聊天历史」。
2. 进行多轮对话（用户说几句、AI 回复几轮）。
3. 正常结束会话（挂断/结束通话）。

### 2.3 校验

- **聊天历史**：该会话在聊天历史中有两条消息（一条用户、一条 AI），且均带有 `audio_url`，指向 `live_chat/{user_id}/{agent_id}/{session_id}_{voice_session_id}.wav` 的 GCS URL。
- **GCS**：在对应 bucket 下存在上述路径的 `.wav` 文件，可下载播放确认为按时间顺序交织的用户与 AI 单路音频。
- **时长**：两条消息的 `meta_data.audioDuration` 一致，为整段 WAV 的总时长（秒）。
- **临时文件**：若配置了 `audio_temp_dir`，会话结束后该目录下不应残留 `live_chat_*.wav`（已在 finally 中删除）。

## 3. 可选补充

- 对 `_save_conversation_history` 的音频分支做单测时，可 mock `GCSService.upload_live_chat_audio`、`chat_history_service.update_message_audio_url`、`build_interleaved_pcm_24k` 等，构造带 `conversation_audio_chunks` 的 `LiveSession` 与 `db`，调用 `_save_conversation_history` 并断言依赖的调用与参数。

## 4. 相关文档

- 功能说明：`docs/FR_LIVE_CHAT_AUDIO_GCS.md`
- 评测与 Android 对比：`docs/LIVE_CHAT_EVALUATION_ANDROID.md`
