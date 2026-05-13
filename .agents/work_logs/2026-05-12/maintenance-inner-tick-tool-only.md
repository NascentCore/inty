# maintenance inner tick tool-only

- 维护性 inner tick 在 async 工具路由上固定跳过前台 dual-LLM envelope，仅 `tool_background`；移除 `InnerTickMechanism` / `app.features.inner_tick_mechanism`；WS maintenance 在空前台但已启动 tool_bg 时保留 `foreground_pending` 并跳过首条 outbound。
- `turn.py` / `manager.py` / `config.py` / `companion_chat_service.py` / `chat.py` / 测试与 ARCH、AGENTS 文档已对齐。
