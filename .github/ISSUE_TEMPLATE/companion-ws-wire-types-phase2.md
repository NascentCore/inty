---
name: Companion WS wire types Phase 2
about: Adopt typed Pydantic wire models for companion /api/v1/chat/ws downlink (Phase 2+)
title: "Companion WS completion: adopt typed Pydantic wire models (Phase 2+)"
labels: agentic_companion
assignees: ''
type: Task
---

Phase 1 adds typed models in `app/schemas/chat_websocket.py` without changing emit/parse paths.

- [ ] Implement `build_companion_ws_completion_data(input: BuildCompanionWsCompletionInput) -> ChatWsCompletionData`
- [ ] `app/api/v1/endpoints/chat_ws.py`: all emit paths use typed builder (foreground / tool_bg / bootstrap interim / inner-tick / greeting)
- [ ] `app/api/v1/endpoints/chat.py`: `_companion_ai_meta_from_turn_result` returns `ChatWsCompanionWireMessageMetaData`
- [ ] `app/schemas/chat_websocket.py`: tighten `ChatWebSocketResponse.data` to `ChatWsCompletionData | None`
- [ ] `tools/inty_v2_repl/backend_chat_ws.py`: parse via `ChatWebSocketQueuedSuccessFrame.model_validate`
- [ ] `backend/ops/weixin_channel/inty_ws_client.py`: align downlink parse with `ChatWebSocketQueuedSuccessFrame`
- [ ] `app/core/companion_harness/companion/models.py`: `CompanionTurnResult` docstring points to wire types
- [ ] `app/services/chat_history_service.py`: `get_ai_message_info_by_id` returns `ChatWsPersistedAssistantRow`
- [ ] Endpoint regression tests (`tests/app/api/v1/endpoints/test_chat.py` WS companion cases)
- [ ] Out of scope: tighten HTTP `ChatCompletionResponse.choices` (separate issue)

Search codebase for `TODO(issue#` referencing this issue after filing.
