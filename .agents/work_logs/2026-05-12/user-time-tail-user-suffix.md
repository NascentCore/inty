# user-time tail user suffix

User time is appended as `user-time:` / `user-time-zone:` / optional `user-time-utc-offset:` lines after the tail user text for LLM requests instead of a system markdown block.

- User wall-clock context moved from system markdown to a factual suffix on the last user message (companion + classic Agent OpenAI payload), gated by `experimental_enable_chat_with_user_time_context`.
- Removed `implicit_signal_system_messages` and assembler user-time system blocks; added `suffix_user_text_with_time_context_lines` and `_openai_messages_from_lc_messages_with_tail_user_time`.

Follow-ups: none.
