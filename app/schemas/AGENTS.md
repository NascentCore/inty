# `app/schemas` — cross-boundary data shapes

**Summary:** This package holds Pydantic models for **HTTP bodies, WebSocket JSON frames, and other serialized payloads** that cross the API boundary. It is the typed contract between FastAPI handlers, non-Python clients, and (where applicable) persistence-oriented shapes defined alongside the ORM layer.

## Who should read this

- **Backend engineers** changing request/response or WebSocket wire formats.
- **Client engineers** aligning Kotlin/Swift (or other) DTOs with the same JSON field names and enums.
- **Anyone debugging turns** who needs to know which identifiers are on the wire versus only in logs or tracing.

If you are not touching serialization boundaries, you usually do not need to edit here.

## Role in the system

- **What belongs here:** request/response DTOs and wire enums — **not** orchestration, LLM prompts, or domain services.
- **Package root exports:** the package initializer only carries legacy re-exports; **do not grow** that surface for new types — introduce named modules and import from them directly at call sites.
- **Ops-only analytics DTOs** (e.g. operational user analytics reports) belong with the ops application schema area, **not** under this tree.

## Scope by concern (grouped by intent)

Descriptions below name **topics**, not implementation files; use your editor’s symbol search or tests that assert wire JSON when you need the exact model.

- **Companion chat (HTTP + fields shared with realtime):** message lists, completions, media-generation-related payloads, user time context for the companion.
- **Chat WebSocket wire:** control, acknowledgment, and ping frames; queued business envelopes; companion `meta_data` conventions. Where models are intentionally forward-tolerant, extra keys may be preserved rather than rejected. Assistant or user `meta_data` may carry scheduled-reminder bookkeeping when a due schedule-queue task is delivered through the inner-tick path.
- **Realtime voice / live session payloads:** language and session-oriented validation for live chat and phone-call style flows.
- **Turn-adjacent telemetry (not user-authored chat text):** versioned implicit-signal bundles the product may surface without treating them as normal user messages.
- **History compaction artifacts:** structured representations of truncated or compacted windows for long-context handling.
- **Identity and account:** registration, login, guest flows, tokens, verification codes, user CRUD, and deletion-related payloads.
- **Product surface:** agents, character themes, downloadable resources, subscriptions, settings, notifications, business actions, and reporting DTOs the app exposes over HTTP.
- **Shared API plumbing:** generic success/error wrappers, pagination helpers, field-omission utilities for selective serialization, and small health/version probe payloads.

## Contract boundaries (must stay aligned)

- **Cross-language syncing:** Any change here is a **public wire contract** until deprecated with a deliberate migration; treat field renames and enum value changes as client-facing releases, not refactors.
- **Mobile and desktop clients:** chat-related names, enums, and `meta_data` keys must remain consistent with the **Kotlin (and any parallel Swift) DTOs** maintained in the Android and iMate client codebases. When companion behavior introduces new `meta_data` keys (for example background tool loops, voice-as-message delivery, or implicit sign-on semantics), clients and this package must advance together or behind explicit version gates.
- **Product copy for implicit companion signals:** user-visible strings for synthetic or implicit turns are owned next to the companion harness, not duplicated inside schema modules — schemas carry structure; copy lives with companion presentation rules.
- **Persistence coherence:** when a payload intentionally mirrors something stored, keep the **shape and invariants** aligned with the ORM models and migrations so serializers do not drift from what the database can represent.
- **Transport versus turn correlation:** `ws_conn_id` is negotiated as a **WebSocket handshake query parameter** for logging and session-scoped server behavior. It is **not** a JSON body field on chat completions and it **does not replace** per-turn identifiers such as **`user_msg_uuid`**, **`inty_trace_id`**, or LangSmith run/trace identifiers when correlating a single assistant turn end-to-end.

## Housekeeping

- Do not use **`model_config` as a field name** on a Pydantic model (it clashes with Pydantic v2 configuration — see the upstream [model_config](https://docs.pydantic.dev/2.0/usage/model_config/) documentation).
