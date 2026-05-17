# Wire → Turn → Persistence：会话数据分层

## 范围

本文用三层模型归纳 **伴侣 WebSocket 聊天** 上各类输入/输出的归属：传输帧、回合信封、持久化落点。适用于讨论「某事件会不会进 transcript」「和 `chat_history` 是否一致」「lifecycle 事件落在哪」等架构问题。

**在范围内**：生产路径 `/api/v1/chat/ws` 上的控制帧、用户消息、MemoryStore 轨迹、`chat_history` 镜像。

**不在范围内**：Gemini Live 音频、legacy 非 companion 聊天、Ops 专用表；字段级协议真源仍以 `app/schemas/chat_websocket.py` 与端点实现为准。

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

**注意**：`transcript.jsonl` 只是 **D** 的主轨；完整 Inty 侧轨迹还需 **D 副轨 + E（自我轨迹）+ F**，客户端时间线看 **G**。

---

## 用语：Messages vs structured logs

| 用语 | 定义 | 例子 |
|------|------|------|
| **Messages（消息）** | 有 role + 内容，进入对话语义或 UI 历史 | C：`chat_history`；D：transcript 的 user/assistant（含 synthetic user） |
| **Control frames（控制帧）** | WS JSON 信封，多数不持久化为 message | A：`ping`、`user_signed_on`、`*_ack` |
| **Turn metadata（回合元数据）** | 附着在一次 completion / `run_turn` 上，不单独成「一句用户话」 | B：`ImplicitSignalBundle`、`UserTimeContext` |
| **Structured logs（结构化日志）** | 追加一行/一条 JSONL，审计或排障；属 **E 自我轨迹** | `runtime_events` 的 `kind`+`ts`（含 WS lifecycle 与 LLM/工具失败） |

---

## WS lifecycle → `.companion_runtime_events.jsonl`（E，不是 B）

**写入方**：成功 ack 路径上的 `user_signed_on`、`user_signed_out`、`ws_conn_dropped`。

**格式**：每事件一条 JSON（`kind` 为 `user_signed_on` / `user_signed_out` / `ws_conn_dropped`）；`ts` 为 **用户本地墙钟**（优先 `client_context` 的 `local_time`；drop 可在无 `local_time` 时用 `dropped_at_utc`+时区换算）。另含 `timezone`、`user_id`、`chat_id`、`agent_id`、`received_message_uuid`、`ws_conn_id`；drop 另有 `ws_close_code` / `ws_close_reason`。

**不写入**：`ping`、`client_context`、各 `ack`；校验失败的 lifecycle 帧。

**与 B 的区别**：B 在 `tc_box` 内存中消费；lifecycle 行是 **跨连接追加的 JSONL 审计**，默认不进 LLM 对话窗口。

**与 D 的关系**：`user_signed_on` 仍触发问候 → D（synthetic user + assistant）与 G（仅 assistant）。是否已问候看 transcript：**是否存在 `assistant.reply_to == sign-on message_id`**，不在 lifecycle 行里重复记录。

**前置**：客户端宜在 lifecycle 帧之前发送 `client_context`；无本地 `ts` 时服务端跳过 append 但仍 ack。

---

## 控制帧 → 回合元数据（A → B，分事件）

同一 WS 事件在三层可有 **0 / 1 / 多条** 持久化记录；**不是**所有 A 都会变成 B，也 **不是** B 的 duplicate。

| WS 事件（A） | Turn 层（B/C） | 典型 Persistence |
|--------------|----------------|------------------|
| `ping` / `pong` / `*_ack` | 无 | 0 |
| `client_context` | `tc_box` → 后续 turn 的 `UserTimeContext`（B） | 0（帧本身不落库） |
| `user_signed_on` | RAM `heartbeat_context`；问候轮 `ImplicitSignalBundle.user_signed_on`（B） | E：1× lifecycle JSONL；D：synthetic user + assistant；G：仅 assistant |
| `user_signed_out` | 无 B | E：1× lifecycle JSONL；0×D |
| `ws_conn_dropped` | 无 B | E：1× lifecycle JSONL；0×D |
| 用户 `chat` 帧（C） | C + B（时间等） | G + D |
| 服务端 `inner_tick` | 无 Wire | D 或 `transcript_inner_tick.jsonl` |
| LLM/工具失败 | 无 Wire | E：`runtime_events.jsonl`（failure kind） |

**`ChatMessage.presence`（`repl_online` / `repl_offline`）**：transcript 上的预留字段 + 尾部剥离逻辑；**生产 WS 主路径未写入**，与 `user_signed_on/out` 不是同一机制。

---

## ASCII：三层总览

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
