# Perpetual Agent Demo

This directory now contains **two** perpetual-agent prototypes:

1. `pulse` mode: perpetual loop demo with `pulse` and `call_user` tools.
2. `living` mode: a virtual AI companion that orchestrates different model tiers, proactively reaches out over multiple channels, adapts expression from emotional cues, and ages using a configurable virtual clock ratio.

## Pulse mode behavior

1. The agent runs in a loop (`max_steps` for demo safety).
2. If the model calls `pulse(seconds)`, the tool:
   - sleeps for `seconds`
   - increments a pulse counter
   - returns control to the prompt loop
3. If the user says `call me at <number>`, the first step forces `call_user(phone_number, reason)`.
4. `call_user` places an outbound Twilio call and injects TwiML `<Connect><Stream ... /></Connect>` to bridge call audio to your Gemini Live bridge websocket.
5. The pulse counter is injected into the system message on every step.

## Living companion behavior

`living` mode simulates:

- **Model orchestration**:
  - Fast tier for routine text turns.
  - Reasoning tier for analysis-heavy turns.
  - Multimodal tier for voice-call style interactions.
- **Proactive communication** via channel abstraction:
  - `email`
  - `sms`
  - `voice_call`
- **Emotion-driven expression**:
  - Emotional cues in user text update the companion emotion and outward expression.
- **Virtual aging**:
  - `clock_rate=10` means the companion ages 10x faster than world time.
  - `clock_rate=0.1` means aging is slowed to 0.1x.

## Character layer stack (pulse mode context architecture)

`pulse` mode now builds context using a **deep-to-shallow character layer stack**:

1. `fundamental_identity` (deepest, stable role/values)
2. `interaction_style` (middle, interaction strategy)
3. `conversation` (shallowest, always present)

Rules:

- Every non-conversation layer gets a dedicated update tool:
  - `update_layer_fundamental_identity`
  - `update_layer_interaction_style`
- The shallow `conversation` layer has **no** update tool.
- If a layer is renamed via its update tool (`rename_to`), the update tool name changes on the next turn.
- Layer names must be unique after normalization (e.g. `interaction style` collides with `interaction_style`).
- Context messages are appended in stack order from deepest to shallowest before conversation turns.
- Conversation compaction only applies to messages strictly older than the current assistant tool-call envelope.
- Every layer carries `nesting_level` (initial layers are level `0`).
- Compaction records raw source messages in layer state for observability.
- To avoid context bloat, conversation tool messages only keep raw-message counts, not full raw payloads.

Conversation can be compacted into a new named layer using:

- `compact_recent_conversation_into_layer(layer_name, layer_content, recent_message_count)`
- This compacts raw conversation messages (level `0`) into a new layer with level `1`.

Named layers can also be compacted hierarchically:

- `compact_named_layers_into_layer(layer_name, layer_content, source_layer_names)`
- All source layers must share the same `nesting_level`.
- Source layers must be contiguous in current stack order.
- The merged layer gets `nesting_level = source_level + 1`.

Compaction inserts a new layer immediately above `conversation`, making the stack behave like a Turing-style memory tape/stack where recent turns can be condensed into reusable titled memory layers.

## Run living mode (default)

From repo root:

```bash
python -m experimental.perpetual_agent.main \
  --mode living \
  --clock-rate 10 \
  --initial-virtual-age-years 2 \
  --user-message "I feel lonely tonight. Can you text me?" \
  --user-message "Please call me and help me think through tomorrow." \
  --user-message "Email me a reflective summary."
```

Useful flags:

- `--proactive-interval-seconds`: idle interval before autonomous outreach
- `--tick-seconds`: simulated world-time elapsed between user turns
- `--user-contact`: destination string used by the channel transport

## Run living mode via Telegram

This mode lets the perpetual companion receive user text from Telegram and reply in the same chat.

### Verify the bot token (before the demo loop)

