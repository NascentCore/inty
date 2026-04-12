# Inty 实时语音通话 Android 演示

独立可运行的极简 Android 工程，用于演示 Inty Live Chat WebSocket 语音能力，协议与集成说明见 `docs/FR_EXTERNAL_INTY_VOICE_CALL_INTEGRATION.md`。

## 在 Android Studio 中打开

使用 **File - Open**，选择本目录 `demos/inty_voice_call`（不要打开仓库根目录）。

Android Studio 会自动生成带 `sdk.dir=...` 的 `local.properties`。若用命令行 Gradle，请设置环境变量 `ANDROID_HOME`，或在本地创建 `local.properties` 并写入相同 `sdk.dir`（该文件已列入 `.gitignore`，勿提交）。

运行配置：模块 `app`，执行 `assembleDebug` 后安装到真机或模拟器。

## 界面字段说明

- **API endpoint**：Inty 的 HTTPS 基地址，**不要**末尾斜杠（示例：`https://your-dev-host`）。
- **API key**：JWT，在 HTTP 与 WebSocket 中均作为 `Authorization: Bearer`（长期 token 或登录换得的短期 token）。
- **Agent id**：WebSocket 路径中的 `.../live-chat/{agent_id}`。
- **Speech language code / Response language name**：WebSocket URL 上的可选查询参数（BCP-47 与自然语言名称，与后端校验一致）。

## 操作流程

1. 点击 **Request microphone permission** 授予麦克风权限。
2. 可选：点击 **GET /api/v1/live-chat/status**，确认 `enabled` 与上下行采样率。
3. 点击 **Start voice call**：使用 Bearer 头建立 WebSocket（**不在** URL 中带 `token=`），按服务端 `send_sample_rate` 采集 PCM 上行，解码并播放下行 `audio_response` 的 PCM。
