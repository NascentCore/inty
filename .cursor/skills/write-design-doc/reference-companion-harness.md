# Companion Harness — DESIGN doc recon checklist

Use with [SKILL.md](SKILL.md) when the target is `docs/companion_harness/DESIGN.md` or companion architecture.

## Read order

| Step | Read | Extract |
|------|------|---------|
| 1 | [/AGENTS.md](/AGENTS.md) | 1:1 Inty, `/api/v1/chat/ws` boundary, dir allowlist |
| 2 | [app/core/companion_harness/AGENTS.md](/app/core/companion_harness/AGENTS.md) | PROTOTYPE, single presence, agent = llm+harness+memory+channels |
| 3 | [companion/AGENTS.md](/app/core/companion_harness/companion/AGENTS.md) | LLM tracks, AwakeTurn/DreamingBatch, lifecycle invariants |
| 4 | [runtime/__init__.py](/app/core/companion_harness/runtime/__init__.py) | `turn_lock` contract |
| 5 | [companion/models.py](/app/core/companion_harness/companion/models.py) | `CompanionTurnTrack`, `InnerTickActivity` docstrings |
| 6 | [companion/runtime_channel.py](/app/core/companion_harness/companion/runtime_channel.py) | `CompanionRuntimeChannel` |
| 7 | [turn_invariants.py](/app/core/companion_harness/companion/turn_invariants.py) | Awake vs Dreaming curation rules |
| 8 | [lifecycle_invariants.py](/app/core/companion_harness/companion/lifecycle_invariants.py) | transcript append-only awake rules |
| 9 | [turn_routes.py](/app/core/companion_harness/companion/turn_routes.py) | `ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL` |
| 10 | Entry shell | `chat_ws.py` → `companion_chat_service.py` → `CompanionManager` → `run_turn` |
| 11 | IM ops | `backend/ops/weixin_channel/`, `backend/ops/telegram_demo/`, `app/services/agentic_channel/` |
| 12 | Inner tick | `core/companion_harness/runtime/inner_tick_fire.py`, `runtime/dreaming_batch.py`; glue: `services/agentic_companion/inner_tick_fire.py` |
| 13 | Memory | `memory/memory_store.py`, `memory_store_document_mapping.py` |
| 14 | Worlds | `app/living_sphere/`, `app/techno_core/` — imports/call sites only |
| 15 | Persist | `companion_memory_document_versions`, `memory_registry` DSN, `backend/alembic/` |
| 16 | Observability | `langsmith_parent_policy.py`, `runtime_events.py`, loguru |
| 17 | Roadmap | `grep 'TODO.*#[0-9]+' app/core/companion_harness` (+ telegram/channel TODOs in `app/`) |

## Architecture drawing anchors

**Do not** center the diagram on `chat_ws.py`. Center on **Companion Harness kernel**.

- Channel layer: WS, Weixin ops, Telegram ops, REPL (via WS).
- Access: auth, usage, visible history, protocol adaptation (API shell).
- Kernel: session, memory, turn orchestration — **not** fully isolated inbound runtime today.
- Adjacent: LivingSphere (personal), TechnoCore (shared virtual world).
- Persistence: MemoryStore versions + dialogue trace.

## Turn track template (from code)

For each `CompanionTurnTrack` member:

```markdown
- **`TRACK_NAME`**
  - 触发：…
  - 用户可见：是 / 否（…）
```

Add **Dreaming** under `InnerTickActivity.DREAMING` as **非 turn** (memory batch).

Include `INNER_TICK_AUTONOMY` when present in `CompanionTurnTrack` (silent; see [AUTONOMY.md](/docs/companion_harness/AUTONOMY.md)).

## Do not document here (pointer only)

- WebSocket payload fields → `app/schemas/chat_websocket.py`
- Memory doc taxonomy → [MEMORY_STORE.md](/docs/companion_harness/MEMORY_STORE.md)
- Autonomy / LIFE_CURRENTS → [AUTONOMY.md](/docs/companion_harness/AUTONOMY.md)
- World engine FR → [FR_WORLD_ENGINE.md](/docs/companion_harness/FR_WORLD_ENGINE.md)
- Unwired `contracts/turn.py`
- `/experimental/`, maintenance HTTP chat

## Epic clustering hints (from code TODO themes)

Group by Epic issue in roadmap section only — one line per Epic:

- Telegram production — #3395
- CRS — #3341
- Portable runtime — #3373
- Turn program / Pie-aligned orchestration — #3393
- Sub-tasks / sub-agents — #3394

Sub-issues stay in GitHub; do not checklist in DESIGN.md.
