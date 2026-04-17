# Structured output adherence (chat replay)

See [PLAN.md](PLAN.md) for the full experiment design.

## Prerequisites

- Python 3.12+ with repo venv activated.
- Network access to your OpenAI-compatible API.
- Read-only PostgreSQL access to IntelliMate `chat_history` (and optional `chats` for discovery queries).

## Configure

Copy `.env.example` to `.env` in this folder or set variables in the shell:

- `OPENROUTER_API_KEY` (or `OPENAI_API_KEY`)
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (or pass `--database-url`)

## Dry run (no DB, no API)

Uses bundled sample lines:

```bash
cd /workspace
source .venv/bin/activate
python experimental/structured_output_adherence/run_experiment.py \
  --fixture experimental/structured_output_adherence/fixtures/sample_turns.jsonl \
  --dry-run \
  --max-turns-per-chat 3 \
  --out-dir /tmp/soa_dry
```

## Production replay (sample chats)

From repo root (loads `config.yaml` database section if present, same pattern as `experimental/user_analytics`):

```bash
cd /workspace
source .venv/bin/activate
set -a && [ -f experimental/structured_output_adherence/.env ] && . experimental/structured_output_adherence/.env && set +a
python experimental/structured_output_adherence/run_experiment.py \
  --sample-chats 5 \
  --min-rows 8 \
  --max-turns-per-chat 12 \
  --model openai/gpt-4o-mini \
  --out-dir /tmp/soa_run
```

Adjust `--since` / `--until` (ISO dates, UTC) to limit rows scanned.

## Artifacts

- `<out-dir>/turns.jsonl` - one record per model call.
- `<out-dir>/summary.json` - aggregate metrics.
