# voice - 语音模块

## Cursor Summary

- 目录用途: 与语音/TTS 相关的核心模型与适配。
- 关键文件: `model.py` 定义语音相关的数据结构/枚举，供服务/接口层复用。
- 关键文件: `tts_api.py` 提供 TTS wrapper API（Gemini TTS 优先，失败回退 ElevenLabs），供 `VoiceService` 等上层服务调用。`voice_id` 支持带 provider 前缀（`google/xxx`、`11labs/xxx`），详见 [FR_VOICE_ID_PROVIDER_PREFIX](../../docs/FR_VOICE_ID_PROVIDER_PREFIX.md）。
  - 当配置 `tts.use_gemini_prompted_tts=true` 时，Gemini 使用 `synthesize_with_roleplay_prompt`（角色扮演指令 + 原文）；可通过 iMate `settings.voice_message_narration_mode` 控制语音播报模式：`dialogue_only`（默认，仅朗读台词）或 `dialogue_and_stage_directions`（连同括号内舞台说明一起朗读）。
  - 当配置 `tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate=true` 且目标音色为 ElevenLabs 时，走「Gemini 全文脚本合成 -> ElevenLabs speech-to-speech 变声」链路；该链路不做文本清理、不拆分舞台说明与台词。Gemini 音色路径不受该开关影响。
- 关联: `app/services/voice_service.py`、`app/services/voice_cache_service.py` 等具体实现与缓存策略。
