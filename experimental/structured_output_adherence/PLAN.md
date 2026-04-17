# Structured output adherence experiment (IntelliMate production chat replay)

## Goal

Quantify how reliably an LLM follows a fixed JSON shape when asked to infer a **conversational scenario** from chat context, using **real chat_history rows** from IntelliMate production (read-only). The scenario is a synthetic label for analysis, not user-facing copy.

## Definitions

- **Turn**: one row in `chat_history` for a given `session_id`, ordered by `created_at`, excluding `deleted_at IS NOT NULL`.
- **Replay**: for turn index `t`, build context from turns `0..t-1` (empty at `t=0`), call the model once, record pass/fail and token usage.
- **Structure adherence (primary)**: fraction of calls where the assistant message is valid JSON and passes `ConversationScenario.model_validate_json(content)` (Pydantic v2).
- **JSON validity (secondary)**: fraction where `json.loads` succeeds regardless of schema.

## Data source

- Table: `chat_history` (`session_id` UUID, `message` JSONB, `created_at`, `deleted_at`).
- `session_id` is derived from `chats.id` the same way as production: `uuid.uuid5(uuid.NAMESPACE_DNS, chat_id)` (string form).
- Prefer a **replica** DSN if your operator provides `database.async_replica_url` mapped to sync `postgresql://...`; otherwise use the read-only user on primary. Never run writes from this experiment.

## Sampling strategy (recommended)

1. Pick `N` active `chats.id` with at least `M` non-deleted history rows in a date window (CLI: `--since`, `--until`, `--min-rows`).
2. Cap turns per chat with `--max-turns-per-chat` to bound cost.
3. Optional: `--stride k` to only evaluate every k-th turn after the first.

## Model and API

- OpenAI-compatible Chat Completions (default: OpenRouter) with `response_format` set to JSON schema strict mode when the provider supports it; script falls back to `{"type": "json_object"}` if strict schema fails at runtime.
- Credentials: `OPENROUTER_API_KEY` or `OPENAI_API_KEY` plus `--base-url` (see README).

## Outputs

- **JSONL** per run: one line per evaluated turn with `chat_id`, `turn_index`, `ok`, `error`, `prompt_tokens`, `completion_tokens`, `latency_ms`, and a short `raw_head` preview on failure.
- **Summary JSON**: aggregate rates, counts, and optional histogram of failure reasons.

## Ethics and compliance

- Treat message text as **user data**: do not commit exports; restrict access to result files; redact or hash `user_id` in any report you share outside the trust boundary.
- This directory only contains code and local fixtures; no production dumps.

## Extensions (not implemented here)

- Multi-model comparison (same sample, different `--model`).
- Temperature sweep.
- Constrained decoding providers (e.g. outlines, guidance) vs plain `response_format`.
