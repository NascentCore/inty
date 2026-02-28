# TEST_STEPS_CHAT_TO_MUSIC_MVP

## 目标

验证 chat-to-music MVP 后端能力：

1. endpoint 能返回统一 APIResponse
2. 业务限额错误能被正确包装
3. service 成功路径会写入 `audio_url` 与 `meta_data.generated_music`

## 自动化测试命令（本次执行）

1. `pytest tests/app/services/test_chat_service.py -k "generate_chat_music" -v -s`
2. `pytest tests/app/api/v1/endpoints/test_chat.py -k "generate_music" -v -s`

## 关键断言

- `ChatMusicGenerationResponse` 字段完整：`audio_url/audio_metadata/prompt/model`
- `SubscriptionService.record_usage(..., "music_generation", ...)` 被调用
- `chat_history.audio_url` 更新为生成音乐 URL
- `chat_history.meta_data.generated_music` 包含 `audio_url/model`
