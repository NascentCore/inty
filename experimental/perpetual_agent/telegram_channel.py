from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

# urllib timeout must exceed Telegram's long-poll ``timeout`` query param.
_GET_UPDATES_URLOPEN_TIMEOUT_SLACK_S = 5


def format_epoch_for_local_log(
    ts: float | int | None, *, missing: str = "n/a"
) -> str:
    """Format Unix epoch seconds for logs: convert to **system local** timezone with offset.

    Use for ``time.time()`` (local receive) and Telegram ``message.date`` (UTC unix).
    """
    if ts is None:
        return missing
    dt = datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone()
    return dt.strftime("%Y-%m-%d %H:%M:%S %z")


@dataclass(frozen=True)
class TelegramIncomingMessage:
    update_id: int
    chat_id: str
    text: str
    # Wall time when this process finished parsing the getUpdates payload (seconds since epoch).
    local_received_at: float
    # Telegram Message.date (Unix UTC), if present in the update.
    message_date_unix: int | None = None


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
        # Telegram: timeout=0 is short polling; >0 is long-poll up to that many seconds.
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

        # One wall clock for the whole parsed payload (not per update row) so batch latency is consistent.
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
            raw_date = message.get("date")
            message_date_unix = int(raw_date) if raw_date is not None else None
            messages.append(
                TelegramIncomingMessage(
                    update_id=update_id,
                    chat_id=chat_id,
                    text=text,
                    local_received_at=local_received_at,
                    message_date_unix=message_date_unix,
                )
            )
        return messages, next_offset

    def send_message(self, *, chat_id: str, text: str) -> dict[str, Any]:
        body = urllib.parse.urlencode(
            {"chat_id": chat_id, "text": text}
        ).encode("utf-8")
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
