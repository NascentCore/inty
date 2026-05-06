# Pydantic models for API endpoints

- Ops platform analytics schemas live under `app/schemas/analytics/` (e.g. user_analytics).
- Must keep consistent between data types here and Kotlin DTOs under [`android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model`](/android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model) (e.g. `SendMsgReq.messageType` matches `ChatCompletionRequest.message_type`) and iMate [`ChatApiModels.kt`](/imate_android_app/app/src/main/java/com/inty/imate/chat/data/bean/ChatApiModels.kt).
- **iMate** [`ChatApiModels.kt`](/imate_android_app/app/src/main/java/com/inty/imate/chat/data/bean/ChatApiModels.kt) sends `IMPLICIT_USER_SIGNED_ON` when entering chat (per agent, per WebSocket connection); IntelliMate contract may differ. Product copy for implicit sign-on lives in [`/app/core/agentic_kernel/companion/implicit_signal_messages.py`](/app/core/agentic_kernel/companion/implicit_signal_messages.py).
- Also keep consistent with [SqlAlchemy table models](/app/models/)
- Do not use `model_config` as field name in Pydantic Model objects,
  which conflicts with <https://docs.pydantic.dev/2.0/usage/model_config/>
