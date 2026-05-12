---
name: investigate-imate-ws-backend
description: >-
  Debug Inty/iMate companion WebSocket /api/v1/chat/ws + tools.inty_v2_repl: no assistant reply after
  user-input, LangSmith pending runs, user_msg_uuid / inty_trace_id correlation, Ops log time coverage,
  post_turn vs downlink. Use with local Ops :8001 and LangSmith project inty-backend-local-* .
---

# Investigate iMate companion WebSocket backend（本地 Ops + REPL）

面向 **Inty Ops** 挂载的伴侣路由 **`/api/v1/chat/ws`** 与终端客户端 **`tools.inty_v2_repl`**（只做传输与打印，推理在服务端）。用于系统性区分：**客户端未等到帧**、**日志文件未覆盖事发时段**、**LangSmith 显示推理未收尾**，避免误判。

## 何时使用

- REPL 已打印 `user-input message-uuid=…`，长时间没有 `[…] chat …` 助手行，也没有 `chat-ws-error`。
- 需要从 **`user_msg_uuid`**、**`langsmith_trace_id` / `langsmith_run_id`**、**`inty_trace_id`** 串起证据链。
- LangSmith 上出现 **`pending`** 的根 run / `agentic_companion_chat` 子 run，需对照本地进程或上游 LLM。

## REPL 行为（勿与「后端未处理」混淆）

交互 REPL **先**打印 `user-input`，**再**执行 `bridge.post_turn`（仅 `ws.send`，不等待助手帧）。因此：

- `user-input` 上的本地时间戳 **可能早于** 服务端真正开始一轮 companion（例如 `post_turn` 在重连预算内阻塞）。
- 助手帧在后续 **`>` 等待输入** 时经 sideband 轮询打印；若截图太早会像「无回复」。

见 [`tools/inty_v2_repl/main.py`](../../../tools/inty_v2_repl/main.py)：

```477:482:tools/inty_v2_repl/main.py
        msg_uuid = str(uuid.uuid4())
        t_send = time.perf_counter()
        _print_repl_user_input(line, message_uuid=msg_uuid)
        try:
            mid_sent = bridge.post_turn(agent_id, line, msg_uuid)
```

完整语义见 [`tools/inty_v2_repl/AGENTS.md`](../../../tools/inty_v2_repl/AGENTS.md)。

## 排查步骤（按顺序）

### A. 收集关联 ID

| 来源 | 字段 |
|------|------|
| REPL `user-input` | `message-uuid` → 当作服务端侧的 **`user_msg_uuid`** 关联键 |
| REPL 已有 `chat` 行 | `langsmith_trace_id`、`langsmith_run_id`（拉 trace） |
| LangSmith parent run | `inputs.inty_trace_id`（辅助 grep Ops 日志） |

### B. 校验 Ops 文件日志是否覆盖事发时段

- 常见路径（相对 **启动 Ops 时的 shell cwd**）：[`inty-local-backend-repl`](../inty-local-backend-repl/SKILL.md) 示例 `./tmp/inty-ops-local.log`。
- **先** `tail` / `stat` 看**最后一行时间与是否 Shutdown**；若在事发时刻之前已结束，结论必须是：**本文件无法证明当晚会话**，需用户当晚终端输出或实际使用的 `--log-file`。
- 再 `grep`：`user_msg_uuid`、`inty_trace_id`、`agent_id`（UUID）、LangSmith run id（如 `019e…`）。

### C. LangSmith

**项目名与密钥**（与后端一致）见 [`langsmith-download-run`](../langsmith-download-run/SKILL.md) 中「What `config.yaml` drives」表：`LANGSMITH_PROJECT` 由 `app.name`、`app.environment` 推导；`environment: local` 时后缀 **`-{USER slug}`**。API key 来自 `agent.langchain_api_key` 或环境变量 **`LANGCHAIN_API_KEY` / `LANGSMITH_API_KEY`**（技能正文不抄写密钥）。

**时区**：REPL 横幅常为 **`+0800`**；LangSmith `start_time` 多为 **UTC**。先把「事发本地时间」换成 **UTC** 再设查询窗口，避免搜错区间。

**查询限制**：`list_runs` 单次 **`limit` 不得超过 100**（LangSmith API 限制）；宽窗可能截断，需收窄 `start_time` 或分段查询。全 trace 下载脚本同样受单批上限约束，见 [`scripts/download_run.py`](../../../scripts/download_run.py)。

**勿单靠 metadata filter**：对 `user_msg_uuid` 的 structured filter 在实践中可能 **0 命中**。优先：**UTC 时间窗** + 关注 **`agentic_companion_user_turn`** + 将 run `model_dump` 序列化后 **子串匹配 UUID**。

