# tools/inty_v2_repl

This package is **WebSocket REPL only**: `python -m tools.inty_v2_repl.main repl` connects to `/api/v1/chat/ws`. Companion logic lives in [`app/core/agentic_kernel/companion/`](../../app/core/agentic_kernel/companion/).

Full usage: [README.md](README.md).

## Transport vs REPL behavior

- **Uplink**: Each non-empty user line is sent with [`BackendChatWsBridge.post_turn`](backend_chat_ws.py) (**`ws.send` only**). The next line can be sent **without waiting** for the assistant frame; frames queue on the socket while the server still **processes one chat message at a time** per connection.
- **Reconnect sign-on**: If the WebSocket URL includes `agent_id` (bootstrap kickoff on first connect), after the **second and later successful transport connections** the bridge sends one frame with empty user text and `messageType: IMPLICIT_USER_SIGNED_ON` so the server can greet without duplicating the first-connect bootstrap. URLs without `agent_id` do not auto-send this frame.
- **Downlink**: Assistant and error JSON are read into `_response_q` and surfaced via [`pop_downlink_item`](repl_message_io.py) (POSIX TTY: during input polling; after each `post_turn`; non-TTY: best-effort drain after each `input()` line).
- **Multi-frame replies**: `tool_bg`, proactive heartbeat, etc. each produce separate JSON payloads; all drain through the same queue.
- **Latency banner**: Wall elapsed for an assistant line uses `meta_data.user_msg_uuid` or `reply_to_user_msg_uuid` to match the matching `post_turn` timestamp when possible; otherwise `0ms`.
- **Sync API**: [`BackendChatWsBridge.send_turn`](backend_chat_ws.py) still blocks until one parsable assistant payload (subject to `INTY_V2_BACKEND_WS_RECV_TIMEOUT_SEC`); reserved for scripts, not used by interactive `repl`.
