### 语音实时聊天 Demo（WebRTC / FastAPI / Gemini Live）

- **用户需求（中文概述）**：创建一个使用 WebRTC 的“安卓独立 Kotlin 应用 ↔ FastAPI Python 服务端”的实时语音聊天演示，服务端将安卓端语音代理到 Gemini Live API（`https://ai.google.dev/gemini-api/docs/live`）。所有代码位于 `experimental/voice_chat`，并将 Gemini API Key 等配置放入类似 `app/core/config.py` 风格的文本配置文件中。

- **实现要点**：
  - **服务端**：FastAPI + aiortc 提供 SDP 信令 `/offer`，接收上行音频，代理到 Gemini Live，并将返回音频作为下行音轨回灌给客户端。
  - **客户端**：独立 Android 应用（Kotlin），使用 WebRTC 采集麦克风、通过 HTTP 与服务端交换 SDP、播放返回的音频。
  - **配置**：YAML 配置，支持从环境变量展开（例如 `${GOOGLE_API_KEY}`）。

### 目录结构

```
experimental/voice_chat/
  ├─ server/                # FastAPI + aiortc 服务端
  │   ├─ main.py            # /offer 信令与 Gemini Live 音频桥接
  │   ├─ config.py          # YAML 配置加载（支持环境变量展开）
  │   ├─ config.yaml        # 示例配置（可用 ${GOOGLE_API_KEY}）
  │   ├─ requirements.txt   # 服务端依赖
  │   └─ start.sh           # 启动脚本
  └─ android_app/           # Android WebRTC Demo 应用（Kotlin）
      ├─ settings.gradle.kts
      ├─ build.gradle.kts
      └─ app/
          ├─ build.gradle.kts
          └─ src/main/
              ├─ AndroidManifest.xml
              ├─ res/layout/activity_main.xml
              └─ java/com/example/voicechat/MainActivity.kt
```

### 配置

- **位置**：`experimental/voice_chat/server/config.yaml`
- **说明**：支持从环境变量展开，推荐将 `gemini.api_key` 写为 `${GOOGLE_API_KEY}` 并导出环境变量。

示例：
```yaml
server:
  host: 0.0.0.0
  port: 9001
  stun_server: stun:stun.l.google.com:19302
  log_level: info

gemini:
  api_key: "${GOOGLE_API_KEY}"
  model: gemini-live-2.5-flash-preview-native-audio-09-2025
  voice_name: Zephyr
  send_sample_rate: 16000
  receive_sample_rate: 24000
```

### 运行（服务端）

- 准备 Python 环境（推荐 Python 3.11/3.10，以获得 PyAV 预编译轮子，安装更顺畅）：
```bash
export GOOGLE_API_KEY="你的_Gemini_API_Key"
python3 -m pip install -r experimental/voice_chat/server/requirements.txt
bash experimental/voice_chat/server/start.sh
# 健康检查
curl http://127.0.0.1:9001/healthz
```
- 若安装 `PyAV` 失败（多见于 Python 3.13 或无 FFmpeg 开发库的 Linux 环境），可选择：
  - 切换到 Python 3.11/3.10；或
  - 在系统安装 FFmpeg 开发库后再装依赖（示例命令，需 root 权限）：
    - **Debian/Ubuntu**：`apt-get update && apt-get install -y pkg-config libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libavfilter-dev libswscale-dev libswresample-dev`

### 运行（Android）

- 用 Android Studio 打开 `experimental/voice_chat/android_app`
- 运行到模拟器/真机
- 在输入框填写服务端地址（模拟器访问宿主机用 `http://10.0.2.2:9001`），点击“Start Voice Chat”并授权麦克风权限

### 服务端 API

- **POST `/offer`**：接收客户端 SDP，返回服务端 SDP（本 Demo 不启用 trickle ICE，服务端会等待 ICE 收敛再返回）
- **GET `/healthz`**：健康检查

### 实现细节

- **WebRTC → Gemini**：
  - 上行音频从 WebRTC `MediaStreamTrack` 读取，重采样为 16kHz s16 mono PCM，使用 `audio/pcm;rate=16000` 发送到 Gemini Live。
  - 下行从 Gemini Live 接收 24kHz PCM，封装为音频帧，作为服务端的下行音轨回灌给客户端。
- **注意**：为简化演示，未实现 VAD/断句、降噪、鉴权、带宽自适应等。

### 已知限制与注意事项

- **依赖安装**：`aiortc` 依赖 PyAV；在某些环境需要 FFmpeg 开发库。推荐使用包含 PyAV 预编译轮子的 Python 版本（3.11/3.10）。
- **信令**：演示使用简单的 HTTP SDP 交换且未做鉴权，仅用于本地测试，生产需接入认证和安全校验。
- **网络**：本 Demo 默认使用 Google STUN（`stun.l.google.com:19302`），内网/企业网络需确保 UDP 通信畅通或部署 TURN。

### 后续可扩展方向

- **鉴权与限流**：在 `/offer` 接口加入鉴权和配额控制。
- **文本/指令输入**：在语音会话中附带文本指令或上下文（Gemini Live 支持多模态输入）。
- **Web/iOS 客户端**：补充浏览器与 iOS 的 WebRTC 客户端示例。
- **录音与追踪**：按需将会话音频存储，或接入观测平台（如 LangSmith）记录元数据。
