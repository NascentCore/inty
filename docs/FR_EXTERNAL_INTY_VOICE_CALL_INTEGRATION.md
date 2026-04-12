# 外部集成：Inty 实时语音通话（Live Chat）API

本文面向需要在自有系统中调用 Inty **实时语音通话**能力的外部开发者与集成方。

## 1. 可行性结论（与常见预期的差异）

| 说法 | 实际情况 |
| --- | --- |
| 「独立 API 服务」 | 语音通话能力以 **Inty 主后端** 中的路由形式提供（`/api/v1/live-chat/...`），**不是**单独进程或单独域名下的微服务。若必须物理隔离，需要运维侧做独立部署或网关拆分（本仓库未提供现成「仅语音」部署形态）。 |
| 「Kotlin client library」 | 仓库内存在 Android 库模块 `android_app/library/inty_voice_call`，用于 **Android（Ktor WebSocket）** 集成；**不是**纯 JVM 无 Android 依赖的 SDK。非 Android 客户端应直接按本文 **WebSocket JSON 协议** 实现。 |
| 「生成 API key」 | 当前实现使用 **JWT（Bearer）** 校验用户身份（与 App 其它接口一致），**没有**面向第三方的专用静态 API key 机制。常见做法是：在目标环境数据库中创建 **邮箱密码（`AuthType.EMAIL`）用户**，再调用登录接口换取 JWT（见 **2.1**）。对外沟通时仍建议称「访问令牌 / JWT」而非 API key。 |

在以上前提下：**技术上可行**（调用 dev 环境同一套 Inty 后端即可），但命名上更准确的表述是「开放 Live Chat WebSocket 与配套 HTTP 接口」，而非「独立语音微服务 + API key」。

## 2. 前置条件（由 Inty 运营方提供）

集成方需要从 Inty 侧获得：

1. **Dev 环境 HTTPS 基地址**（示例占位符：`<YOUR_INTY_DEV_BASE_URL>`，无尾部斜杠）。生产环境若开放，同理替换为 prod 基地址。
2. **可用的 `agent_id`**：对应 Inty 中已配置、且该用户有权使用的角色（Agent）。
3. **访问令牌**：JWT 字符串，在 HTTP/WebSocket 请求中作为 `Authorization: Bearer <token>` 传递（见下文）。令牌对应 Inty 中的 **真实用户**，用量与订阅策略绑定到该用户。获取方式之一见 **2.1**。

**服务端必须开启 Live Chat**：若功能关闭，WebSocket 会以关闭码 `4003` 拒绝（reason：`Live chat is disabled`）。

### 2.1 邮箱密码用户与登录换票（可行）

**结论**：可行。Inty 支持在请求体中同时提供 `email` 与 `password` 时走邮箱密码校验，成功后返回与其它登录方式相同的 JWT（见 `app/api/v1/endpoints/auth.py` 中 `POST .../google/login` 分支调用 `email_password_login`）。

**运营方（有该环境数据库与代码检出）典型流程**：

1. **配置**：在仓库根目录使用 **该 dev 环境** 对应的 `config.yaml`（或等价环境变量），保证脚本的 `AsyncSessionLocal` 连到 dev 库（与运行中的 Inty dev 实例一致）。
2. **创建用户**：在仓库根执行（需已安装应用依赖与 `PYTHONPATH=.`）：

   ```bash
   export PYTHONPATH=.
   python scripts/create_email_password_superuser.py \
     --email partner-dev@example.com \
     --password '<strong-password>' \
     --is-superuser=false \
     --nickname "Live chat integration" \
     --yes
   ```

   - 脚本路径：`scripts/create_email_password_superuser.py`；更细的字段说明见 `scripts/CREATE_EMAIL_PASSWORD_USER.md`。
   - 对 **外部集成专用账号** 建议使用 `--is-superuser=false`，避免误用超级用户权限（例如 WebSocket 上的 `assume_user_id` 仅对 superuser 生效）。
3. **换取 JWT**：对 **同一 dev 环境的 HTTP 基地址** 调用：

   ```bash
   curl -sS -X POST "<YOUR_INTY_DEV_BASE_URL>/api/v1/auth/google/login" \
     -H "Content-Type: application/json" \
     -d '{"email":"partner-dev@example.com","password":"<strong-password>"}'
   ```

   成功时响应为统一 `APIResponse` 包装：`code == 200` 且 `data.token` 即为 JWT。将该值作为 `Authorization: Bearer ...` 用于 `GET /api/v1/live-chat/status` 与 Live Chat WebSocket。

**集成方注意**：

- 若环境将 `app.api_endpoints.use_dummy_api_v1_auth_google_login` 设为 `true`，该登录端点会返回固定假数据，**无法**用真实邮箱密码换票；需 Inty 运营方在 dev 上关闭该开关后再联调。
- 令牌过期时间由服务端 `security.access_token_expire_minutes` 等配置决定；过期后需用同一登录请求刷新 JWT。
- 邮箱与密码由运营方安全渠道单独交付集成方，**不要**把密码写进版本库或聊天日志。

## 3. HTTP：查询能力状态

- **方法 / 路径**：`GET /api/v1/live-chat/status`
- **鉴权**：`Authorization: Bearer <JWT>`（与其它需登录接口一致）
- **成功响应**：统一 `APIResponse` 包装；`data` 中含 `enabled`、`model`、`default_voice`、`send_sample_rate`、`receive_sample_rate`、`default_speech_language_code`、`default_response_language_name` 等字段，供客户端做采样率与默认语言对齐。

未带有效 JWT 时返回 **401**。

