# TEST_STEPS_OFFICIAL_ASSISTANT_MBTI_TOOL_CALLING

## Preconditions

1. Start PostgreSQL:
   - `sudo docker run --rm --name pg-inty -p 5432:5432 -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD='sxwl666!' -e POSTGRES_DB=inty -d postgres:16`
2. Start backend:
   - `source .venv/bin/activate && ./backend/inty/start.sh --test`
3. Prepare a valid bearer token for a test user.

## Steps

1. Send a chat request to the official assistant endpoint:
   - `POST /api/v1/chat/completions/879e5e14-fec2-4d63-9704-4f3141bed74f`
2. In the conversation, ask the assistant to run a full MBTI interview and return a final type.
3. Ensure the assistant returns a final MBTI type (for example, `INTJ`).

## Verification

1. Query database:
   - `SELECT meta_data FROM users WHERE id = '<user_id>';`
2. Confirm `meta_data` includes:
   - `{"mbti_type": "<FINAL_MBTI_TYPE>"}`.
3. Send a follow-up chat request and verify user profile context includes:
   - `MBTI Type: <FINAL_MBTI_TYPE>`.
