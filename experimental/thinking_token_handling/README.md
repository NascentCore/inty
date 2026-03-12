# Thinking Token Handling Demo

This demo calls an LLM with high thinking mode and prints both:

1. thinking token usage (`reasoning_tokens`)
2. final response text

## File

- `demo_high_thinking.py`

## Run

```bash
cd experimental/thinking_token_handling
/workspace/.venv/bin/python demo_high_thinking.py
```

## Environment

The script loads `.env` via `python-dotenv`.

Default provider is OpenRouter (`THINKING_DEMO_PROVIDER=openrouter`), and API key is resolved in this order:

- `OPENROUTER_API_KEY`
- fallback to `config.yaml -> agent.api_key`

Optional environment variables:

- `THINKING_DEMO_MODEL` (default: `google/gemini-2.5-pro`)

## Expected output sections

- `=== Thinking Tokens ===`
- `=== Raw Usage (for verification) ===`
- `=== Thinking Content (if available) ===`
- `=== Final Response ===`