**解读**：

- 根 run（`agentic_companion_user_turn …`）与子 run **`agentic_companion_chat`** 长期 **`pending`** 且 **`error` 为空** → 推理已在服务端挂上但未在 LangSmith 侧收尾（进程被杀、`uvicorn --reload`、上游 LLM 挂死、上报未完成等）。
- 窗口内 **无任何含该 UUID 的 run** → 可能未进入 companion 父 span、**tracing 关闭**、**API key / project 与事发环境不一致**、或消息从未到达服务端。

**归档 trace**：在仓库根执行（venv 已激活）：

```bash
python scripts/download_run.py \
  --trace-id "<TRACE_ID_FROM_REPL_OR_PARENT_RUN>" \
  -o tmp/langsmith_traces/<TRACE_ID>.json
```

若只有一个 span 的 run id，可用 seed run + `--entire-trace`，见 langsmith-download-run skill。

### D. 客户端传输与复测

- `post_turn` 线程侧超时：`INTY_V2_BACKEND_WS_POST_TURN_TIMEOUT_SEC`（默认 `180`，范围 clamp），见 [`backend_chat_ws.py`](../../../tools/inty_v2_repl/backend_chat_ws.py) `default_post_turn_thread_timeout_sec`。
- 发送失败会走 `_print_send_turn_exception`（`chat-ws-error` 等）。
- 连通性复测：[`inty-server-module-verify`](../inty-server-module-verify/SKILL.md)、[`scripts/inty_backend_smoke_tests/test_chat_ws.py`](../../../scripts/inty_backend_smoke_tests/test_chat_ws.py)。

## 按 `user_msg_uuid` 扫 LangSmith（仓库根 + venv）

脚本：[scripts/langsmith_find_companion_run_by_user_msg_uuid.py](../../../scripts/langsmith_find_companion_run_by_user_msg_uuid.py)。`--window-start-utc` 为 **UTC** ISO8601，应略早于 REPL `user-input` 对应时刻（并考虑 `post_turn` 延迟）。可选 `--project-name` 覆盖 `LANGSMITH_PROJECT`，`--config` 指向非默认 `config.yaml`。

```bash
cd /path/to/inty/repo/root
source .venv/bin/activate
python3 scripts/langsmith_find_companion_run_by_user_msg_uuid.py \
  --user-msg-uuid 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' \
  --window-start-utc '2026-05-11T10:30:00+00:00'
```

## 结论表（Agent 速查）

| 日志覆盖事发 | LangSmith | REPL | 下一步 |
|--------------|-----------|------|--------|
| 否 | （任意） | 无 error | 换当晚真实日志或让用户重载带 `--log-file` 的 Ops；勿从旧文件推断。 |
| 是 | 对应 UUID 根 + chat **pending** | 无下行 | 查同一时段 Ops 是否 **reload / crash / OOM**；查上游 LLM / OpenRouter 超时；必要时复现并抓文件 DEBUG 日志。 |
| 是 | **无** run | 无 error | 核对 **project / API key**、`agent.langsmith_tracing_enabled`；确认消息是否送达（smoke / `post_turn` 是否抛错）。 |
| 是 | success | 无下行 | 查客户端解析/队列（罕见）；对照「sideband 是否仍在轮询」与下行帧是否非标准 JSON。 |
| （任意） | （任意） | **`chat-ws-error`** | 先读 error `code`/`message`；再决定是否查服务端限流、鉴权、业务错误帧。 |

## See also

- [`inty-local-backend-repl`](../inty-local-backend-repl/SKILL.md) — 起 Ops + REPL、默认日志路径。
- [`langsmith-download-run`](../langsmith-download-run/SKILL.md) — 下载单 run / 全 trace。
- [`inty-server-module-verify`](../inty-server-module-verify/SKILL.md) — WebSocket smoke。
- [`docs/agentic_kernel/ARCH.md`](../../../docs/agentic_kernel/ARCH.md) — WebSocket、`run_turn` 链路。
- [`app/core/agentic_kernel/companion/llm_chat_runtime.py`](../../../app/core/agentic_kernel/companion/llm_chat_runtime.py) — companion LangSmith parent run；`inputs` 含 `user_msg_uuid`、`inty_trace_id`。

## 实现边界

- 技能 Markdown **不**改服务端或 REPL 实现；LangSmith 扫描由仓库 [`scripts/langsmith_find_companion_run_by_user_msg_uuid.py`](../../../scripts/langsmith_find_companion_run_by_user_msg_uuid.py) 承担（仓库根 venv 需已安装 `langsmith` / `PyYAML`，与 `requirements.txt` 一致）。
- **不要**在 Markdown 中粘贴 `config.yaml` 密钥；用本地配置或环境变量。
