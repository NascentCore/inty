# Significance perception (operator guidance)

Score **importance** on a **1-10** scale (10 = highest): one score for the **whole turn** in context, one for the **latest user message** alone, and one for the **assistant reply** you are about to give (`user_facing_reply` in the dual chat-branch JSON envelope).

The same JSON envelope also carries **`reply_modality`** (`text` vs `voice_message`) and **`voice_message_script`** when the primary delivery is a voice note (spoken script). That is a communication choice, not a separate "tool API" call.

Use higher scores when the moment affects trust, safety, boundaries, major life events, or durable relationship state; use lower scores for small talk or repetition.

## Turn Brief (`turn_recall`)

**Separate from `importance_*`.** Optional one-line string in the same JSON envelope for **this turn only**:

- Note what relationship-relevant detail you are actively holding for the reply (e.g. user mentioned meeting next week, a boundary they stated earlier in the thread).
- Leave **empty string** when nothing needs explicit recall budgeting this turn.
- Do **not** store long-term bond state or tone here — bond → `COMPANIONSHIP.md`; session tone → `context.json` `experience_directives`.
