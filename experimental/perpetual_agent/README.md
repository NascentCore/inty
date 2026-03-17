# Perpetual Agent Demo

Minimal perpetual agent demo with one tool: `pulse`.

## Behavior

1. The agent runs in a loop (`max_steps` for demo safety).
2. If the model calls `pulse(seconds)`, the tool:
   - sleeps for `seconds`
   - increments a pulse counter
   - returns control to the prompt loop
3. The pulse counter is injected into the system message on every step.

## Run

From repo root:

```bash
python -m experimental.perpetual_agent.main \
  --user-prompt "Run in a loop. Use pulse." \
  --model "z-ai/glm-4.5-air:free" \
  --max-steps 5
```

Requires:

- `OPENROUTER_API_KEY` in environment (or pass a different `--api-key-env`)
- OpenAI-compatible endpoint (default: OpenRouter)
