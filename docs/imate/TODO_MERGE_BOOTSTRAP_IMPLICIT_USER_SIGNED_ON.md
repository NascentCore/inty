# TODO: Merge WS bootstrap kickoff into IMPLICIT_USER_SIGNED_ON

## Purpose

Unify **first proactive companion turn** on WebSocket (today split between server-driven **interactive bootstrap kickoff** and client-driven **`messageType: IMPLICIT_USER_SIGNED_ON`**) so **one client-visible mechanism** triggers onboarding greeting / bootstrap-aware opening, reducing duplicated logic and reconnect semantics.

Related docs:

- [/docs/FR_USER_SIGN_ON_GREETINGS.md](/docs/FR_USER_SIGN_ON_GREETINGS.md)
- [/app/api/AGENTS.md](/app/api/AGENTS.md) (chat WS contract)

## Current behavior (summary)

| Mechanism | When | Kernel input shape | `chat_history` user row |
|-----------|------|--------------------|-------------------------|
| `_try_send_ws_user_interactive_bootstrap_kickoff` ([`/app/api/v1/endpoints/chat.py`](/app/api/v1/endpoints/chat.py)) | After WS accept when `?agent_id=` and subscription allows | `run_turn` with synthetic **user** line `INTERACTIVE_BOOTSTRAP_WS_KICKOFF_USER_TEXT` ([`/app/core/agentic_kernel/companion/bootstrap_user_interactive.py`](/app/core/agentic_kernel/companion/bootstrap_user_interactive.py)) | No separate user message frame for kickoff reply path (assistant only via kickoff flow) |
| `IMPLICIT_USER_SIGNED_ON` | Client sends chat frame with empty visible text | Tail **system** `USER_SIGNED_ON_TRIGGER_SYSTEM_TEXT` ([`/app/core/agentic_kernel/companion/implicit_signal_messages.py`](/app/core/agentic_kernel/companion/implicit_signal_messages.py)); no empty user line | Skipped for implicit turn |

**Idempotency today:** `companion_ws_interactive_kickoff_sent` in workspace `context.json` gates kickoff so reconnect does not call `run_companion_interactive_bootstrap_kickoff_for_ws` twice ([`/app/services/companion_chat_service.py`](/app/services/companion_chat_service.py)).

## Target behavior

1. **Remove** server-side `_try_send_ws_user_interactive_bootstrap_kickoff` (and `run_companion_interactive_bootstrap_kickoff_for_ws` if nothing else needs it).
2. **Require** clients that want immediate proactive opening to send **one** WebSocket chat frame with `messageType: IMPLICIT_USER_SIGNED_ON` after session setup (ordering vs `user_signed_on` control frame TBD in implementation).
3. **Preserve** USER_INTERACTIVE bootstrap semantics while bootstrap incomplete: model must still enter relationship-establishment flow, not only a generic short greeting. Today kickoff aligns with placeholder-user instructions in bootstrap slices; IMPLICIT uses a different tail-system trigger - **plan must include prompt/kernel alignment** (e.g. extend tail-system text when `interactive_bootstrap_active`, or single merged trigger).

## Open design decisions

- **Server-side one-shot:** After deleting kickoff, decide whether to **delete** `companion_ws_interactive_kickoff_sent` entirely or **repurpose** it (e.g. first implicit bootstrap opening consumed) so reconnect + repeated IMPLICIT does not spam openings or burn quota. Alternative: derive idempotency from transcript (`implicit_user_signed_on` JSONL row) when bootstrap still incomplete.
- **Control frame:** Whether [`user_signed_on`](/docs/FR_USER_SIGN_ON_GREETINGS.md) should optionally **cause** the server to behave as if IMPLICIT was sent (product intent mentions greetings); today control frame mainly arms proactive heartbeat coords ([`/app/api/v1/endpoints/chat.py`](/app/api/v1/endpoints/chat.py)).
- **Quota:** IMPLICIT already counts as chat usage with `implicit_user_signed_on: true`; confirm parity with kickoff `ws_interactive_bootstrap_kickoff` analytics and whether either path should be exempt (see FR open TODOs).

## Client impact

| Client | Action |
|--------|--------|
| Shipped Android ([`/android_app/`](/android_app/), [`/imate_android_app/`](/imate_android_app/)) | FR notes they **never** sent IMPLICIT; **must add** one IMPLICIT chat frame when entering companion WS chat if product wants instant greeting without user typing. |
| [`/tools/inty_v2_repl/`](/tools/inty_v2_repl/) | Already sends IMPLICIT on first connect when URL has `agent_id`; **remove** reliance on server kickoff ordering if kickoff is deleted; verify smoke flows. |
| Tests ([`/tests/support/companion_ws_bootstrap/`](/tests/support/companion_ws_bootstrap/), [`/scripts/inty_backend_smoke_tests/`](/scripts/inty_backend_smoke_tests/)) | Replace kickoff drain/assertions with IMPLICIT send + response assertions. |

## Implementation checklist (for executor)

- [ ] Kernel/prompt: unify incomplete-bootstrap opening semantics for IMPLICIT vs old placeholder user text.
- [ ] API: remove kickoff call site after WS accept; adjust outbound ordering documentation.
- [ ] Service: remove or narrow `run_companion_interactive_bootstrap_kickoff_for_ws`; update `_mark_companion_ws_interactive_kickoff_sent_in_store` usage or delete field end-to-end (`ContextMeta`, [`/app/core/agentic_kernel/companion/manager.py`](/app/core/agentic_kernel/companion/manager.py) seed, seeds under [`/experimental/harness_seeding_demo/`](/experimental/harness_seeding_demo/), tests).
- [ ] Docs: update [/docs/FR_USER_SIGN_ON_GREETINGS.md](/docs/FR_USER_SIGN_ON_GREETINGS.md), [/app/api/ENDPOINTS.md](/app/api/ENDPOINTS.md), [/app/api/AGENTS.md](/app/api/AGENTS.md), [/docs/imate/DESIGN.md](/docs/imate/DESIGN.md) if it references kickoff.
- [ ] Kotlin models/comments if behavior promises change ([`/imate_android_app/.../ChatApiModels.kt`](/imate_android_app/app/src/main/java/com/inty/imate/chat/data/bean/ChatApiModels.kt), [`/android_app/.../ChatBeans.kt`](/android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model/ChatBeans.kt)).
- [ ] E2E: companion WS bootstrap tests and CI smoke paths green.

## Risks

- **Silent companion** if clients are not updated and kickoff is removed.
- **Duplicate openings** without server idempotency when clients send IMPLICIT on every reconnect.
- **Weaker bootstrap adherence** if tail-system greeting text dominates over interactive bootstrap spec without redesign.

## Status

Planning document only; implementation not started. Delete or shrink this file after merge is complete and canonical docs are updated.
