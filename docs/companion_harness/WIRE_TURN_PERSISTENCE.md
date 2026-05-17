# Wire → Turn → Persistence：会话数据分层

## 范围

三层模型归纳 **伴侣 WebSocket 聊天** 上输入/输出的归属：传输帧（Wire）、回合信封（Turn）、持久化落点（Persistence）。用于讨论「某事件会不会进 transcript」「和 `chat_history` 是否一致」「lifecycle 事件落在哪」等。

- **在范围内**：`/api/v1/chat/ws` 控制帧、用户消息、MemoryStore 轨迹、`chat_history` 镜像。
- **不在范围内**：Gemini Live、legacy 非 companion、Ops 专用表；字段级协议真源见 `app/schemas/chat_websocket.py` 与端点实现。

**See also**：[ARCH.md](ARCH.md) · [MEMORY_STORE.md](MEMORY_STORE.md) · [GLOSSARY.md](GLOSSARY.md)

---

## 七类概念（A–G）

| 类 | 名称 | 含义 |
|----|------|------|
| **A** | 传输 / 会话控制 | WS 等控制帧：`ping`、`client_context`、`user_signed_on/out`、`ws_conn_dropped` 及各类 `*_ack`；多数不直接写入 transcript |
| **B** | 客户端伴生元数据 | 随用户轮或特殊轮附带、**非用户正文**：`UserTimeContext`、`ImplicitSignalBundle`、`localId`、app version 等 |
| **C** | 用户意图消息 | 用户故意发送的文本/图/语音等 → `chat_history` +（companion 时）transcript |
| **D** | Agent 对话轨迹 | MemoryStore JSONL，供 LLM：`transcript.jsonl`、`transcript_inner_tick.jsonl`；含 synthetic user（sign-on trigger、heartbeat marker） |
| **E** | 自我轨迹 | Inty 侧非用户可见对白的持续记录：`ai_private*`、`.companion_runtime_events.jsonl` |
| **F** | Agent 状态与记忆 | `IDENTITY`/`SOUL`/…、`context.json`、压实/schedule 快照等（非逐轮 log） |
| **G** | 客户端可见历史 | 产品 API 的 `chat_history`（应与 D 语义对齐，结构不同） |

`transcript.jsonl` 只是 **D** 主轨；完整 Inty 侧轨迹 = **D（含 inner_tick 副轨）+ E + F**；客户端时间线看 **G**。

---

## 四类用语

- **Messages（消息）** — 有 role + 内容，进入对话语义或 UI 历史。例：C `chat_history`；D transcript user/assistant（含 synthetic user）。
- **Control frames（控制帧）** — WS JSON 信封，多数不持久化为 message。例：A `ping`、`user_signed_on`、`*_ack`。
- **Turn metadata（回合元数据）** — 附着在一次 completion / `run_turn`，不单独成「一句用户话」。例：B `ImplicitSignalBundle`、`UserTimeContext`。
- **Structured logs（结构化日志）** — 追加一行/一条 JSONL，审计或排障；属 **E**。例：`runtime_events` 的 `kind`+`ts`（WS lifecycle 与 LLM/工具失败）。

---

## 事件 → Turn → Persistence

同一 WS 事件在三层可有 **0 / 1 / 多条** 持久化记录；**不是**所有 A 都会变成 B，也 **不是** B 的 duplicate。

| WS 事件（A） | Turn 层（B/C） | 典型 Persistence |
|--------------|----------------|------------------|
| `ping` / `pong` / `*_ack` | 无 | 0 |
| `client_context` | `tc_box` → 后续 turn 的 `UserTimeContext`（B） | 0（帧本身不落库）；**后续轮**可在 prompt/meta 用时间 |
| `user_signed_on` | RAM `heartbeat_context`；问候轮 `ImplicitSignalBundle.user_signed_on`（B） | E：1× lifecycle JSONL；D：synthetic user + assistant；**G：仅 assistant（无 user 行）** |
| `user_signed_out` | 无 B | E：1× lifecycle JSONL；0×D |
| `ws_conn_dropped` | 无 B | E：1× lifecycle JSONL；0×D |
| 用户 `chat` 帧（C） | C + B（时间等） | G + D；**可选** 经 tools / memory pipeline 更新 **F** |
| 服务端 `inner_tick` | 无 Wire | D 或 `transcript_inner_tick.jsonl`；**不进** public chat LLM 窗口 |
| LLM/工具失败 | 无 Wire | E：`runtime_events.jsonl`（failure kind）；**另** loguru 服务端日志（ops，非 MemoryStore） |

**`ChatMessage.presence`（`repl_online` / `repl_offline`）**：transcript 上的预留字段 + 尾部剥离逻辑；**生产 WS 主路径未写入**，与 `user_signed_on/out` 不是同一机制。

**`.companion_runtime_events.jsonl`（WS lifecycle，E）**：成功 ack 路径写入 `user_signed_on` / `user_signed_out` / `ws_conn_dropped`（`kind` + **用户本地墙钟** `ts`，优先 `client_context.local_time`；drop 可无 `local_time` 时用 `dropped_at_utc`+时区）。另含 `timezone`、`user_id`、`chat_id`、`agent_id`、`received_message_uuid`、`ws_conn_id`；drop 另有 `ws_close_code` / `ws_close_reason`。**不写入**：`ping`、`client_context`、各 `ack`、校验失败的 lifecycle 帧。与 **B**：B 在 `tc_box` 内存消费；lifecycle 行跨连接 JSONL 审计，默认不进 LLM。`user_signed_on` 仍走问候 → D/G；是否已问候看 transcript **`assistant.reply_to == sign-on message_id`**，不在 lifecycle 行重复。客户端宜在 lifecycle 前发 `client_context`；无本地 `ts` 时跳过 append 仍 ack。

