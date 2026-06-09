## Goal

WeChat 用户发送图片时 companion 能「看见」并回复。实现分两层：

1. **Phase 1** — 在 agentic companion harness 定义接受图片的 user-chat 接口
2. **Phase 2** — Weixin channel 作为薄 adapter，把 Hermes inbound 映射到该接口

是否走 multimodal 由 **`select_chat_model()` 解析出的 user chat model** 的 `modalities.inputs` 是否含 `IMAGE` 决定——**不使用**单独的 vision/caption 或 tool-call 模型。

## Phase 1 — Companion chat interface (core)

### 1a. Model capability — `app/utils/models_catalog.py`

- 新增 `chat_model_accepts_image_input(model: GenAIModel) -> bool`
- 修正 `CHAT_TEXT_MODELS` 中 vision-capable 条目（至少 `GEMINI_2_5_FLASH*` 补 `IMAGE` input）
- `openrouter_chat_model_from_id_uncatalogued` 保持 TEXT-only

### 1b. Companion user-turn contract

- 新类型 `CompanionUserTurnInput` in `app/core/companion_harness/companion/user_turn_input.py`
  - `text: str`, `image_data_urls: tuple[str, ...]`
  - `to_transcript_text()` → caption 或 `"[image]"`
- `companion_chat_service.run_user_chat(user_turn=...)` 替代 `user_text: str`
- Gate: `CompanionMultimodalNotSupportedError` when images present but chat model lacks IMAGE input

### 1c. Turn pipeline

Thread `CompanionUserTurnInput` through manager / turn.py / turn_pipeline; assemble OpenAI multimodal tail user message when model accepts IMAGE. Transcript/memory stay text-only.

### 1d. Tests (no Weixin dependency)

- catalog helper, turn_pipeline multimodal tail, model gate rejection

## Phase 2 — Weixin channel adapter

- `backend/ops/weixin_channel/weixin_inbound_media.py`: Hermes cache → data URL → `CompanionUserTurnInput`
- `session.py` / `inprocess_presence.py`: call `run_user_chat(user_turn=...)`; catch gate error for WeChat fallback
- Weixin integration tests

## Out of scope

- WS `/api/v1/chat/ws` multimodal gate (follow-up after Phase 1)
- Outbound WeChat send_image, voice ASR, historical image replay

## Tracking

Code TODOs use tags `companion-multimodal-user-turn` (Phase 1) and `weixin-inbound-image` (Phase 2).

Related PR (TODO markers only): #3291
