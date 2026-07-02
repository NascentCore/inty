"""Tests for Telegram campaign start-parameter encode/decode helpers."""

from __future__ import annotations

import pytest

from app.external_services.telegram_bot import (
    CampaignAttribution,
    encode_campaign_start_parameter,
    parse_campaign_start_parameter,
)


def test_encode_campaign_start_parameter_roundtrip() -> None:
    attribution = CampaignAttribution(
        source="ig", medium="story", campaign="summer25"
    )
    token = encode_campaign_start_parameter(attribution)
    assert token == "c_ig_story_summer25"
    assert parse_campaign_start_parameter(token) == attribution


def test_encode_rejects_underscore_in_field() -> None:
    with pytest.raises(AssertionError):
        encode_campaign_start_parameter(
            CampaignAttribution(
                source="ig", medium="story", campaign="summer_25"
            )
        )


def test_encode_rejects_overlong_token() -> None:
    with pytest.raises(AssertionError):
        encode_campaign_start_parameter(
            CampaignAttribution(
                source="s" * 30, medium="m" * 30, campaign="c" * 30
            )
        )


def test_parse_non_campaign_tokens_return_none() -> None:
    assert parse_campaign_start_parameter("onboard") is None
    assert parse_campaign_start_parameter("agent_abc-123") is None
    assert parse_campaign_start_parameter("") is None


def test_parse_malformed_campaign_tokens_return_none() -> None:
    assert parse_campaign_start_parameter("c_ig_story") is None
    assert parse_campaign_start_parameter("c_ig__summer25") is None
    assert parse_campaign_start_parameter("c_ig_story_sum mer") is None
