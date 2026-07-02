"""Tests for ``parse_start_payload``."""

from __future__ import annotations

from app.external_services.telegram_bot import CampaignAttribution
from backend.ops.telegram_channel.binding import (
    StartPayloadKind,
    parse_start_payload,
)


def test_parse_start_payload_bare_start() -> None:
    payload = parse_start_payload("/start")
    assert payload.kind == StartPayloadKind.ONBOARD


def test_parse_start_payload_bare_start_with_bot_username() -> None:
    payload = parse_start_payload("/start@MyBot")
    assert payload.kind == StartPayloadKind.ONBOARD


def test_parse_start_payload_onboard_deep_link() -> None:
    payload = parse_start_payload("/start onboard")
    assert payload.kind == StartPayloadKind.ONBOARD


def test_parse_start_payload_onboard_deep_link_with_bot_username() -> None:
    payload = parse_start_payload("/start@MyBot onboard")
    assert payload.kind == StartPayloadKind.ONBOARD


def test_parse_start_payload_unknown_start_token_is_none() -> None:
    payload = parse_start_payload("/start agent_abc-123")
    assert payload.kind == StartPayloadKind.NONE
    assert payload.campaign is None


def test_parse_start_payload_none() -> None:
    payload = parse_start_payload("hello")
    assert payload.kind == StartPayloadKind.NONE
    assert payload.campaign is None


def test_parse_start_payload_campaign_onboard() -> None:
    payload = parse_start_payload("/start c_ig_story_summer25")
    assert payload.kind == StartPayloadKind.ONBOARD
    assert payload.campaign == CampaignAttribution(
        source="ig", medium="story", campaign="summer25"
    )


def test_parse_start_payload_campaign_onboard_with_bot_username() -> None:
    payload = parse_start_payload("/start@MyBot c_web_banner_launch")
    assert payload.kind == StartPayloadKind.ONBOARD
    assert payload.campaign == CampaignAttribution(
        source="web", medium="banner", campaign="launch"
    )


def test_parse_start_payload_malformed_campaign_is_none() -> None:
    payload = parse_start_payload("/start c_ig_story")
    assert payload.kind == StartPayloadKind.NONE
    assert payload.campaign is None
