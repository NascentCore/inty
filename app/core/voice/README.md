# voice - 语音模块

## Cursor Summary

- 目录用途: 与语音/TTS 相关的核心模型与适配。
- 关键文件: `model.py` 定义语音相关的数据结构/枚举，供服务/接口层复用。
- 关键文件: `tts_api.py` 提供 TTS wrapper API（Gemini TTS 优先，失败回退 ElevenLabs），供 `VoiceService` 等上层服务调用。`voice_id` 支持带 provider 前缀（`google/xxx`、`11labs/xxx`），详见 [FR_VOICE_ID_PROVIDER_PREFIX](../../docs/FR_VOICE_ID_PROVIDER_PREFIX.md）。
  - 当配置 `tts.use_gemini_prompted_tts=true` 时，Gemini 使用 `synthesize_with_roleplay_prompt`（角色扮演指令 + 原文，括号内为舞台说明不朗读）；否则使用 `synthesize`（仅朗读原文）。前者不做文本清理，保留括号内容供语气参考。
- 关联: `app/services/voice_service.py`、`app/services/voice_cache_service.py` 等具体实现与缓存策略。
