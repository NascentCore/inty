# FR_PHONE_CALL - PSTN 与 App 内实时通话

## 功能概述

Phone Call 是 Inty 多媒介互动能力的电话层。它把三类入口统一到现有实时语音栈：用户在聊天中明确说“Call me at ...”时由 agent 外呼；用户直接拨打 agent 的 Twilio 号码时接入同一 companion；Android / iOS App 内点击实时语音通话时仍走既有 Live Chat WebSocket。后端复用 Agent、聊天会话、Gemini Live、聊天历史与 live-chat 用量体系，不新增独立 AI 对话栈。

功能开关默认开启，但实际可用性由运行环境配置决定：Twilio 凭据、Twilio 主叫号码、公网 `wss` Media Stream 地址与 Gemini Live 都配置完成后，`GET /api/v1/phone-calls/status` 才会返回 `available=true`。

## 入口与行为

| 入口 | 用户动作 | 后端路径 | 说明 |
| --- | --- | --- | --- |
| 聊天触发 | `Call me at 1234560123` | `/api/v1/chat/ws` 内部触发 | 当前轮明确要求打电话且含号码时直接外呼；不会从记忆或旧消息推断号码。 |
| 显式 API | App / 内部工具传手机号 | `POST /api/v1/phone-calls/{agent_id}` | 用于产品按钮或调试工具触发 PSTN 外呼。 |
| 直接来电 | 用户拨打 Twilio 号码 | `POST /api/v1/phone-calls/twilio/inbound` | Twilio Voice webhook；识别已绑定 caller 后返回 Media Stream TwiML。 |
| PSTN 音频桥 | Twilio Media Streams | `WS /api/v1/phone-calls/twilio-media` | Twilio μ-law 8k 与 Gemini Live PCM 流互转。 |
| App 内通话 | Android / iOS 语音按钮 | `WS /api/v1/live-chat/{agent_id}` | 不经过 Twilio，直接复用 Live Chat 协议。 |

## 身份与隐私

- 后端不使用也不写入 `users.phone`。
- 用户通过登录态发起外呼时，后端为该号码建立 caller binding，用于后续直接来电识别。
- caller binding 只保存标准化手机号的 HMAC 与脱敏展示；不保存完整明文手机号。
- 未绑定号码直接来电时，Twilio 会收到一段拒绝 TwiML，请用户先打开 App 让 Inty 主动打一次电话。
- Media Stream WebSocket 使用短期签名 token；Twilio URL 中不携带用户 JWT。

## 配置

```yaml
phone_call:
  enabled: true
  default_country_code: "+1"
  twilio_from_number: ""
  twilio_media_stream_base_url: ""
  twilio_account_sid: ""
  twilio_auth_token: ""
  inbound_number_agent_map: {}
  default_inbound_agent_id: ""
  media_stream_token_ttl_seconds: 300
```

部署时 Twilio 密钥优先走环境变量：

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`

`twilio_media_stream_base_url` 必须是公网可访问的 `wss://` 后端基地址，不带尾部斜杠。直接来电需要把 Twilio 号码配置到 `inbound_number_agent_map`，键为 Twilio E.164 号码，值为 agent id；没有映射时才使用 `default_inbound_agent_id`。

## API 契约

### `GET /api/v1/phone-calls/status`

登录用户查询当前环境的电话能力状态。响应不暴露任何 secret：

```json
{
  "enabled": true,
  "available": false,
  "twilio_configured": false,
  "media_stream_configured": false,
  "live_chat_enabled": false,
  "from_number_configured": false
}
```

### `POST /api/v1/phone-calls/{agent_id}`

登录用户请求 agent 外呼：

```json
{
  "phone_number": "+14155550123",
  "speech_language_code": "en-US",
  "response_language_name": "English"
}
```

成功后返回 Twilio call sid、状态与脱敏号码。服务端会先检查 live-chat 用量限制；被限制时沿用现有订阅业务错误形状。

### Twilio inbound webhook

Twilio Voice webhook 指向：

```text
POST https://<backend>/api/v1/phone-calls/twilio/inbound
```

后端根据 `From` 的 HMAC binding 识别用户，根据 `To` 的号码映射识别 agent，然后返回 `<Connect><Stream ... /></Connect>` TwiML。

## 通话音频

- Twilio 入站：μ-law 8k，base64 JSON `media.payload`。
- Gemini Live 入站：PCM16 16k。
- Gemini Live 出站：PCM16 24k。
- Twilio 出站：μ-law 8k。

音频桥只做协议与采样率转换，不改变实时语音的人设、历史、配额和落库逻辑。

## 安全边界

- 仅当前轮明确要求打电话时，agent 工具可外呼；implicit greeting、proactive heartbeat、maintenance inner tick 都不能主动打电话。
- 直接来电必须命中已绑定 caller；未知号码不创建匿名用户、不进入任何 agent 记忆空间。
- 日志与响应仅使用脱敏号码。
