"""Telegram Bot API HTTP client for Ops telegram-demo long-poll bridge.

TODO(telegram-meta-ops-api): Add setMyName / setMyDescription / sendChatAction — #3397
  (requires dedicated-bot bonding #3361; shared-bot constraints #3396)
TODO(telegram-reply-reaction-api): Parse reply_to_message + message_reaction in getUpdates;
  sendMessage reply_parameters + setMessageReaction — #3441 (epic #3440)
TODO(!3451): Add the minimal sendPhoto wrapper for native Telegram image bubbles.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

# urllib timeout must exceed Telegram's long-poll ``timeout`` query param.
_GET_UPDATES_URLOPEN_TIMEOUT_SLACK_S = 5


class TelegramParseMode(StrEnum):
    """Telegram Bot API parse_mode values for sendMessage."""

    HTML = "HTML"


def format_epoch_for_local_log(
    ts: float | int | None, *, missing: str = "n/a"
) -> str:
    """Format Unix epoch seconds for logs: convert to **system local** timezone with offset."""
    if ts is None:
        return missing
    dt = datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone()
    return dt.strftime("%Y-%m-%d %H:%M:%S %z")


@dataclass(frozen=True)
class TelegramIncomingMessage:
    update_id: int
    chat_id: str
    channel_user_id: str
    text: str
    local_received_at: float
    message_date_unix: int | None = None


@dataclass(frozen=True)
class TelegramBotInfo:
    bot_id: int
    username: str


@dataclass
class TelegramBotApi:
    bot_token: str
    urlopen: Any = urllib.request.urlopen
    base_url: str = "https://api.telegram.org"

    def _method_url(self, method_name: str) -> str:
        return f"{self.base_url}/bot{self.bot_token}/{method_name}"

    def get_me(self) -> TelegramBotInfo:
        request = urllib.request.Request(
            url=self._method_url("getMe"),
            method="GET",
        )
        with self.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("ok") is not True:
            raise ValueError(f"Telegram getMe failed: {payload}")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise ValueError(f"Telegram getMe invalid result: {payload}")
        bot_id_raw = result.get("id")
        username_raw = result.get("username")
        if not isinstance(bot_id_raw, int):
            raise ValueError(f"Telegram bot id missing or invalid: {result}")
        if not isinstance(username_raw, str) or not username_raw.strip():
            raise ValueError(
                f"Telegram bot username missing or invalid: {result}"
            )
        return TelegramBotInfo(bot_id=bot_id_raw, username=username_raw.strip())

    def get_text_messages(
        self,
        *,
        offset: int | None,
        timeout_seconds: int,
    ) -> tuple[list[TelegramIncomingMessage], int | None]:
        query_params: dict[str, str | int] = {
            "timeout": max(0, timeout_seconds)
        }
        if offset is not None:
            query_params["offset"] = offset
        request = urllib.request.Request(
            url=f"{self._method_url('getUpdates')}?{urllib.parse.urlencode(query_params)}",
            method="GET",
        )
        with self.urlopen(
            request,
            timeout=timeout_seconds + _GET_UPDATES_URLOPEN_TIMEOUT_SLACK_S,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("ok") is not True:
            raise ValueError(f"Telegram getUpdates failed: {payload}")

        local_received_at = time.time()
        messages: list[TelegramIncomingMessage] = []
        next_offset: int | None = offset
        for item in payload.get("result", []):
            update_id = int(item["update_id"])
            next_offset = update_id + 1
            message = item.get("message")
            if not message:
                continue
            text = message.get("text")
            if not text:
                continue
            chat_id = str(message["chat"]["id"])
            from_user = message.get("from") or {}
            raw_from_id = from_user.get("id")
            if raw_from_id is None:
                continue
            channel_user_id = str(raw_from_id)
            raw_date = message.get("date")
            message_date_unix = int(raw_date) if raw_date is not None else None
            messages.append(
                TelegramIncomingMessage(
                    update_id=update_id,
                    chat_id=chat_id,
                    channel_user_id=channel_user_id,
                    text=text,
                    local_received_at=local_received_at,
                    message_date_unix=message_date_unix,
                )
            )
        return messages, next_offset

    def send_message(
        self,
        *,
        chat_id: str,
        text: str,
        parse_mode: TelegramParseMode | None,
    ) -> dict[str, Any]:
        fields: dict[str, str] = {"chat_id": chat_id, "text": text}
        if parse_mode is not None:
            fields["parse_mode"] = parse_mode.value
        body = urllib.parse.urlencode(fields).encode("utf-8")
        request = urllib.request.Request(
            url=self._method_url("sendMessage"),
            method="POST",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with self.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("ok") is not True:
            raise ValueError(f"Telegram sendMessage failed: {payload}")
        return payload
