from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .living_companion import ChannelTransport, ChannelType, OutboundEvent


@dataclass(frozen=True)
class TelegramIncomingMessage:
    update_id: int
    chat_id: str
    text: str


@dataclass
class TelegramBotApi:
    bot_token: str
    urlopen: Any = urllib.request.urlopen
    base_url: str = "https://api.telegram.org"

    def _method_url(self, method_name: str) -> str:
        return f"{self.base_url}/bot{self.bot_token}/{method_name}"

    def get_text_messages(
        self,
        *,
        offset: int | None,
        timeout_seconds: int,
    ) -> tuple[list[TelegramIncomingMessage], int | None]:
        query_params: dict[str, str | int] = {"timeout": max(1, timeout_seconds)}
        if offset is not None:
            query_params["offset"] = offset
        request = urllib.request.Request(
            url=f"{self._method_url('getUpdates')}?{urllib.parse.urlencode(query_params)}",
            method="GET",
        )
        with self.urlopen(request, timeout=timeout_seconds + 5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("ok") is not True:
            raise ValueError(f"Telegram getUpdates failed: {payload}")

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
            messages.append(
                TelegramIncomingMessage(update_id=update_id, chat_id=chat_id, text=text)
            )
        return messages, next_offset

    def send_message(self, *, chat_id: str, text: str) -> dict[str, Any]:
        body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode(
            "utf-8"
        )
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


@dataclass
class TelegramChannelTransport(ChannelTransport):
    bot_api: TelegramBotApi

    def send(
        self,
        *,
        channel: ChannelType,
        recipient: str,
        content: str,
        metadata: dict[str, str],
    ) -> OutboundEvent:
        # In Telegram mode we always deliver to the Telegram chat id recipient.
        self.bot_api.send_message(chat_id=recipient, text=content)
        return OutboundEvent(
            channel=channel,
            recipient=recipient,
            content=content,
            metadata=metadata,
        )
