# FR: Implicit user sign-on greetings (companion WebSocket)

## Goal

Reduce awkwardness when the user returns to the chat channel by letting the client send a non-user-authored turn that the backend treats as an implicit signal: inject a system slice so the model briefly greets the user. The first proactive turn on a fresh connection with `?agent_id=` remains the existing USER_INTERACTIVE bootstrap kickoff; subsequent reconnects can use `messageType: IMPLICIT_USER_SIGNED_ON` (see REPL bridge).

## Protocol (summary)

- Optional field on `ChatCompletionRequest`: `messageType` (alias), enum `CompanionChatTurnMessageType`: `USER_MESSAGE` (default), `IMPLICIT_USER_SIGNED_ON`.
- `IMPLICIT_USER_SIGNED_ON` requires empty user visible text and no image parts in `messages`; WebSocket companion only; maps to `ImplicitSignalBundle.user_signed_on` and skips persisting an empty user row.
- Usage analytics: successful implicit sign-on turns include `implicit_user_signed_on: true` in `record_usage` `extra_data` (still counts as one chat turn toward limits).
- HTTP `/api/v1/chat/completions` rejects `IMPLICIT_USER_SIGNED_ON` with 400.

## Sequence (sign-on turn)

```mermaid
sequenceDiagram
    participant REPL
    participant WS as chat_ws
    participant API as _agent_chat_completions_impl
    participant CCS as companion_chat_service
    participant LLM

    REPL->>WS: ChatWebSocketRequest empty user messageType IMPLICIT_USER_SIGNED_ON
    WS->>API: validate ChatCompletionRequest
    API->>API: ImplicitSignalBundle user_signed_on from message_type
    API->>CCS: run_companion_chat_turn_for_api
    CCS->>LLM: system includes sign-on greeting slice + user content empty
    LLM-->>CCS: assistant greeting
    CCS-->>API: CompanionTurnResult
    API-->>REPL: APIResponse choices
```

## Open TODOs (follow-ups)

Anchor for deep links: `#open-todos-follow-ups`.

Non-blocking items from code review; implement when product or refactor needs them.

### Subscription quota (`record_usage`)

Implicit sign-on turns still call `record_usage(..., "chat", 1)` and consume the same daily limit as a normal user message. Product may later want to **exclude** `IMPLICIT_USER_SIGNED_ON` from the limit or count it separately; that requires changes in subscription / limit checks (not only `extra_data`). Analytics can filter on `extra_data.implicit_user_signed_on` until then.

### `implicit_signed_on_ws` binding scope

The flag is computed once at the start of `_agent_chat_completions_impl` and used deep inside the companion branch. If this function is split into smaller helpers, **pass `implicit_signed_on_ws` explicitly** so companion / persistence paths cannot drift.

### Multimodal rejection paths

- `messageType: USER_MESSAGE` with **image-only** content still hits the generic companion multimodal **400** (`Multimodal user turns with images are not supported...`).
- `messageType: IMPLICIT_USER_SIGNED_ON` with any image part hits a **distinct** **400** (`...does not support multimodal or image content`). Keep both behaviors documented when changing either branch.

### Client build verification

[`imate_android_app`](/imate_android_app/) full `:app:compileDebugKotlin` was not run in all CI sandboxes (missing `ANDROID_HOME`). **Merge or release checklist:** compile iMate app with a normal Android SDK; IntelliMate [`android_app`](/android_app/) `:core:data:compileDebugKotlin` should be run when touching [`ChatBeans.kt`](/android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model/ChatBeans.kt).

## References

- Schema: [`/app/schemas/chat.py`](/app/schemas/chat.py) (`CompanionChatTurnMessageType`, `ChatCompletionRequest.message_type`)
- Bundle: [`/app/schemas/implicit_signals.py`](/app/schemas/implicit_signals.py)
- Prompt slice: [`/app/core/agentic_kernel/companion/implicit_signal_messages.py`](/app/core/agentic_kernel/companion/implicit_signal_messages.py)
- Handler: [`/app/api/v1/endpoints/chat.py`](/app/api/v1/endpoints/chat.py)
- REPL client: [`/tools/inty_v2_repl/backend_chat_ws.py`](/tools/inty_v2_repl/backend_chat_ws.py)
