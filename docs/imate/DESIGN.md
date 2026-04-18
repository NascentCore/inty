# iMate companion design (kernel)

## Routing

- HTTP `chat/completions`: legacy `Agent.chat`.
- WebSocket `chat/ws`: `companion_chat_service` -> `CompanionManager` -> `companion.turn.run_turn`. Authority: `MemoryStore` (ORM-backed docs + `transcript.jsonl`); product chat rows: `chat_history_service`.

## Turn

- Assemble system from prompt slices (`PromptBundle`) + transcript window + optional compaction.
- LLM: `CompanionLLMClient` (OpenAI-compatible); tool loop calls `companion_tool_runtime.execute_tool_call` (schemas in `tools.py`).
- Post-turn: memory pipeline enqueue/sync per config.

## Dual LLM

- When enabled: separate chat vs tool model routes; tool branch may run sync or async (async chat foreground + background tool loop).
- Chat branch may use tools mirrored with `tool_choice=none` for context parity without calling tools from chat.

## Significance perception

- Prompt slice `SIGNIFICANCE_PERCEPTION` + optional structured envelope on the **chat** branch when that branch is non-tool (`response_format` JSON schema).
- Fields: `user_facing_reply`, `importance_round`, `importance_user_message`, `importance_assistant_message` (1-10).
- Assistant transcript row may carry `significance_perception`; WebSocket path may mirror into `chat_history.meta_data` for downstream jobs.

## Memory extraction (optional)

- Config `memory_extraction.use_significance_perception_in_extraction`: when true, sort turns by `importance_round`, annotate prompt lines with scores, add a short English hint block to extraction prompts. Default off.

## Naming

- `companion_tool_runtime.py`: companion tool schemas + execution (not only filesystem I/O).

## REPL

- `tools/inty_v2_repl`: local harness; imports `inty_v2_repl.*` with `tools/` on `sys.path` (`tests/conftest.py`).
