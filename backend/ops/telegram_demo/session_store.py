"""Telegram demo binding store: in-memory presences + Postgres persistence."""

from __future__ import annotations

from loguru import logger

from app.external_services.telegram_bot_api import TelegramBotApi
from app.services.agentic_companion.runtime_channel_registry import (
    ActiveRuntimeChannel,
    register_active_channel,
)
from backend.ops.telegram_demo.binding import TelegramDemoBinding
from backend.ops.telegram_demo.inprocess_presence import (
    TelegramInprocessPresence,
)
from backend.ops.telegram_demo.persistence import (
    list_bindings,
    upsert_binding as persist_binding_row,
)

_bindings_by_chat_id: dict[str, TelegramDemoBinding] = {}
_presences_by_chat_id: dict[str, TelegramInprocessPresence] = {}


def get_binding(telegram_chat_id: str) -> TelegramDemoBinding | None:
    assert telegram_chat_id != ""
    return _bindings_by_chat_id.get(telegram_chat_id)


def _put_binding_memory(binding: TelegramDemoBinding) -> None:
    assert binding.telegram_chat_id != ""
    _bindings_by_chat_id[binding.telegram_chat_id] = binding


async def put_binding(binding: TelegramDemoBinding) -> None:
    """Write binding to memory and Postgres."""
    _put_binding_memory(binding)
    await persist_binding_row(binding)


# TODO(telegram-demo-unbind): call from transport unbind before ``delete_binding`` — #3340
def remove_binding(telegram_chat_id: str) -> None:
    assert telegram_chat_id != ""
    _bindings_by_chat_id.pop(telegram_chat_id, None)
    _presences_by_chat_id.pop(telegram_chat_id, None)


# TODO(telegram-demo-ensure-presence): Replace with ``ensure_presence``; uninited return breaks
# inner-tick/tool_bg — #3338
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


# TODO(telegram-demo-ensure-presence): Merge into single ``ensure_presence`` entry — #3338
async def start_presence(
    binding: TelegramDemoBinding,
    *,
    api: TelegramBotApi,
) -> TelegramInprocessPresence:
    """Replace any prior presence for ``binding`` and start inner-tick worker."""
    existing = _presences_by_chat_id.pop(binding.telegram_chat_id, None)
    if existing is not None:
        await existing.stop()
    presence = TelegramInprocessPresence(binding)
    _presences_by_chat_id[binding.telegram_chat_id] = presence
    await presence.start(api=api)
    return presence


async def stop_all_presences() -> None:
    """Stop every in-process presence (inner-tick + tool_bg) on Ops shutdown."""
    chat_ids = list(_presences_by_chat_id.keys())
    for chat_id in chat_ids:
        presence = _presences_by_chat_id.pop(chat_id, None)
        if presence is not None:
            await presence.stop()


async def restore_persisted_bindings(*, api: TelegramBotApi) -> None:
    """Reload Postgres bindings and restart presences after Ops restart."""
    assert api is not None
    # TODO(telegram-demo-restore-parallel): ``create_task`` per binding like Weixin — #3339
    # TODO(telegram-demo-ensure-presence): do not ``_put_binding_memory`` until presence starts — #3338
    records = await list_bindings()
    for record in records:
        binding = record.to_demo_binding()
        _put_binding_memory(binding)
        register_active_channel(
            user_id=binding.user_id,
            channel=ActiveRuntimeChannel.TELEGRAM,
        )
        try:
            await start_presence(binding, api=api)
        except Exception:
            logger.exception(
                "telegram-demo restore presence failed chat_id={}",
                binding.telegram_chat_id,
            )
    if records:
        logger.info(
            "telegram-demo: restored {} persisted binding(s)",
            len(records),
        )


def clear_all_for_tests() -> None:
    """Test-only reset of in-memory store."""
    _bindings_by_chat_id.clear()
    _presences_by_chat_id.clear()
