# FR_INTY_V2_CHAT_WS_INTEGRATION_PLAN

Revised integration plan for Inty v2 agentic companion via existing `WebSocket /api/v1/chat/ws`, incorporating review fixes (contract, verify parity, scope, DB session, idle timeout, tests).

## 1. Goals and constraints

- Same path as Android today: `wss://{base}/api/v1/chat/ws`, one JSON request per turn, one JSON response (shape of `SendMsgResponse`), plus `ping` / `pong` text frames.
- Land v2 inside the same `backend/inty` process; prototype code converges into `app/` product paths (see `docs/DEVOPS_IMATE_BACKEND_PLAN.md`).
- API user-facing error strings stay English (`app/AGENTS.md`).

## 2. Phase 0 - Contract and scope freeze

- Map `ChatWebSocketRequest` (`app/schemas/chat.py`) to Android `ChatWebSocketReq` / `SendMsgReq` / `SendMsgResponse` (`android_app/core/data/.../ChatBeans.kt`). New server fields are optional until the app needs them (client ignores unknown JSON keys).
- **Scope for first ship**: user-triggered turns only (same as current WS). Do not bind proactive heartbeat, inner tick, or schedule-driven turns to the first WS integration; those need a worker or a new client protocol.
- **Gray-scale keys** (pick before coding): config allowlist by `agent_id`, header (e.g. `X-App-Id`), and/or user segment. Document the chosen key in config comments.

## 3. Phase 1 - Shared chat turn entry (HTTP and WS)

- **Single source of behavior**: extract or centralize the body of `agent_chat_completions` so both `POST /api/v1/chat/completions/{agent_id}` and `/ws` call the same function (e.g. inner impl + thin HTTP/WS adapters). Avoid duplicating subscription limits, errors, and persistence.
- Introduce a narrow executor or branch inside that function: `legacy` vs `agentic_v2`, selected by config.
- **Shipped (partial)**: `app.features.chat_use_companion_kernel_agent_ids` routes matching agents through `CompanionManager` / companion `run_turn` only on **`WS /api/v1/chat/ws`** (`_agent_chat_completions_impl` with `chat_route="websocket"`), with `chat_history` persistence. **`POST /api/v1/chat/completions/{agent_id}`** keeps the legacy `Agent` stack. Gray-list rollout; verify endpoint still legacy-only until Phase 5.

## 4. Phase 2 - Persistence decision (before workspace mapping)

- Decide before wiring `run_turn`: whether each turn also writes `chat_history` (and matches list APIs). If v2 only writes `transcript.jsonl` (or v2-only store), either sync into `chat_history` or extend message-list APIs; otherwise the Android history UI breaks.
- Align subscription counting and business errors with the HTTP path.

## 5. Phase 3 - Identity and workspace mapping

- Define stable mapping from `user_id`, `agent_id`, `chat.id` to companion workspace root or DB-backed transcript (no ambiguous paths on shared VMs).
- Implement conversion from `SendMsgReq` messages (including multimodal parts) to v2 transcript rows.

## 6. Phase 4 - Async, timeout, and DB session rules

- **Idle timeout** (wait for next client text frame): `app.features.chat_ws_idle_timeout_seconds` in `config.yaml` (default 60, validated 10..3600 in `_validate_config`). Long LLM or tool work does not extend this window; the client must send `ping` (or any frame) often enough, or raise the config value for known slow agents.
- **AsyncSession**: the WS handler uses one `AsyncSession` for the whole connection (`Depends(get_async_db)`). Do not pass that session into `asyncio.to_thread` or any thread. If v2 runs blocking work in a thread, open a **new** DB session inside that worker (or avoid DB in the worker and pass plain IDs).
- **Turn timeout**: cap wall time for one turn so the server can return a structured error instead of hanging; keep under client read timeouts where possible.

## 7. Phase 5 - `/ws/verify` parity

- Today verify uses `generate_message_without_user_save`, not `agent_chat_completions` (`app/api/v1/endpoints/chat.py` docstring).
- When v2 is added to `/ws`, either:
  - **A (recommended)** refactor a shared dispatcher with a `persist: bool` flag so verify and prod share engine selection and only differ on persistence, or
  - **B** document verify as legacy-engine-only until aligned (risk: false confidence in QA).

## 8. Phase 6 - Testing

- `tests/AGENTS.md` prefers E2E without monkeypatch; **exception**: isolated WS handler tests may monkeypatch auth and completion stubs (see `tests/app/api/v1/endpoints/test_chat.py`). Prefer real server + token for new contract-critical paths when feasible.
- Add or extend tests for configurable idle timeout and for v2 routing once implemented.

## 9. Rollout

- Default off or tiny allowlist; monitor errors and latency; rollback via config only.

## 10. Config reference

```yaml
app:
  features:
    chat_ws_idle_timeout_seconds: 60
    # Optional: gray-list agent UUIDs for companion kernel (see Phase 1 shipped note).
    # chat_use_companion_kernel_agent_ids: []
    # companion_workspaces_base_dir: "/var/lib/inty/companion_workspaces"
    # companion_default_context_mode: "intimate"
```

Optional nested keys under `app` are parsed in `load_config` (e.g. `app.api_endpoints` for `APIEndpointsConfig`).

## 11. Follow-up backlog (companion kernel in `_agent_chat_completions_impl` / WebSocket path)

Track these after the initial gray-list ship; execute in order when touching the same code paths.

| Step | Item | Notes |
|------|------|-------|
| 1 | **Multimodal user turns** | **Done (2026-04-12):** WebSocket + companion allowlist: if the last user message includes an `image_url` part, return **HTTP 400** with English detail (also sent as JSON on `/ws` with `code`/`message`/`agent_id`, connection stays open). Multiple **text-only** parts still run (joined text passed to `run_turn`). Fixed inner `except Exception` in `_agent_chat_completions_impl` so `HTTPException` is not swallowed. Full multimodal rows in the kernel remain future work. |
| 2 | **Atomicity: workspace vs `chat_history`** | `run_turn` persists to companion store first; user/assistant rows are appended via `chat_history_service` after. A failure between the two can diverge. Define compensation, ordering, or a single transactional boundary. |
| 3 | **First-turn bootstrap semantics** | `bootstrap_session` consumes the first user line until workspace init passes. Document product/QA expectation for first HTTP/WS message vs local REPL. |
| 4 | **Config hot reload** | `companion_chat_service` uses `lru_cache` on allowlist and on resolved model id. Changing YAML without process restart does not refresh caches unless something calls `clear_companion_chat_service_caches()`. Document ops expectation or wire reload hook. |
| 5 | **`/ws/verify` parity** | Still Phase 5: verify path does not run companion kernel; align or keep explicit QA disclaimer. |
| 6 | **Lazy `get_agent` for companion path** | WebSocket companion path still loads legacy `Agent` (needed for voice, premium preview, etc.). Optional: defer `get_agent` until after branch or split dependencies. |
| 7 | **E2E** | Add real-server or integration test for one allowlisted agent round-trip (WS + message list), when CI has stable LLM stub or env flag. |

### Task log

- **2026-04-12:** Completed backlog step 1 (multimodal user turns on WS companion path). Code: `ChatMessage.has_image_content_part`, `_companion_rejects_multimodal_user_turn` in `app/api/v1/endpoints/chat.py`, WS handler maps `HTTPException` to JSON error frame; tests in `tests/app/api/v1/endpoints/test_chat.py`.
