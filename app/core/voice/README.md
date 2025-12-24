# voice - 语音模块

## Cursor Summary

- 目录用途: 与语音/TTS 相关的核心模型与适配。
- 关键文件: `model.py` 定义语音相关的数据结构/枚举，供服务/接口层复用。
- 关键文件: `tts_api.py` 提供 TTS wrapper API（Gemini TTS 优先，失败回退 ElevenLabs），供 `VoiceService` 等上层服务调用。
- 关联: `app/services/voice_service.py`、`app/services/voice_cache_service.py` 等具体实现与缓存策略。
