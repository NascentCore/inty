from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class TelegramBotProvisionResult:
    bot_id: int
    bot_username: str
    start_parameter: str
    deep_link: str
    provisioned_at: str

    def to_extensions_payload(self) -> dict[str, str | int]:
        return {
            "status": "provisioned",
            "bot_id": self.bot_id,
            "bot_username": self.bot_username,
            "start_parameter": self.start_parameter,
            "deep_link": self.deep_link,
            "provisioned_at": self.provisioned_at,
        }


# TODO(telegram-demo): Ops telegram-demo long-poll uses ``telegram_bot_api``; this service
# remains for public-agent promotion deep links only.
# TODO(telegram-dedicated-bot-bonding): Per-agent bot token + triage portal — #3361 (epic #3395)


@dataclass
class TelegramBotService:
    bot_token: str
    urlopen: Any = urllib.request.urlopen
    base_url: str = "https://api.telegram.org"

    def _method_url(self, method_name: str) -> str:
        return f"{self.base_url}/bot{self.bot_token}/{method_name}"

    def _get_me(self) -> dict[str, Any]:
        request = urllib.request.Request(
            url=self._method_url("getMe"),
            method="GET",
        )
        with self.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("ok") is not True:
            raise RuntimeError(f"Telegram getMe failed: {payload}")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise RuntimeError(f"Telegram getMe invalid result: {payload}")
        return result

    def provision_agent_bot(
        self,
        *,
        agent_id: str,
    ) -> TelegramBotProvisionResult:
        me = self._get_me()
        bot_id_raw = me.get("id")
        username_raw = me.get("username")
        if not isinstance(bot_id_raw, int):
            raise RuntimeError(f"Telegram bot id missing or invalid: {me}")
        if not isinstance(username_raw, str) or not username_raw.strip():
            raise RuntimeError(
                f"Telegram bot username missing or invalid: {me}"
            )

        start_parameter = f"agent_{agent_id}"
        deep_link = (
            f"https://t.me/{username_raw}"
            f"?start={urllib.parse.quote(start_parameter, safe='')}"
        )
        provisioned_at = datetime.now(timezone.utc).isoformat()
        return TelegramBotProvisionResult(
            bot_id=bot_id_raw,
            bot_username=username_raw,
            start_parameter=start_parameter,
            deep_link=deep_link,
            provisioned_at=provisioned_at,
        )
