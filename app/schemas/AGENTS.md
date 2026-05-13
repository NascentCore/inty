# `app/schemas` — cross-boundary data shapes

**Summary:** This package holds Pydantic models for **HTTP bodies, WebSocket JSON frames, and other serialized payloads** that cross the API boundary; it is the typed contract between FastAPI handlers, clients, and (where applicable) persistence shapes in `app/models/`.

## Role in the system

- **What belongs here:** request/response DTOs and wire enums — **not** orchestration, LLM prompts, or domain services.
- **`app/schemas/__init__.py`:** legacy re-exports only; **do not add new imports** there (see file header).
- **Ops-only analytics DTOs** (e.g. user analytics reports) live under [`backend/ops/schemas/`](/backend/ops/schemas/), not under `app/schemas/`.

## Scope by concern (files are grouped by intent, not enumerated)

- **Companion chat (HTTP + shared fields):** message lists, completions, media generation helpers, time context — [`chat.py`](/app/schemas/chat.py).
- **Chat WebSocket wire:** control/ack/ping frames, queued business envelopes, companion `meta_data` conventions (forward-compatible `extra="allow"` where defined) — [`chat_websocket.py`](/app/schemas/chat_websocket.py).
- **Realtime voice / live session payloads:** language and session-oriented validation — [`live_chat.py`](/app/schemas/live_chat.py), [`phone_call.py`](/app/schemas/phone_call.py).
- **Turn-adjacent telemetry (non user-authored text):** versioned implicit signal bundles — [`implicit_signals.py`](/app/schemas/implicit_signals.py).
- **History compaction artifacts:** structured summaries of truncated/compacted windows — [`messages_compaction.py`](/app/schemas/messages_compaction.py).
- **Identity & account:** registration/login/guest, tokens, verification codes, user CRUD, deletion flows — [`auth.py`](/app/schemas/auth.py), [`token.py`](/app/schemas/token.py), [`verification_code.py`](/app/schemas/verification_code.py), [`user.py`](/app/schemas/user.py), [`user_deletion.py`](/app/schemas/user_deletion.py).
- **Product surface:** agents, themes, resources, subscriptions, settings, notifications, biz actions, reports — [`agent.py`](/app/schemas/agent.py), [`character_theme.py`](/app/schemas/character_theme.py), [`resource.py`](/app/schemas/resource.py), [`subscription.py`](/app/schemas/subscription.py), [`settings.py`](/app/schemas/settings.py), [`notification.py`](/app/schemas/notification.py), [`biz_action.py`](/app/schemas/biz_action.py), [`report.py`](/app/schemas/report.py).
- **Shared API plumbing:** generic API wrappers and pagination — [`response.py`](/app/schemas/response.py); field-omission helpers — [`exclude_fields.py`](/app/schemas/exclude_fields.py); health/version probes — [`health.py`](/app/schemas/health.py), [`version.py`](/app/schemas/version.py).

## Contract boundaries (must stay aligned)

- **Cross-language syncing:** These schemas need to be in sync with clients written in non-Python languages
- **Mobile / product clients:** chat-related field names, enums, and `meta_data` keys must stay consistent with Kotlin DTOs (e.g. [`android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model`](/android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model), [`imate_android_app/app/src/main/java/com/inty/imate/chat/data/bean/ChatApiModels.kt`](/imate_android_app/app/src/main/java/com/inty/imate/chat/data/bean/ChatApiModels.kt)); product copy for implicit companion signals is owned in [`app/core/agentic_kernel/companion/implicit_signal_messages.py`](/app/core/agentic_kernel/companion/implicit_signal_messages.py). Concrete WebSocket frame types, companion `meta_data` models, and control/ack `type` strings live in [`chat_websocket.py`](/app/schemas/chat_websocket.py) — read that module when changing wire behavior, not this overview.
- **Persistence:** when a payload mirrors stored entities, keep it coherent with [`app/models/`](/app/models/).
- **Transport vs turn correlation:** `ws_conn_id` is a **WebSocket handshake query parameter** used for logging and session-scoped behavior — it is **not** a Pydantic body field and does **not** replace **`user_msg_uuid`**, **`inty_trace_id`**, or LangSmith identifiers for correlating a single turn.

## Housekeeping

- Do not use **`model_config` as a field name** on a Pydantic model (clashes with Pydantic v2 configuration — see [model_config](https://docs.pydantic.dev/2.0/usage/model_config/)).