---

## ASCII：三层总览

纯文本图：在 Git、IDE、飞书/Notion 粘贴与 diff 里均可读，不依赖 Mermaid 渲染。与上表互补——上表查落点，下图看端到端帧流、三层布局与同事件多落点。

```
                    Inty: Wire → Turn → Persistence
                    Wire: WS 传输与控制帧（A），多数不直接持久化。
                    Turn: 单次 completion / run_turn 的内存信封与连接态（B/C）。
                    Persistence: 跨重连落库的轨迹、历史、审计与状态文档（D/E/F/G）
                    =================================================
                    

  LAYER 1: WIRE (A)                    WS / transport — mostly ephemeral
  ─────────────────
       Client                                                          Server
         │                                                               │
         │  ping ───────────────────────────────────────────────────────►│ pong
         │  client_context ─────────────────────────────────────────────►│ client_context_ack
         │  user_signed_on ─────────────────────────────────────────────►│ user_signed_on_ack
         │  user_signed_out ────────────────────────────────────────────►│ user_signed_out_ack
         │  ws_conn_dropped ────────────────────────────────────────────►│ ws_conn_dropped_ack
         │  chat (user text / image / …) ───────────────────────────────►│ completion frames
         │                                                               │
         │                              (acks & ping: no persistence)    │


  LAYER 2: TURN ENVELOPE (B / C)       In-memory + per-turn
  ──────────────────────────────
       ┌─────────────────────────────────────────────────────────────────┐
       │  Connection state (WS lifetime)                                 │
       │    tc_box[0]  ←── client_context  →  UserTimeContext (B)        │
       │    heartbeat_context ←── user_signed_on  (inner-tick coords)    │
       └─────────────────────────────────────────────────────────────────┘
       ┌─────────────────────────────────────────────────────────────────┐
       │  Per completion / run_turn                                      │
       │    C  user-authored: messages[], message_id, localId, parts…    │
       │    B  bundled with turn: ImplicitSignalBundle                   │
       │         • client_time (from tc_box or request)                  │
       │         • user_signed_on=true  (greeting turn only)             │
       │    synthetic user line in prompt (sign-on trigger, heartbeat)   │
       └─────────────────────────────────────────────────────────────────┘


  LAYER 3: PERSISTENCE (D / E / F / G)   Postgres / MemoryStore — survives reconnect
  ────────────────────────────────────

       G chat_history          C user rows + assistant rows (product UI / API)
       │                       │
       │    companion path     │
       └──────────┬────────────┘
                  │
       D transcript.jsonl      user/assistant JSONL (LLM main track)
       D transcript_inner_tick.jsonl   maintenance inner-tick only
       │
       E runtime_events.jsonl   WS lifecycle + llm/tool failures (JSONL)
       E ai_private.jsonl / .md   inner activity (not user chat)
       │
       F IDENTITY/SOUL/USER/MEMORY, context.json, .companion_* snapshots, …


  SAME EVENT → DIFFERENT PERSISTENCE COUNTS (examples)
  ───────────────────────────────────────────────────

  ping                    Wire ──► (no persistence)

  client_context          Wire ──► B in tc_box ──► (0 direct persist of frame;
                              later turns may use time in prompts / meta)

  user_signed_on          Wire ──► heartbeat_context (RAM)
                          └──► greeting turn: B(user_signed_on)
                          └──► D: synthetic user + assistant greeting
                          └──► G: assistant only (no user chat_history row)
                          └──► E: 1 lifecycle JSONL (local ts)

  user_signed_out         Wire ──► E: 1 lifecycle JSONL
                          └──► (0 × B, 0 × D transcript row)

  ws_conn_dropped         Wire ──► E: 1 lifecycle JSONL
                          └──► (0 × B, 0 × D)

  user chat message       Wire ──► C + B(time, …)
                          └──► G: user + assistant
                          └──► D: user + assistant JSONL
                          └──► (optional F via tools / memory pipeline later)

  inner_tick (server)   (no Wire) ──► D or D_inner only
                          └──► filtered out of public chat LLM window

  LLM / tool failure    (runtime) ──► E: runtime_events.jsonl (failure kind)
                          └──► loguru server logs (ops, not MemoryStore)


  FLOW SUMMARY (left → right)
  ───────────────────────────

    [ Client ]     A: Wire frames          B/C: Turn envelope        D/E/F/G: Persist
        │                 │                         │                         │
        │── ping ────────►│                         │                         │
        │── context ─────►├── tc_box (B) ──────────►│                         │
        │── signed_on ───►├── RAM coords ──────────►│                         │
        │                 │    └── greeting turn ──►├── B + prompt ──────────►├── D,G
        │                 │                         │                         ├── E lifecycle
        │── signed_out ──►│                         │                         ├── E lifecycle
        │── dropped ─────►│                         │                         ├── E lifecycle
        │── chat ────────►├── C + B ───────────────►│                         ├── G + D
        │                 │                         │                         │
        │                 │    [ Server inner_tick ]│                         ├── D or D_inner
        │                 │                         │                         ├── F (state)
```
