# Perpetual Agent Demo

This directory now contains **two** perpetual-agent prototypes:

1. `pulse` mode: original single-tool loop demo.
2. `living` mode: a virtual AI companion that orchestrates different model tiers, proactively reaches out over multiple channels, adapts expression from emotional cues, and ages using a configurable virtual clock ratio.

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

## Run pulse mode

```bash
python -m experimental.perpetual_agent.main \
  --mode pulse \
  --user-prompt "Run in a loop. Use pulse." \
  --model "z-ai/glm-4.5-air:free" \
  --max-steps 5
```

Pulse mode requires:

- `OPENROUTER_API_KEY` in environment (or pass a different `--api-key-env`)
- OpenAI-compatible endpoint (default: OpenRouter)
