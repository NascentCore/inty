# FR_OFFICIAL_ASSISTANT_MBTI_TOOL_CALLING

## Scope (Step 1)

Add tool calling capability for the official assistant (`Inty`) to persist the user's final MBTI type.

## Functional Requirements

1. Backend `users` table must have a new JSON column `meta_data`.
2. Official assistant chat flow must expose one tool:
   - `save_user_mbti_type`
3. Tool input:
   - `mbti_type` (string, one of 16 valid MBTI types)
4. When the tool is called successfully:
   - Persist `meta_data.mbti_type` for the current user.
   - Invalidate user profile cache so next prompt build reads updated data.
5. User profile prompt block should include MBTI when present:
   - `MBTI Type: <TYPE>`.

## Non-goals (Step 1)

1. No new public API endpoint is added.
2. No Android contract changes are required in this step.
3. No automatic MBTI inference is done by backend logic; the LLM decides when to call the tool.

## Validation

- Unit/logic tests under `tests/app/core/agent/`.
- Runtime smoke test with local PostgreSQL and direct helper invocation.
