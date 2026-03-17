# Perpetual Agent Demo

Minimal perpetual agent demo with two tools: `pulse` and `call_user`.

## Behavior

1. The agent runs in a loop (`max_steps` for demo safety).
2. If the model calls `pulse(seconds)`, the tool:
   - sleeps for `seconds`
   - increments a pulse counter
   - returns control to the prompt loop
3. If the user says `call me at <number>`, the first step forces `call_user(phone_number, reason)`.
4. `call_user` places an outbound Twilio call and injects TwiML `<Connect><Stream ... /></Connect>` to bridge call audio to your Gemini Live bridge websocket.
5. The pulse counter is injected into the system message on every step.

## Run

From repo root:

```bash
python -m experimental.perpetual_agent.main \
  --user-prompt "Run in a loop. Use pulse." \
  --model "z-ai/glm-4.5-air:free" \
  --max-steps 5
```

Call flow demo prompt:

```bash
python -m experimental.perpetual_agent.main \
  --user-prompt "Call me at +14155550123 and check in on me." \
  --model "z-ai/glm-4.5-air:free" \
  --max-steps 1
```

Requires:

- `OPENROUTER_API_KEY` in environment (or pass a different `--api-key-env`)
- OpenAI-compatible endpoint (default: OpenRouter)
- For `call_user`:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_PHONE_NUMBER` (Twilio caller ID)
  - `GEMINI_LIVE_BRIDGE_WS_URL` (your websocket service that forwards Twilio Media Stream audio to Gemini Live API)
  - optional `GEMINI_LIVE_CALL_SYSTEM_PROMPT` (sent as a Twilio stream parameter)
