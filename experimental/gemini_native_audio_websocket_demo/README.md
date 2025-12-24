# Gemini Native Audio WebSocket Demo（Plain JS + Python SDK）

CREATED_BY_AGENT

本目录用于复现与验证 Gemini Multimodal Live API（native audio）在 **WebSocket** 场景下的行为，参考官方示例的使用方式：`plain-js-python-sdk-demo-app`。

## 功能

- 前端：纯 HTML/JS
  - 采集麦克风音频，重采样到 16kHz PCM16，分块通过 WebSocket 发送到后端
  - 播放后端返回的 24kHz PCM16 音频
- 后端：Python（google-genai SDK + FastAPI WebSocket）
  - 连接 Vertex AI Live（native audio 模型）
  - 将前端音频转发到 Gemini Live
  - 将 Gemini 的音频响应转发回前端

## 运行

### 1) 准备 GCP 凭证

需要设置 `GOOGLE_APPLICATION_CREDENTIALS` 指向服务账号 JSON。

本仓库里如果存在 `inty-backend-key.json`，服务端也会自动尝试使用它（无需 export）。

### 2) 启动服务端

在仓库根目录执行：

```bash
python -m uvicorn experimental.gemini_native_audio_websocket_demo.server:app --reload --port 8765
```

### 3) 打开页面

浏览器打开：

`http://127.0.0.1:8765/`

点击 **Start**，允许麦克风权限后讲话即可。

## 模式：复现 #1224 vs 绕过

服务端提供两种模式（通过 URL query 控制）：

- `ws://127.0.0.1:8765/ws?mode=single`：单个 live session（用于复现 #1224 类问题）
- `ws://127.0.0.1:8765/ws?mode=reconnect`：每次 `turn_complete` 后重连（绕过方案）

前端 UI 里可以切换模式。

## 调试日志

服务端会把关键事件写入：

`/Users/donggang/Documents/code/inty-backend/.cursor/debug.log`

重要字段：

- `location=demo_server.py:turn_complete`：收到 turn_complete
- `location=demo_server.py:reconnect_*`：重连前/后/失败
