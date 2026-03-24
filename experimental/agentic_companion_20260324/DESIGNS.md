# Minimal Design: Generalized Agentic Companion (2026-03-24)

## 1) Goal

Build a bare-bones companion agent system that supports:

- Multi-modal chat (`text/image/audio/video`) in app.
- Phone channels (`SMS` and `call`).
- Internal long-term memory + retrieval.
- Prompt assemblage from memory/history/channel context.
- Human-like autonomy when user is idle.

## 2) Design principles (minimal)

- One shared runtime pipeline for all channels.
- One canonical internal message/event contract.
- Keep autonomy as a small heartbeat loop, not a complex planner.
- Separate user-visible proactive actions from internal maintenance actions.
- Reuse the same memory + prompt system for both reactive and proactive turns.

## 3) Bare-bones components

1. **Channel Gateway**
   - Inbound adapters: app chat webhook, SMS webhook, call webhook.
   - Outbound adapters: app push/chat delivery, SMS send, call TTS/playback.

2. **Conversation Orchestrator**
   - Main turn handler.
   - Coordinates preprocessing, memory retrieval, prompt assembly, LLM call, and response routing.

3. **Media Service**
   - Inbound: STT for audio/video and basic image/video caption extraction.
   - Outbound: TTS for call/audio responses.

4. **Memory Core**
   - Memory store (facts/summaries/preferences).
   - Memory retriever (semantic + recency).
   - Memory evolver (async extraction and maintenance).

5. **Prompt Assembler**
   - Builds final LLM prompt from system/persona/channel policy/history/retrieved memory.

6. **LLM Gateway**
   - Unified model invocation interface.
   - Allows separate model configs for chat vs memory extraction.

7. **Autonomy Engine (heartbeat worker)**
   - Runs periodically for active user-companion pairs.
   - Executes internal maintenance or proactive outreach when appropriate.

8. **Storage**
   - PostgreSQL (sessions/messages/memories/policies/jobs).
   - Object storage (media files).
   - Vector index (pgvector/equivalent for memory retrieval).

## 4) Canonical internal event contract

All channels normalize inbound payloads into one envelope:

- `event_id`
- `user_id`
- `companion_id`
- `channel` (`app_chat | sms | phone_call`)
- `session_id`
- `content_parts[]` (`text | image | audio | video`)
- `timestamp`
- `metadata` (phone number, language, qos, etc.)

This keeps downstream logic channel-agnostic.

## 5) Minimal data model

- `users`
- `companions` (persona + channel preferences + llm config)
- `sessions` (per channel conversation context)
- `messages` (normalized event log)
- `memories` (memory item + score + last_seen_at + source refs)
- `memory_vectors` (embedding per memory item)
- `autonomy_policy` (quiet hours, budgets, channel permissions)
- `autonomy_state` (last action, ignored count, current idle state)
- `autonomy_log` (why/what/outcome for each autonomous action)
- `jobs` (async tasks: transcribe, memory evolve, tts, heartbeat)

## 6) Prompt assemblage (single template)

Prompt sections:

1. System core behavior.
2. Companion persona.
3. Channel behavior policy (app/sms/call constraints).
4. Safety/style constraints.
5. Retrieved memory snippets (top-K).
6. Recent conversation window.
7. Output schema for target channel.

## 7) End-to-end flows

### 7.1 User-driven turn

1. Inbound event received by Channel Gateway.
2. Normalize + persist message.
3. Media preprocessing (if needed).
4. Retrieve top-K memory.
5. Assemble prompt.
6. Call LLM.
7. Render per channel contract.
8. Persist AI response.
9. Dispatch outbound response.
10. Enqueue async memory evolution.

### 7.2 Autonomous turn (idle user)

1. Heartbeat selects candidate user-companion pair.
2. Load `autonomy_policy` + `autonomy_state` + recent interaction signals.
3. Decide action type:
   - Internal-only action (memory consolidation / summary update), or
   - Outward proactive action (check-in/reminder).
4. If outward action allowed, assemble prompt + generate + dispatch.
5. Log decision score, reason, and result in `autonomy_log`.
6. Update `autonomy_state` and cooldown/budgets.

## 8) Autonomy behavior (minimal but human-like)

### 8.1 Idle states

- `ACTIVE`: user interacted recently; no outreach.
- `IDLE_SOFT`: internal maintenance only.
- `IDLE_MEDIUM`: optional low-intrusion check-in.
- `IDLE_LONG`: one re-engagement attempt, then back off.

### 8.2 Action classes

- **Internal-only** (safe default):
  - merge duplicate memories,
  - decay stale memories,
  - refresh relationship summary.
- **Outward** (user-visible):
  - short contextual check-in,
  - reminder follow-up,
  - channel-aware nudge (app first, SMS second, call opt-in only).

### 8.3 Decision function

Use a lightweight score:

`score = relevance + memory_need + relationship_value - intrusiveness - recent_outreach_penalty`

Execute only when:

- score is above threshold,
- quiet hours are respected,
- daily/channel budgets remain,
- cooldown window has elapsed.

## 9) Channel output contracts

- `AppResponse`: `{ text, media_actions[] }`
- `SmsResponse`: `{ text }` (strict length and tone rules)
- `CallResponse`: `{ utterance_text, tts_voice_id, end_call? }`

## 10) Minimal API surface

- `POST /events/inbound`
- `POST /responses/outbound/{channel}`
- `GET /sessions/{id}/messages`
- `POST /companions`
- `PATCH /companions/{id}`
- `GET /memories?user_id=...&companion_id=...`
- `POST /internal/jobs/memory-evolve`
- `POST /internal/jobs/autonomy-heartbeat`

## 11) Phase-1 delivery scope

Start with:

- app chat + sms + basic call tts,
- memory retrieval + async memory evolution,
- heartbeat autonomy with internal actions enabled by default,
- proactive outbound disabled by default (opt-in + strict budget).

This is the smallest architecture that still supports multi-channel interaction, evolving memory, prompt coupling, and human-like idle autonomy.
