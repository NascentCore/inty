# Voice ID 带 Provider 前缀（provider/voice-name）

## 格式

- **新格式**：`<provider>/<raw_voice_id>`
  - Gemini：`google/Zephyr`、`google/Puck` 等
  - ElevenLabs：`11labs/<elevenlabs_voice_id>`
- **解析规则**：仅按**第一个** `/` 分割；无 `/` 视为无前缀（兼容旧数据）。
  - 例：`parse_voice_id("google/Zephyr")` → `("google", "Zephyr")`；`parse_voice_id("Zephyr")` → `("", "Zephyr")`。

## 后端行为

- **列表接口**：`GET /text-to-speech/list-voices` 返回的每条音色 `voice_id` 均带前缀（Gemini 为 `google/xxx`，ElevenLabs 为 `11labs/xxx`）。
- **合成**：根据 `voice_id` 前缀或（无前缀时）是否在 Gemini 预置集合内，自动选择 Gemini TTS 或 ElevenLabs TTS；调用各自 API 时使用 **raw** 部分。
- **Live 语音**：`_build_live_config` 支持 `google/Zephyr` 与无前缀 `Zephyr`，传给 Gemini Live 的 `voice_name` 为 raw。

## 兼容性

- **读路径**：支持带前缀与无前缀两种形式；无前缀时仍通过「是否在 Gemini 预置名集合」判断 provider。
- **写路径**：新建/编辑角色保存的 `voice_id` 建议为带前缀（与列表返回一致）；旧数据未迁移前可为 `Zephyr`、`JBFqnCBsd6RMkjVDRZzb` 等。
- **可选迁移**：对 `agents.voice_id` 做一次性脚本：若 `voice_id` 在 Gemini 预置名集合则更新为 `google/{voice_id}`；其余可统一为 `11labs/{voice_id}`。

## 相关代码

- `app.core.voice.tts_api`：`parse_voice_id`、`is_gemini_voice`、`VOICE_ID_PREFIX_*`、`get_gemini_voices()` 返回带前缀。
- `app.services.voice_service`：列表为 ElevenLabs 项加 `11labs/` 前缀，`get_voice_info` 按前缀/raw 分支查找。
- `app.services.live_chat_service`：`_build_live_config` 解析 `voice_id` 得到 raw/voice_name。
