---
name: inty-backend-inspect
description: >-
  General Inty backend investigation: correlate local Ops logs, LangSmith traces, and Postgres
  (DSN from repo config.yaml) using ws_conn_id, trace/run IDs, user_msg_uuid, inty_trace_id.
  Covers WebSocket / REPL issues and timestamp-specific verification (message.timestamp vs UserTimeContext).
---

# Investigate Inty backend（通用方法：日志 + LangSmith + 数据库）

面向 **`/api/v1/chat/ws`**、**`tools.inty_v2_repl`** 及同类后端问题。先建立 **三条独立数据源** 上的事实，再用 **关联键** 对齐同一事件；避免只信单一来源或混淆「连接级」与「回合级」ID。

## 通用调查方法（三条数据源）

| 数据源 | 典型用途 | 如何接入 |
|--------|----------|----------|
| **本地文件日志**（Ops / uvicorn） | 进程内时间顺序、是否 crash/reload、companion 各阶段、`ws_conn_id` 前缀行 | 路径相对 **启动后端的 cwd**（常见 `./tmp/inty-ops-local.log`，见 [`inty-local-backend-repl`](../inty-local-backend-repl/SKILL.md)）；先 `stat`/`tail` 确认**覆盖事发时段** |
| **LangSmith** | 上游 LLM 输入输出、span 是否 `pending`、父子 trace | 项目名与 API key 与后端进程一致：见 [`langsmith-download-run`](../langsmith-download-run/SKILL.md)「What `config.yaml` drives」；与 [`app/core/config.py`](../../../app/core/config.py) `set_langsmith_environment_variables` 同源 |
| **本地 Postgres** | 落库消息、`created_at`、meta 里的回合键 | 连接信息在仓库根 **`config.yaml`** 的 **`database`** 段（`host` / `port` / `user` / `password` / `db`），与 [`app/utils/config.py`](../../../app/utils/config.py) `DatabaseSettings` 一致；**勿**把密码写进技能或 git |

**工作流（建议顺序）**：(1) 从 REPL/终端或用户描述收集 **至少一个关联键** → (2) **grep 日志** 定 UTC/本地时间窗口与是否缺日志 → (3) **LangSmith** 按 UTC 时间窗或 `trace_id` 拉全 trace → (4) **psql** 用 `user_msg_uuid` / `session_id` / 时间窗对齐 `chat_history` → (5) 下结论（哪一层断裂）。

## 关联键：如何把日志、LangSmith、DB 串成一条链

不同键回答不同问题；**不要**用 `ws_conn_id` 代替 `user_msg_uuid` 做「第几轮对话」关联。

| 键 | 粒度 | 典型出现位置 |
|----|------|----------------|
| **`ws_conn_id`** | 单次 **WebSocket 物理连接**（握手 query，缺省则服务端生成） | Ops 日志：`chat_ws session_open` / `session_end`、inner-tick、控制帧处理等多类行前缀；**不**出现在业务 JSON body；契约见 [`app/schemas/AGENTS.md`](../../../app/schemas/AGENTS.md) |
| **`langsmith_trace_id`**（或 UI 里的 trace UUID） | **一次分布式 trace**（可含多个 span） | REPL `chat` 行、LangSmith UI、下载的 JSON `trace_id` |
| **`langsmith_run_id`** | **单个 span** | REPL、某子 run 的 id |
| **`inty_trace_id`** | **Inty 侧一轮/链路 id**（grep 日志） | companion `run_turn` / `companion_chat_turn` 日志、LangSmith parent run `inputs` |
| **`user_msg_uuid`** | **一轮 companion 用户消息**（RFC4122，常等于客户端 `message_id`） | REPL `user-input message-uuid=`、AI 行 `meta_data.user_msg_uuid`、LangSmith companion 相关 run |
| **`session_id` / `chat_id`** | **聊天会话 / 业务 chat 行** | 日志里的 `session_id=`、`chat=`；`chat_history.session_id`；与 `user_msg_uuid` 配合定位行 |

