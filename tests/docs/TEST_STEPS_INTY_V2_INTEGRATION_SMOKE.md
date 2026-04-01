# TEST_STEPS_INTY_V2_INTEGRATION_SMOKE

## Goal

Validate Phase 0 integration baseline for `experimental/inty_v2_text_chat_prototype`:

- integration contracts are fixed
- `run_turn` remains the single assistant transcript write entry
- prompt assembly and heartbeat semantics have no regressions

## Preconditions

- Run from repository root.
- Activate project venv:

`source .venv/bin/activate`

## Phase 0 Gate Commands

Run exactly:

1) `pytest -q experimental/inty_v2_text_chat_prototype/tests/test_transcript_for_llm_turn.py`
2) `pytest -q experimental/inty_v2_text_chat_prototype/tests/test_heartbeat_schedule.py`
3) `pytest -q experimental/inty_v2_text_chat_prototype/tests/test_workspace_bootstrap_loop.py`

## Pass Criteria

- All three commands pass.
- No change is needed in:
  - required workspace files contract (`IDENTITY.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `transcript.jsonl`)
  - heartbeat synthetic turn behavior
  - transcript schema expectations used by test fixtures

## Manual Spot Check (optional)

1) Run:

`python -m experimental.inty_v2_text_chat_prototype.main once --workspace experimental/inty_v2_text_chat_prototype/_ws --message "hello"`

2) Confirm:

- output returns assistant text
- `experimental/inty_v2_text_chat_prototype/_ws/transcript.jsonl` appends one user row and one assistant row

