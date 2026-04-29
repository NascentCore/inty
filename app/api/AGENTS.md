# Inty 后端 API 服务端点

- 后台管理用的 API 只能开放给超级用户（superuser）
- 增加新的 API endpoint(s) 需要更新 ENDPOINTS.md
- API endpoint(s) 从一个 py 文件迁移到另一个需要更新 ENDPOINTS.md

## Chat WebSocket

- `/api/v1/chat/ws`：正式对话 WebSocket，走持久化对话流程（写入 chat 历史）。
- `/api/v1/chat/ws/verify`：协议与 `/ws` 一致，但使用 `generate_message_without_user_save`，**不写入 chat_history**；用于校验连接、试对话效果而不污染记录。若在 `/ws` 上扩展路由（例如 agentic v2），需保持 verify 与正式路径行为对齐或单独说明；见 `app/api/v1/endpoints/chat.py` 内 docstring 与 `docs/FR_INTY_V2_CHAT_WS_INTEGRATION_PLAN.md`。