## 4. WebSocket：建立实时语音会话

### 4.1 URL

在基地址上将 `https` 换为 `wss`、`http` 换为 `ws`，路径为：

```text
{ws_base}/api/v1/live-chat/{agent_id}
```

可选查询参数（单次会话语言覆盖，与实现一致）：

- `speech_language_code`：BCP-47，例如 `en-US`
- `response_language_name`：自然语言名称，用于回复语言指令，例如 `English`

**鉴权**（按优先级，与后端实现一致）：

1. 请求头：`Authorization: Bearer <JWT>`（**推荐**）
2. 子协议：`Sec-WebSocket-Protocol: Bearer, <JWT>`
3. 兼容旧用法：查询参数 `?token=<JWT>`（注意日志与 Referer 泄漏风险，生产集成优先用 Header）

### 4.2 连接后的典型流程

1. 服务端在校验订阅与用量通过后 **accept** 连接。
2. 首条下行 JSON 为 **session_info**（类型字段为 `session_info`），包含 `remaining_duration`、`agent_limit`、`agent_count` 等。
3. 客户端按采样率发送 **PCM 音频**（上行 `audio` 消息，payload 为 base64），并可发送 `activity_start` / `activity_end` 等控制消息。
4. 服务端下行 `audio_response`、`transcript`、`user_transcript`、`status`、`error`、`latency` 等类型消息。

### 4.3 上行消息（JSON 文本帧）

| `type` | 说明 |
| --- | --- |
| `audio` | `data` 为 base64 编码的 PCM 字节 |
| `text` | `data` 为文本；将传入实时会话 |
| `activity_start` | 活动开始（无 `data`） |
| `activity_end` | 活动结束 |
| `end` | 客户端主动结束 |

### 4.4 下行消息（JSON 文本帧，主要类型）

| `type` | 说明 |
| --- | --- |
| `session_info` | 会话配额信息 |
| `audio_response` | `data` 为 base64 PCM；含 `sample_rate`（与配置中的接收采样率一致） |
| `transcript` | 模型侧转写；可含 `is_final`、`message_id`、`timestamp` |
| `user_transcript` | 用户侧转写 |
| `status` | `status`、`message` 字段表示会话状态 |
| `error` | 业务错误；含 `code`、`error_code`、`message` |
| `latency` | 延迟指标（字段以后端实际 payload 为准） |

### 4.5 WebSocket 关闭码（节选）

| 关闭码 | 含义 |
| --- | --- |
| `4000` | 语言相关查询参数非法 |
| `4001` | 未认证或 token 无效 |
| `4003` | Live Chat 未启用 |
| `4010` | Agent 数量限制 |
| `4011` | 时长限制 |

用量或订阅不满足时，可能先 **accept** 再下发一条 `error` 类型 JSON，然后关闭连接；具体 `error_code` 与 HTTP API 业务错误码体系一致（例如未订阅、Agent 上限、时长上限等）。

## 5. Kotlin（Android）源码共享方式

库路径（可将该目录以源码形式拷贝或 submodule 引入到你的 Android 工程）：

```text
android_app/library/inty_voice_call/
```

主要入口：

- `IntyVoiceCallUrls.liveChatWebSocketUrl(...)`：拼接 WebSocket URL（默认使用查询参数 `token=`，集成时建议改为在 Ktor `HttpClient` 上配置 `Authorization` 头，避免 token 出现在 URL）。
- `IntyVoiceCallClient` / `VoiceCallWebSocketDataSource`：基于 Ktor 的 WebSocket 与 `kotlinx.serialization` 的 `CallPacket` 收发。

依赖与版本见同目录下 `build.gradle.kts`（含 Ktor WebSocket、Kotlin Serialization 等）。

## 6. 非 Android 客户端实现要点

- 使用任意 WebSocket 库连接上述 URL，**必须**支持携带 `Authorization: Bearer` 或 `Sec-WebSocket-Protocol`。
- 消息体为 **UTF-8 JSON 文本帧**，与上文章节一致。
- 上行 PCM 的采样率须与 `GET /api/v1/live-chat/status` 返回的 `send_sample_rate` 对齐（否则可能导致识别或桥接异常）。

## 7. 安全与合规建议（运营 + 开发）

- JWT 等价于账户凭证：应 **最小权限** 创建专用测试用户，仅用于 dev 联调；勿与管理员账号混用。
- 若文档中曾称「API key」，建议在对外沟通中改为 **「服务账户 JWT」** 或 **「集成测试用户令牌」**，避免与真正的静态 API key 混淆。
- Dev 环境数据与模型行为可能与生产不一致；对外承诺 SLA 前需单独约定。

## 8. 若必须对齐「独立服务 + API key」产品形态

本仓库当前未提供以下能力，如需对外产品化可考虑后续工程投入：

1. **部署隔离**：单独服务或网关只暴露 `live-chat` 与最小依赖，与主业务 API 解耦。
2. **第三方凭据模型**：例如 `X-Inty-Api-Key` 映射到租户、独立限流与审计，而非共享 App 用户 JWT。
3. **跨平台 SDK**：在 `inty_voice_call` 之外提供 JVM / Node / Python 参考实现或 OpenAPI 扩展说明。
4. **文档自动化**：从 `app/api/v1/endpoints/live_chat.py` 与 `app/schemas/live_chat.py` 生成 OpenAPI / 协议版本号，减少手工文档漂移。

---

**实现参考（仓库内）**

- WebSocket 路由与消息类型说明：`app/api/v1/endpoints/live_chat.py`
- Android URL 与客户端封装：`android_app/library/inty_voice_call/`
