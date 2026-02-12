# AGENTS.md · experimental/（原型与实验）

本文件覆盖并补充根 `AGENTS.md`，仅适用于 `experimental/`。

## 边界

- 非生产代码；不作为发布工件依赖；不影响 `app/` 与 `android_app/` 的构建。

## 约定

- 尽量最小化依赖并隔离环境；如需脚本/服务，请在本目录自备 `requirements.txt` 或说明。
- 若原型成熟，应迁移到对应正式目录并补齐测试与文档。

## 目录索引（节选）

- `fastapi_otel/`：FastAPI + OpenTelemetry 请求/响应追踪最小化 demo（纯 OTLP，无 Sentry）。
- `gemini_native_audio_websocket_demo/`：Gemini Live（native audio）WebSocket demo（Plain JS + Python SDK），包含 single-session 复现与 reconnect 绕过模式。
- `image_model_benchmark/`：图像生成模型评测工具，对比 Seedream 4.5、Gemini 2.5 Flash Image、Nano Banana Pro、Flux.2 Pro 的响应时间和效果。
- `memory_prompt_benchmark/`：记忆提示词评测工具，从用户聊天历史提取记忆，对比有记忆和无记忆情况下与新角色的对话效果。
