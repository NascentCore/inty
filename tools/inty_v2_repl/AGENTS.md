# tools/inty_v2_repl

This package is **WebSocket REPL only**: `python -m tools.inty_v2_repl.main repl` connects to `/api/v1/chat/ws`. Companion logic lives in [`app/core/agentic_kernel/companion/`](../../app/core/agentic_kernel/companion/).

Full usage: [README.md](README.md).

## Transport vs REPL behavior

- **User online signal (`user_signed_on`)**: Arms proactive heartbeat coords; greeting triggers use **`messageType: IMPLICIT_USER_SIGNED_ON`** chat frames (copy in `/app/core/agentic_kernel/companion/implicit_signal_messages.py`). On the **first** successful WebSocket connect, if the URL includes `agent_id`, the bridge sends one **`{"type":"user_signed_on","agent_id":...}`** control frame (not repeated per chat turn or on reconnect within the same REPL process). Interactive `repl` logs send and ack to stderr; bridge callbacks enqueue formatted lines and [`main._readline_backend_ws_with_sideband`](main.py) drains them on the input thread so TTY stdout (`> `) and stderr do not splice on one row.
- **Uplink**: Each non-empty user line is sent with [`BackendChatWsBridge.post_turn`](backend_chat_ws.py) (**`ws.send` only**). The next line can be sent **without waiting** for the assistant frame; frames queue on the socket while the server still **processes one chat message at a time** per connection.
- **Startup implicit sign-on**: On the **first** successful WebSocket connect after the bridge starts, if the URL includes `agent_id`, the bridge schedules one chat frame with empty user text and `messageType: IMPLICIT_USER_SIGNED_ON` (after `user_signed_on`). URLs without `agent_id` do not auto-send this frame; transport reconnects do not send another. Success logs at info (`repl sent IMPLICIT_USER_SIGNED_ON at startup`); failures log at exception level with `agent_id`.
- **Downlink**: Assistant and error JSON are read into `_response_q` and surfaced via [`pop_downlink_item`](repl_message_io.py) (POSIX TTY: during input polling; after each `post_turn`; non-TTY: best-effort drain after each `input()` line).
- **Multi-frame replies**: `tool_bg`, proactive heartbeat, etc. each produce separate JSON payloads; all drain through the same queue.
- **Latency banner**: Wall elapsed for an assistant line uses `meta_data.user_msg_uuid` or `reply_to_user_msg_uuid` to match the matching `post_turn` timestamp when possible; otherwise `0ms`.
- **Sync API**: [`BackendChatWsBridge.send_turn`](backend_chat_ws.py) still blocks until one parsable assistant payload (subject to `INTY_V2_BACKEND_WS_RECV_TIMEOUT_SEC`); reserved for scripts, not used by interactive `repl`.
