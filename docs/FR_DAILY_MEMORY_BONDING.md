# Daily Memory Bonding Note (Love Journal Everyday Expansion)

CREATED_BY_AGENT

## 1. Goal

Expand Love Journal from festival-only recall to **everyday relationship memory building** so users feel "you remember me" in normal days, not only on special dates.

This feature is directly aligned with `docs/iMates_memory_for_bonding.md` Phase 3 ("periodic non-festival micro shared memory notes") and the bonding response protocol.

## 1.1 Design status update (2026-03-03)

### Implemented in current MVP branch

- Added backend memory type `daily_bonding` and daily metadata parsing model.
- Added on-demand daily prompt delivery on:
  - `POST /api/v1/chat/completions/{agent_id}`
  - `GET /api/v1/chats/agents/{agent_id}/messages`
- Added idempotent prompt message type `daily_memory_prompt` and `delivery_at` mark update.
- Added agent detail output `features.daily_memories`.
- Added app version gating with `min_app_version_code_for_daily_memory`.
- Excluded `daily_memory_prompt` from user analytics activity/latency metrics.
- Synced Android API DTOs (`daily_memories`, `daily_memory_id`) for compatibility.

### Deferred to next phase

- Automated DBN write path (scheduler + LLM extraction) is not included in this PR.
- DB-level uniqueness migration for `(user_id, agent_id, daily_bonding, local_date)` is not included yet.
- Safety controls planned in this doc (cadence cap, user opt-out toggle, risk-tier downgrade policy) are not fully implemented yet.
- Experiment dashboard events for DBN funnel are not fully instrumented yet.

## 2. Feature definition

### 2.1 Name

**Daily Bonding Note (DBN)**

### 2.2 Core user value

- Turn ordinary chats into small, emotionally salient shared memories.
- Increase continuity between consecutive days.
- Strengthen perceived responsiveness ("you listened to me yesterday and followed up today").

### 2.3 User experience flow

1. User chats with an iMate during a local calendar day.
2. If that day has enough interaction quality, backend creates one DBN memory item.
3. On next open/chat list fetch, system delivers one lightweight `daily_memory_prompt` message.
4. User taps prompt and opens Love Journal directly on that DBN card.
5. Card ends with one gentle follow-up invitation (forward motion).

Example prompt text:
"{char} kept a small note from yesterday. Want to read it?"

## 3. Scope and non-goals

### In scope

- One DBN max per `(user_id, agent_id, local_date)`.
- Existing Love Journal UI reused; add daily section/tag.
- Reuse festival-memory on-demand delivery style and idempotency behavior.

### Out of scope (phase 1)

- No full retrieval ranking overhaul for all memory types.
- No rewrite of main chat context packing.
- No complex personalization settings UI beyond a simple opt-out toggle.

## 4. Generation and eligibility logic

## 4.1 Candidate window

- Local timezone day window: `00:00 -> 23:59:59`.
- Evaluate after day close (recommended scheduler run at local `04:05` to avoid timezone edge noise).

### 4.2 Eligibility gates

Create DBN only when all pass:

1. Minimum user message rounds in day window (initial threshold: `>= 8`).
2. At least one emotionally meaningful moment detected:
   - user self-disclosure, or
   - user positive milestone, or
   - successful repair after tension.
3. Safety gate passes (no high-risk dependency escalation cues for that day).

### 4.3 Output structure

Each DBN card has 3 compact parts:

1. **Moment**: what happened.
2. **Meaning**: what it says about user state/preference/bond.
3. **Next step**: one low-friction invitation for today's chat.

Tone requirements:

- warm, specific, non-repetitive
- no over-romantic escalation
- no fabricated facts (abstain if uncertain)

## 5. Data model and API plan

### 5.1 Storage

Use `memory` table with new `memory_type = daily_bonding`.

Suggested metadata payload:

- `local_date` (YYYY-MM-DD)
- `timezone` (IANA)
- `emotional_salience` (0-1)
- `source_message_count`
- `delivery_at` (reuse current undelivered/delivered semantics)

Uniqueness semantics:

- one row for `(user_id, agent_id, memory_type=daily_bonding, local_date)`

### 5.2 Delivery

Reuse festival pattern:

- deliver on `POST /chat/completions/{agent_id}` and `GET messages`
- inject `messageType = "daily_memory_prompt"` meta message
- idempotent insert + mark `delivery_at`
- exclude prompt meta messages from normal AI model context by default

### 5.3 Client response

- `GET /api/v1/ai/agents/{agent_id}` extends `features.daily_memories` (or merged timeline item type).
- Android Love Journal renders DBN cards with date badge "Yesterday" or concrete date.

## 6. Safety-by-design controls

1. **Cadence cap**: max 3 DBN deliveries per 7 days per `(user, agent)`.
2. **Intensity cap**: if risk flags rise, force neutral-supportive wording template.
3. **Agency control**: user can mute "Daily Bonding Notes" from settings.
4. **Night overuse guard**: if repeated late-night overuse pattern exists, reduce push frequency.

## 7. Experiment and rollout

### 7.1 Feature flags

- `enable_daily_bonding_memory_write`
- `enable_daily_bonding_memory_read`
- `enable_daily_bonding_prompt_delivery`

### 7.2 Rollout steps

1. Internal dogfood on staff accounts.
2. 5% user rollout (subscribers first).
3. 25% rollout with safety monitor.
4. 50%/100% only if bonding metrics improve without safety regressions.

### 7.3 Success metrics

Primary:

- D7 and D30 retention uplift vs control
- "felt understood/remembered" feedback uplift
- next-day return rate after DBN delivery

Secondary:

- DBN open rate
- DBN -> same-day reply conversion
- user correction rate ("that's not what happened")

Safety:

- high-intensity attachment-risk event rate
- unhealthy night-only usage trend

## 8. Acceptance criteria (MVP)

1. System writes at most one DBN per day per `(user, agent)`.
2. DBN prompt is delivered exactly once (idempotent) and deep-links to correct Love Journal entry.
3. DBN content follows 3-part structure (moment/meaning/next-step).
4. Opt-out fully suppresses new DBN prompt delivery.
5. Metrics dashboard can segment treatment vs control for DBN flag cohorts.

## 9. Testing plan (for implementation phase)

Backend:

- unit tests for eligibility and idempotency
- integration tests for write + deliver + deep-link metadata
- regression test to confirm prompt message excluded from normal model context

Android/Evaluation:

- Love Journal list rendering with mixed `festival` + `daily_bonding`
- prompt click opens exact card
- opt-out toggle suppresses prompt entry

Safety:

- simulated high-risk users verify intensity/cadence caps applied

## 10. One-sentence implementation summary

Ship a new `daily_bonding` memory type that auto-summarizes meaningful daily moments into one Love Journal card and delivers it once on the next session to strengthen everyday continuity safely.