Confirm BotFather token and bot identity with a single HTTP call ([`getMe`](https://core.telegram.org/bots/api#getme)):

```bash
curl -sS "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"
```

Expect `"ok":true` and `result.username` matching your bot. This does not start long polling; it only proves the token is valid.

### Start the living companion (Telegram)

From repo root (with [`uv`](https://github.com/astral-sh/uv) or plain `python`):

```bash
export TELEGRAM_BOT_TOKEN="<your-bot-token>"

uv run python -m experimental.perpetual_agent.main \
  --mode living \
  --telegram \
  --telegram-max-user-turns 50 \
  --telegram-poll-timeout-seconds 20 \
  --proactive-interval-seconds 120
```

Optional: pin the chat when you already know the numeric chat id (see troubleshooting below):

```bash
python -m experimental.perpetual_agent.main \
  --mode living \
  --telegram \
  --telegram-chat-id "<chat-id>" \
  --telegram-max-user-turns 50 \
  --proactive-interval-seconds 120
```

Notes:

- **Process must stay running** while you chat in Telegram. If the process exits (traceback or Ctrl+C), the bot will stop replying even though Telegram shows delivered checkmarks on your outgoing messages.
- If `--telegram-chat-id` is omitted **and** `TELEGRAM_CHAT_ID` is unset, the **first incoming text message** sets the bound chat (`getUpdates` → `message.chat.id`). Good for a single-user local smoke test.
- You can set `TELEGRAM_CHAT_ID` in env instead of passing `--telegram-chat-id`.
- In Telegram mode, the companion's default outbound channel is `telegram`.
- Replies in this demo use `ScriptedModelExecutor`: they echo metadata plus `I heard you: <text>` (not a live LLM).
- **Latency logging:** Telegram mode enables `logging.basicConfig(level=INFO)` when the root logger has no handlers. Each handled user text turn logs `telegram_latency` with `receive_to_reply_s` (seconds from finishing `getUpdates` parse for that update until `sendMessage` completes for the reply) and `telegram_message_date_to_local_receive_s` (Telegram `message.date` → same local receive moment; approximates how long the update waited before your process polled it, or `n/a` if `date` was missing).

### Telegram + OpenAI (inbound channel / LLM chat)

Use **`--telegram-llm`** instead of `--telegram` when you want a real chat model (OpenAI-compatible API). Do **not** pass both flags.

Architecture (see [`channel_inbox.py`](channel_inbox.py) and [`telegram_agentic_loop.py`](telegram_agentic_loop.py)):

- **Inbound:** [`TelegramInbox`](channel_inbox.py) long-polls `getUpdates`, advances Telegram’s `offset`, and tracks `last_applied_update_id`. New text updates for the bound chat are appended to the shared LLM `messages` list (merged into one user message per poll by default).
- **Agentic loop:** Before **every** `chat.completions.create` call, the loop drains the inbox again (with **short polling**, `timeout=0`) so queued updates that arrived during tool execution are merged without an extra long-poll wait. The outer `run_telegram_llm_session` loop still long-polls with `--telegram-poll-timeout-seconds` while waiting for the next user batch.
- **Latency logs (INFO):** `telegram_get_updates` (per drain: requested `poll_timeout_s`, `elapsed_ms`, offsets) and `telegram_llm phase_timing` (`drain_wall_ms`, `openai_completion_ms`, `send_message_ms`) for each completion step.
- **Outbound:** Final assistant text is sent with `sendMessage` to the same bound `chat_id`.

```bash
export TELEGRAM_BOT_TOKEN="..."
export OPENROUTER_API_KEY="..."   # or your provider

uv run python -m experimental.perpetual_agent.main \
  --mode living \
  --telegram-llm \
  --model "your-model-id" \
  --telegram-llm-max-user-turns 50 \
  --telegram-poll-timeout-seconds 20
```

Optional: `--telegram-llm-pulse-tool` registers a minimal `pulse(seconds)` tool; `--telegram-llm-no-merge-batches` appends one user message per Telegram update instead of merging.

**Operational constraints:**

- **Single long-poll consumer:** Only one running process (or webhook endpoint) may consume updates for a bot token. A second `getUpdates` client causes conflicts (often HTTP 409); do not run scripted `--telegram` and `--telegram-llm` at the same time, or two copies of either mode.
- **Cursor / loss:** `last_applied_update_id` advances only when inbound text is merged into the LLM transcript. Telegram’s `offset` advances on each successful `getUpdates` response so the server does not redeliver the same updates; do not run a second poller that steals updates before this process applies them.
- **Multi-message policy:** With merge enabled (default), all new text updates in one poll become a single `user` message with labeled lines; the model should treat them as one turn batch.

Useful Telegram flags (see `python -m experimental.perpetual_agent.main --help`):

- `--telegram-poll-timeout-seconds`: long-poll wait for `getUpdates`
- `--telegram-max-user-turns`: exit after this many handled user messages (raise for long demos)
- `--telegram-bot-token-env`: env var name for the token (default `TELEGRAM_BOT_TOKEN`)
- `--telegram-llm` / `--telegram-llm-max-user-turns` / `--telegram-llm-no-merge-batches` / `--telegram-llm-pulse-tool`: OpenAI path (see section above)

### Troubleshooting

1. **`urllib.error.HTTPError: HTTP Error 400: Bad Request` on `sendMessage`**  
   Often an **invalid or mismatched `chat_id`**. If `TELEGRAM_CHAT_ID` / `--telegram-chat-id` is **wrong** (typo, placeholder, or another user’s id), the loop **drops your real messages** (`incoming.chat_id != current_chat_id`) and may still run **proactive** sends to the wrong id → 400. **Fix:** `unset TELEGRAM_CHAT_ID` and omit `--telegram-chat-id`, restart, then send one message from the intended Telegram account so the chat binds correctly; or set the env/flag to the exact numeric id from `getUpdates` / `@userinfobot`.

2. **No reply but double checkmarks on your messages**  
   That only means Telegram accepted the message—not that this Python process received it or called `sendMessage` successfully.

3. **Token security**  
   Treat `TELEGRAM_BOT_TOKEN` like a password; rotate it in BotFather if it leaks. Do not commit it to git.

### Known issues / observations (recorded, not fixed yet)

- Reliability risk (medium): Telegram transient API/network failures currently bubble up as exceptions and can terminate the loop. This is recorded for later hardening; no retry/recovery behavior is implemented yet.
- Test coverage gap (low): The documented "omit `--telegram-chat-id` and auto-bind to first incoming chat" behavior exists in code, but does not yet have a dedicated automated test case. This is recorded only; coverage may be reworked together with upcoming behavior changes.

## Run pulse mode

```bash
python -m experimental.perpetual_agent.main \
  --mode pulse \
  --user-prompt "Run in a loop. Use pulse." \
  --model "z-ai/glm-4.5-air:free" \
  --max-steps 5
```

Pulse mode requires:

Call-flow demo prompt:

```bash
python -m experimental.perpetual_agent.main \
  --mode pulse \
  --user-prompt "Call me at +14155550123 and check in on me." \
  --model "z-ai/glm-4.5-air:free" \
  --max-steps 1
```

- `OPENROUTER_API_KEY` in environment (or pass a different `--api-key-env`)
- OpenAI-compatible endpoint (default: OpenRouter)
- For `call_user`:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_PHONE_NUMBER` (Twilio caller ID)
  - `GEMINI_LIVE_BRIDGE_WS_URL` (your websocket service that forwards Twilio Media Stream audio to Gemini Live API)
  - optional `GEMINI_LIVE_CALL_SYSTEM_PROMPT` (sent as a Twilio stream parameter)