**时区**：REPL 常 **`+0800`**；日志里也可能带本地偏移；LangSmith `start_time` 多为 **UTC**；查库 `created_at` 多为 **timestamptz**。对齐事件时**先统一换算到 UTC**，再收窄查询窗。

## 何时使用

- REPL 已打印 `user-input message-uuid=…`，长时间没有 `[…] chat …` 助手行，也没有 `chat-ws-error`。
- 需要串联 **`user_msg_uuid`**、**`langsmith_trace_id` / `langsmith_run_id`**、**`inty_trace_id`**、**`ws_conn_id`**。
- LangSmith 上 **`pending`**、或本地日志与 trace **时间对不上**。
- 需要对照 **DB 落库** 与 **日志 / trace**（例如消息是否写入、`created_at` 是否合理）。

## REPL 行为（勿与「后端未处理」混淆）

交互 REPL **先**打印 `user-input`，**再**执行 `bridge.post_turn`（仅 `ws.send`，不等待助手帧）。因此 `user-input` 行上的时间 **可以早于** 服务端开始处理；助手帧可能在后续 **`>`** 轮询中才打印。

见 [`tools/inty_v2_repl/main.py`](../../../tools/inty_v2_repl/main.py)：

```477:482:tools/inty_v2_repl/main.py
        msg_uuid = str(uuid.uuid4())
        t_send = time.perf_counter()
        _print_repl_user_input(line, message_uuid=msg_uuid)
        try:
            mid_sent = bridge.post_turn(agent_id, line, msg_uuid)
```

完整语义见 [`tools/inty_v2_repl/AGENTS.md`](../../../tools/inty_v2_repl/AGENTS.md)。

## 分步操作（映射到三条源）

### A. 收集关联键

从 REPL、用户截图、或第一次 grep 日志里收集上表中的键（**越多越好**）。

### B. 本地日志

- **先**确认文件**最后一行时间** ≥ 事发时刻；否则结论只能是「此日志无法证明当晚」。
- `grep`：`ws_conn_id`、`user_msg_uuid`、`inty_trace_id`、`langsmith_trace_id`、`019e` 形态 run id、`session_id`、`agent_id`。

### C. LangSmith

- 配置与 **`config.yaml` + 环境变量** 一致（见 [`langsmith-download-run`](../langsmith-download-run/SKILL.md)）。
- **`list_runs` `limit` ≤ 100**；大窗需分段或收窄 `start_time`（UTC）。
- 对 `user_msg_uuid` **勿只依赖 metadata filter**（可能 0 命中）；可 **时间窗 + 子串匹配** 序列化 run，或用 [`tools/scripts/langsmith_find_companion_run_by_user_msg_uuid.py`](../../../tools/scripts/langsmith_find_companion_run_by_user_msg_uuid.py)。
- **下载全 trace**（仓库根、venv）：

```bash
python tools/scripts/download_run.py \
  --trace-id "<TRACE_UUID>" \
  -o tmp/langsmith_traces/<TRACE_UUID>.json
```

### D. Postgres（`config.yaml` → `database`）

用 **`meta_data->>'user_msg_uuid'`**、**`session_id`**、**`created_at` 时间窗`** 对齐日志与 trace。示例（把连接参数换成你本机 `config.yaml` 中的值）：

```bash
psql -h <host> -p <port> -U <user> -d <db> -c "
SELECT id, message->>'type' AS msg_type,
       meta_data->>'user_msg_uuid' AS user_msg_uuid,
       created_at
FROM chat_history
WHERE meta_data->>'user_msg_uuid' = 'YOUR_USER_MSG_UUID'
   OR session_id = 'YOUR_SESSION_ID'
