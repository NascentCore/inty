# Chat WebSocket Debug Switch Test Steps

1. Start backend service on `localhost:8000`.
2. Open Android app (debug build), navigate to `Me -> Settings -> Debug backend config`.
3. Enable `Chat websocket mode`.
4. Enter chat with Agent A and send one message.
5. Switch to Agent B and send one message without restarting app.
6. Verify both requests succeed and backend logs show `/api/v1/chat/ws` handling both `agent_id` values on the same connection lifecycle.
7. Disable `Chat websocket mode` and send one more chat message.
8. Verify request falls back to `POST /api/v1/chat/completions/{agent_id}`.
