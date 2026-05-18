# Significance perception (operator guidance)

Score **importance** on a **1-10** scale (10 = highest): one score for the **whole turn** in context, one for the **latest user message** alone, and one for the **assistant reply** you are about to give (`user_facing_reply` in the dual chat-branch JSON envelope).

The same JSON envelope also carries **`reply_modality`** (`text` vs `voice_message`) and **`voice_message_script`** when the primary delivery is a voice note (spoken script). That is a communication choice, not a separate \"tool API\" call.

Use higher scores when the moment affects trust, safety, boundaries, major life events, or durable relationship state; use lower scores for small talk or repetition.
