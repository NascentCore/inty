from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_CAMPAIGN_START_PREFIX = "c_"
_CAMPAIGN_FIELD_SEPARATOR = "_"
_CAMPAIGN_FIELD_COUNT = 3
_START_PARAMETER_MAX_LENGTH = 64
_CAMPAIGN_FIELD_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")


@dataclass(frozen=True)
class CampaignAttribution:
    """First-touch marketing attribution carried by a Telegram ``/start`` deep link.

    Encodes the campaign source, medium and campaign name into one compact
    start parameter so that a storefront funnel can be split per placement.
    """

    source: str
    medium: str
    campaign: str


def _assert_campaign_field(value: str) -> None:
    assert value != ""
    assert _CAMPAIGN_FIELD_PATTERN.match(value) is not None, (
        f"campaign field must match {_CAMPAIGN_FIELD_PATTERN.pattern} "
        f"(no underscore, since it is the field separator): {value!r}"
    )


def encode_campaign_start_parameter(attribution: CampaignAttribution) -> str:
    """Build the ``c_<source>_<medium>_<campaign>`` Telegram start parameter.

    Enforces the Telegram deep-link limits (charset and 64-character cap) so
    that the token is never silently dropped by Telegram at tap time.
    """
    assert attribution is not None
    _assert_campaign_field(attribution.source)
    _assert_campaign_field(attribution.medium)
    _assert_campaign_field(attribution.campaign)
    token = (
        f"{_CAMPAIGN_START_PREFIX}{attribution.source}"
        f"{_CAMPAIGN_FIELD_SEPARATOR}{attribution.medium}"
        f"{_CAMPAIGN_FIELD_SEPARATOR}{attribution.campaign}"
    )
    assert len(token) <= _START_PARAMETER_MAX_LENGTH, (
        f"start parameter exceeds {_START_PARAMETER_MAX_LENGTH} chars: {token!r}"
    )
    return token


def parse_campaign_start_parameter(
    start_parameter: str,
) -> CampaignAttribution | None:
    """Decode a campaign start parameter, or ``None`` when it is not one.

    Only ``c_<source>_<medium>_<campaign>`` with exactly three non-empty,
    charset-valid fields is accepted; anything else (bare onboard, ``agent_``
    promotion links, malformed tokens) returns ``None`` so callers fall back
    to their existing routing.
    """
    assert start_parameter is not None
    if not start_parameter.startswith(_CAMPAIGN_START_PREFIX):
        return None
    if len(start_parameter) > _START_PARAMETER_MAX_LENGTH:
        return None
    body = start_parameter[len(_CAMPAIGN_START_PREFIX) :]
    fields = body.split(
        _CAMPAIGN_FIELD_SEPARATOR, _CAMPAIGN_FIELD_COUNT - 1
    )
    if len(fields) != _CAMPAIGN_FIELD_COUNT:
        return None
    for field in fields:
        if field == "" or _CAMPAIGN_FIELD_PATTERN.match(field) is None:
            return None
    return CampaignAttribution(
        source=fields[0],
        medium=fields[1],
        campaign=fields[2],
    )


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


# TODO(telegram-channel): Ops Telegram channel long-poll uses ``telegram_bot_api``; this service
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
