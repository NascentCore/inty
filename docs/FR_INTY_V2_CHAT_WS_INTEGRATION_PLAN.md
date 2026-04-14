# FR_INTY_V2_CHAT_WS_INTEGRATION_PLAN

基于当前仓库内 Inty 后端（`app/`）代码整理的 v2（companion / agentic kernel）与既有 `WebSocket /api/v1/chat/ws` 的集成说明与后续事项。面向调用方的 API 错误文案仍须为英文（见 `app/AGENTS.md`）。

## 1. 目标与约束

- 与 Android 现网一致的路径：`wss://{base}/api/v1/chat/ws`；每轮一条 JSON 请求、一条 JSON 响应（`SendMsgResponse` 形态）；控制帧支持 `ping` / `pong` 文本 JSON，以及会话级 `client_context`（见下）。
- v2 落在同一进程内；原型能力经 `app/services/companion_chat_service.py` 与 `app/core/agentic_kernel/companion/` 收敛到产品路径。
- 面向调用方的错误字符串保持英文。

## 2. 阶段 0 - 契约与范围

- 服务端 `ChatWebSocketRequest`（`app/schemas/chat.py`）与 Android `ChatWebSocketReq` / `SendMsgReq` / `SendMsgResponse`（`android_app/core/data/.../ChatBeans.kt`）对齐；新增字段在客户端未使用前应为可选（客户端可忽略未知 JSON 键）。
- **首版范围**：仅用户主动发起的轮次，与现网 WS 一致。不把 proactive heartbeat、内核 tick、排程驱动轮次绑到首版 WS；这些需要 worker 或新客户端协议。
- **灰度**：生产 `/ws` 一律走 companion 内核；YAML 中的 `chat_use_companion_kernel_agent_ids` 在 `load_config` 时被丢弃（`app/utils/config.py`），不再作为按 `agent_id` 开关。

## 3. 阶段 1 - 共享聊天入口（HTTP 与 WS）- 已实现

- **单一行为入口**：`POST /api/v1/chat/completions/{agent_id}` 与 `WebSocket /api/v1/chat/ws` 均调用 `_agent_chat_completions_impl`（`app/api/v1/endpoints/chat.py`），通过参数 `chat_route: Literal["http", "websocket"]` 区分，避免订阅、错误与持久化逻辑分叉复制。
- **路由规则**：`chat_route == "websocket"` 时使用 companion（`companion_chat_service.run_companion_chat_turn_for_api`）；`chat_route == "http"` 时仍走 legacy `Agent.chat`。
- **生产 WS**：`chat_completions_websocket` 在收到合法 `ChatWebSocketRequest` 后固定传入 `chat_route="websocket"`。

## 4. 阶段 2 - 持久化 - 已实现（需知局限）

- companion 路径在 `run_companion_chat_turn_for_api` 返回文本后，依次 `chat_history_service.add_user_message_async` 与 `add_ai_message_sync_async` 写入 `chat_history`，与消息列表 API 一致。
- **顺序与一致性**：先 companion 状态持久化（API 路径为 Postgres + MemoryStore，非 workspace 磁盘），再写 `chat_history`；两阶段之间失败可能导致 companion 状态与列表短暂不一致（见 backlog「原子性」）。

## 5. 阶段 3 - 身份与工作区映射 - 已实现

- `CompanionManager.get_or_create_session(user_id, agent_id, chat_key)`，`chat_key` 为 `str(chat.id)`（`companion_chat_service.run_companion_chat_turn_for_api`）。
- 工作区根目录由 `app.features.companion_workspaces_base_dir` 配置（默认 `/var/lib/inty/companion_workspaces`），仅参与 `workspace_root` 数据库键前缀；在 `companion_chat_service` + 已配置数据库 DSN 时**不在**该路径下 `mkdir` 或写入权威状态文件（见 `app/api/ENDPOINTS.md` 与 `MemoryStore.uses_repository_without_workspace_disk`）。
- 用户多段纯文本在 HTTP/WS 侧仍经 `HumanMessage` / `extract_text_content` 等路径；companion 路径当前以**拼接后的纯文本** `user_text` 调用 `run_turn`（含图的多模态见 backlog）。

## 6. 阶段 4 - 异步、超时与 DB 会话

- **空闲超时**：`app.features.chat_ws_idle_timeout_seconds`（默认 60；校验范围 10..3600，`_validate_config`）。`asyncio.wait_for(websocket.receive_text(), timeout=...)`；长 LLM/工具执行**不会**单独延长该计时器，客户端需定期发 `ping` 或任意文本帧，或调大配置。
- **控制帧与会话时间**：`_handle_chat_websocket_control_json` 处理 `type: ping`（回 `pong`）、`type: client_context`（校验 `time_context` 为 `UserTimeContext`，成功则 `client_context_ack` 且写入会话级 dict）。后续聊天帧若请求体未带 `user_time_context`，由 `_chat_request_with_merged_ws_time_context` 合并该会话缓存。
- **AsyncSession**：整条 WS 连接共用一个 `Depends(deps.get_async_db)` 得到的 session；不得传入 `asyncio.to_thread` 或其它线程；若 companion 将来在 worker 线程跑阻塞逻辑，须在线程内新开 session 或避免在该线程用 DB。
- **单轮墙钟上限**：当前代码中**未**实现单独的单轮超时配置；仍依赖客户端读超时与上游 LLM 行为。若需要结构化「超时错误」响应，需后续加配置与 `wait_for` 包裹。

