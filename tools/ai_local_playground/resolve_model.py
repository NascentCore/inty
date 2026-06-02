"""
Resolve playground model selectors (nickname or id) to provider ids.

CREATED_BY_AGENT
"""

from __future__ import annotations

from app.utils.models_catalog import (
    resolve_chat_text_model,
    resolve_id_on_provider,
    resolve_nickname,
)


def resolve_playground_text_model_id(raw: str) -> str:
    trimmed = raw.strip()
    assert trimmed
    return resolve_chat_text_model(trimmed).id_on_provider


def resolve_playground_image_model_id(raw: str) -> str:
    trimmed = raw.strip()
    assert trimmed
    by_id = resolve_id_on_provider(trimmed)
    if by_id is not None:
        return by_id.id_on_provider
    by_nick = resolve_nickname(trimmed)
    if by_nick is not None:
        return by_nick.id_on_provider
    return trimmed
