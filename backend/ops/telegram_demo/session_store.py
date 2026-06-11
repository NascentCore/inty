"""In-memory telegram_chat_id ↔ Inty binding for Ops telegram-demo (prototype).

TODO(telegram-demo-orm-persistence): Design ``ops_telegram_demo_bindings`` ORM + restore on Ops restart.
TODO(telegram-demo-binding-not-persisted): Ops restart drops bindings; user must ``/start`` again.
"""

from __future__ import annotations

from backend.ops.telegram_demo.binding import TelegramDemoBinding
from backend.ops.telegram_demo.inprocess_presence import (
    TelegramInprocessPresence,
)

_bindings_by_chat_id: dict[str, TelegramDemoBinding] = {}
_presences_by_chat_id: dict[str, TelegramInprocessPresence] = {}


def get_binding(telegram_chat_id: str) -> TelegramDemoBinding | None:
    assert telegram_chat_id != ""
    return _bindings_by_chat_id.get(telegram_chat_id)


def put_binding(binding: TelegramDemoBinding) -> None:
    assert binding.telegram_chat_id != ""
    _bindings_by_chat_id[binding.telegram_chat_id] = binding


def remove_binding(telegram_chat_id: str) -> None:
    assert telegram_chat_id != ""
    _bindings_by_chat_id.pop(telegram_chat_id, None)
    _presences_by_chat_id.pop(telegram_chat_id, None)


def get_or_create_presence(
    binding: TelegramDemoBinding,
) -> TelegramInprocessPresence:
    assert binding is not None
    existing = _presences_by_chat_id.get(binding.telegram_chat_id)
    if existing is not None:
        return existing
    presence = TelegramInprocessPresence(binding)
    _presences_by_chat_id[binding.telegram_chat_id] = presence
    return presence


def clear_all_for_tests() -> None:
    """Test-only reset of in-memory store."""
    _bindings_by_chat_id.clear()
    _presences_by_chat_id.clear()