ORDER BY id DESC
LIMIT 30;
"
```

### E. 客户端传输与复测

- `INTY_V2_BACKEND_WS_POST_TURN_TIMEOUT_SEC` 等见 [`backend_chat_ws.py`](../../../tools/inty_v2_repl/backend_chat_ws.py)。
- Smoke：[`inty-server-module-verify`](../inty-server-module-verify/SKILL.md)、[`tools/scripts/inty_backend_smoke_tests/test_chat_ws.py`](../../../tools/scripts/inty_backend_smoke_tests/test_chat_ws.py)。

## 专项调查目标示例：消息「时间戳」

用户口中的「时间戳」常混指两件事，**调查结论要分开写**：

| 用户所指 | 技术含义 | 验证方式 |
|----------|----------|----------|
| API / WS 里 **`choices[].message.timestamp`** | 服务端 **`chat_history.created_at`**（持久化时刻，多 UTC 存库） | Postgres `created_at`；代码路径 [`get_ai_message_info_by_id`](../../../app/services/chat_history_service.py) → [`_build_chat_response`](../../../app/api/v1/endpoints/chat.py) |
| 模型是否知道「用户当地几点」 | **`UserTimeContext`**（`local_time` / `timezone` / `utc_offset_minutes`），经 WebSocket **`client_context`** 或请求体 **`time_context`** 合并进 companion；注入 LLM 为 **`##User Time Context`** | LangSmith 子 run **`agentic_companion_chat`** 的 `inputs.messages` 中对应 system 块；合并规则见 [`_chat_request_with_merged_ws_time_context`](../../../app/api/v1/endpoints/chat.py) |

**Inner-tick**（proactive / maintenance）可能从连接缓存 **`tc_box`**（最近一次成功 `client_context`）构造隐式时间上下文；若从未成功 `client_context`，模型侧可能缺少用户时间块（见 [`_implicit_signal_bundle_from_ws_tc_box`](../../../app/api/v1/endpoints/chat.py)）。

## 按 `user_msg_uuid` 扫 LangSmith（仓库根 + venv）

```bash
cd /path/to/inty/repo/root
source .venv/bin/activate
python3 tools/scripts/langsmith_find_companion_run_by_user_msg_uuid.py \
  --user-msg-uuid 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' \
  --window-start-utc '2026-05-11T10:30:00+00:00'
```

`--window-start-utc` 须略早于事发（UTC）；可选 `--config`、`--project-name`。

## 结论表（Agent 速查）

| 日志覆盖事发 | LangSmith | REPL | 下一步 |
|--------------|-----------|------|--------|
| 否 | （任意） | 无 error | 换真实日志或确认 `--log-file`；勿从旧文件推断。 |
| 是 | 对应 UUID + chat **pending** | 无下行 | 查 reload/crash/OOM、上游 LLM 超时。 |
| 是 | **无** run | 无 error | 核对 project/API key、tracing 开关、消息是否到达。 |
| 是 | success | 无下行 | 查客户端解析/sideband（少见）。 |
| （任意） | （任意） | **`chat-ws-error`** | 读 `code`/`message`、鉴权与业务错误。 |

## See also

- [`inty-local-backend-repl`](../inty-local-backend-repl/SKILL.md)
- [`langsmith-download-run`](../langsmith-download-run/SKILL.md)
- [`inty-server-module-verify`](../inty-server-module-verify/SKILL.md)
- [`docs/companion_harness/ARCH.md`](../../../docs/companion_harness/ARCH.md)
- [`app/core/companion_harness/llm/llm_chat_runtime.py`](../../../app/core/companion_harness/llm/llm_chat_runtime.py)

## 实现边界

- 技能 **不**改产品代码；LangSmith 辅助脚本见 [`tools/scripts/langsmith_find_companion_run_by_user_msg_uuid.py`](../../../tools/scripts/langsmith_find_companion_run_by_user_msg_uuid.py)。
- **不要**在 Markdown 或 git 中粘贴 `config.yaml` 里的密码或 API key。
