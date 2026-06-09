"""Weixin inbound media → companion ``CompanionUserTurnInput`` adapter.

TODO(weixin-inbound-image): Phase 2 — implement ``weixin_inbound_to_user_turn``:
https://github.com/NascentCore/inty/issues/3293
read Hermes-cached ``media_paths`` for ``image/*`` MIME types, encode as
``data:<mime>;base64,...`` OpenAI ``image_url`` parts, return
``CompanionUserTurnInput(text=..., image_data_urls=...)``. No LLM calls here —
only Ops-boundary filesystem read of bytes Hermes already decrypted.
"""