## 7. 阶段 5 - `/ws/verify` 与生产 `/ws` 对齐 - 未完成

- `chat_completions_websocket_verify` 仍使用 `generate_message_without_user_save`，**不**走 `_agent_chat_completions_impl`，**不**写 `chat_history`，**不**跑 companion（见该端点 docstring）。
- 建议后续：抽共享调度器并带 `persist: bool`（或与生产共用 `chat_route` + `persist`），否则 QA 需明确「verify 仅验证 legacy 引擎与连接」，与生产 companion 行为不一致。

## 8. 阶段 6 - 测试

- `tests/AGENTS.md` 倾向 E2E；WS 处理器在 `tests/app/api/v1/endpoints/test_chat.py` 中可对鉴权与 completion 做隔离桩（与仓库约定一致）。
- 已覆盖：空闲超时相关、companion 路径多模态拒绝（400 + JSON 错误帧且连接保持）等；新增契约时继续扩展该文件。

## 9. 上线与回滚

- 生产 `/ws` 一律 companion；回滚依赖发版或流量切换，不再依赖 YAML 白名单。

## 10. 配置参考（与实现对齐）

```yaml
app:
  features:
    chat_ws_idle_timeout_seconds: 60
    companion_workspaces_base_dir: "/var/lib/inty/companion_workspaces"
    companion_default_context_mode: "intimate"
    # 可选：companion 转写压缩；null 关闭
    # companion_transcript_compaction: ...
    # 可选：加载转写窗口上限
    # companion_transcript_llm_window_max_messages: ...
```

- `FeaturesConfig` 定义见 `app/utils/config.py`；`companion_transcript_compaction` 默认由 `DEFAULT_COMPANION_FEATURE_COMPACTION` 填充。
- 嵌套 `app.api_endpoints` 等仍由 `load_config` 解析。

## 11. 评估与 WS 辅助行为（代码现状）

- **assume_user_id**：超级用户可在 query 传 `assume_user_id`，语义与 HTTP `X-Assume-User-Id` 对齐（`_resolve_assumed_chat_websocket_user`）。
- **appVersionCode**：WS 从请求头 `appVersionCode` 读取整型，用于节日/日常记忆等门控（与 HTTP 头一致）。
- **premium_preview**：仅 `not use_companion` 时计算；companion WS 路径不生成付费预览 choice。

## 12. 后续 backlog（按 touching 同一链路时优先级自排）

| 序号 | 项 | 说明 |
|------|-----|------|
| 1 | **多模态用户轮** | **已完成（2026-04-12）**：WS companion 路径若最后一条用户消息含 `image_url`，返回 HTTP 400 等价信息（WS 上为 JSON：`code` / `message` / `agent_id`，连接不关闭）。多段纯文本仍合并为文本进入 `run_turn`。内核内完整多模态行仍为后续工作。实现见 `ChatMessage.has_image_content_part`、`_companion_rejects_multimodal_user_turn`、`chat_completions_websocket` 对 `HTTPException` 的 JSON 映射；`_agent_chat_completions_impl` 内层 `except HTTPException: raise` 避免吞掉业务异常。 |
| 2 | **原子性：工作区 vs chat_history** | `run_turn` 与 `chat_history` 两步之间失败时的补偿或单事务边界。 |
| 3 | **首轮 bootstrap 语义** | `app.features.companion_workspace_bootstrap_type`：`LEGACY` 时 `bootstrap_session` 消费首条用户输入直至五件套就绪；`USER_INTERACTIVE` 时用户始终在 `run_turn`，由 `bootstrap_user_interactive` 注入规范与切片工具，模型调用 `companion_bootstrap_user_interactive_complete` 结束阶段；`NONE` 为默认。缺少该 YAML 键时，旧布尔项会映射为该枚举（交互式优先于 legacy）。 |
| 4 | **配置热更新** | `_companion_manager_for_resolved_model` 使用 `lru_cache`；改 YAML 不重启进程时须调用 `clear_companion_chat_service_caches()` 或接入重载钩子。 |
| 5 | **`/ws/verify` 与 companion 对齐** | 同阶段 5。 |
| 6 | **lazy `get_agent`** | companion 路径仍为语音等逻辑加载 legacy `Agent`；可评估延后加载或拆分依赖。 |
| 7 | **单轮超时** | 配置化墙钟上限，在超时返回结构化错误（当前未实现）。 |
| 8 | **E2E** | CI 稳定 stub 或环境开关下，补充「WS companion 一轮 + 消息列表」真实服务级测试。 |

### 变更记录

- **2026-04-12**：backlog 项「多模态用户轮（WS companion）」完成；测试见 `tests/app/api/v1/endpoints/test_chat.py`。
- **2026-04-13**：本文档按 `chat.py`、`companion_chat_service.py`、`config.py` 当前实现重写为中文并补充 `client_context`、companion 配置项与 verify 差异。
