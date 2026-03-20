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
- Context messages are appended in stack order from deepest to shallowest before conversation turns.

Conversation can be compacted into a new named layer using:

- `compact_recent_conversation_into_layer(layer_name, layer_content, recent_message_count)`

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

```bash
export TELEGRAM_BOT_TOKEN="<your-bot-token>"

python -m experimental.perpetual_agent.main \
  --mode living \
  --telegram \
  --telegram-chat-id "<chat-id>" \
  --telegram-max-user-turns 50 \
  --proactive-interval-seconds 120
```

Notes:

- If `--telegram-chat-id` is omitted, the first incoming chat message becomes the bound chat.
- You can set `TELEGRAM_CHAT_ID` in env instead of passing `--telegram-chat-id`.
- In Telegram mode, the companion's default outbound channel is `telegram`.

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
