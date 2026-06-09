"""Companion foreground user-turn input (text + optional images).

TODO(companion-multimodal-user-turn): Phase 1b — implement ``CompanionUserTurnInput``
(frozen dataclass: ``text: str``, ``image_data_urls: tuple[str, ...]``) with
``to_transcript_text()`` (caption or ``"[image]"``). Consumed by
``companion_chat_service.run_user_chat``; channel adapters (Weixin, WS) map wire
DTOs to this type. Multimodal LLM assembly lives in ``turn_pipeline``; capability
gate uses ``chat_model_accepts_image_input`` from ``models_catalog``.
"""
