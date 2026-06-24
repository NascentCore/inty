"""Tests for USER.md identity inline-fill helpers."""

from __future__ import annotations

from app.core.companion_harness.memory.user_md_identity import (
    COHORT_PROBE_LABELS,
    USER_PROFILE_SECTION,
    UserIdentityFieldLabel,
    build_cohort_profile_probe_hint,
    fill_user_md_identity_fields,
    identity_field_values_for_snapshot,
    is_identity_slot_unfilled,
    list_unfilled_identity_labels,
    load_user_md_template_text,
)
from app.models.user import Gender
from app.schemas.user import UserAgeGroup, UserProfileSnapshot


def _template_body() -> str:
    return load_user_md_template_text()


def test_is_identity_slot_unfilled_empty_and_hint_only() -> None:
    assert is_identity_slot_unfilled("- 性别：", UserIdentityFieldLabel.GENDER)
    assert is_identity_slot_unfilled(
        "- 年龄：（分档 18–25 / 26–35）",
        UserIdentityFieldLabel.AGE,
    )
    assert not is_identity_slot_unfilled(
        "- 性别：男", UserIdentityFieldLabel.GENDER
    )
    assert not is_identity_slot_unfilled(
        "- 所在地：NYC",
        UserIdentityFieldLabel.LOCATION,
    )


def test_fill_user_md_identity_fields_single_and_idempotent() -> None:
    text = _template_body()
    merged = fill_user_md_identity_fields(
        text,
        {UserIdentityFieldLabel.GENDER: "男"},
    )
    assert "- 性别：男" in merged.splitlines()
    assert "- 性别：" not in merged.splitlines()
    again = fill_user_md_identity_fields(
        merged,
        {UserIdentityFieldLabel.GENDER: "女"},
    )
    assert "- 性别：女" in again.splitlines()
    assert "- 性别：男" not in again.splitlines()


def test_fill_user_md_identity_fields_multiple() -> None:
    merged = fill_user_md_identity_fields(
        _template_body(),
        {
            UserIdentityFieldLabel.GENDER: "女",
            UserIdentityFieldLabel.AGE: "18-25",
            UserIdentityFieldLabel.LOCATION: "NYC",
        },
    )
    lines = merged.splitlines()
    assert "- 性别：女" in lines
    assert "- 年龄：18-25" in lines
    assert "- 所在地：NYC" in lines


def test_list_unfilled_identity_labels_on_template() -> None:
    unfilled = list_unfilled_identity_labels(
        _template_body(),
        tuple(label.value for label in COHORT_PROBE_LABELS),
    )
    assert unfilled == (
        UserIdentityFieldLabel.GENDER,
        UserIdentityFieldLabel.AGE,
        UserIdentityFieldLabel.LOCATION,
    )


def test_build_cohort_profile_probe_hint_partial_fill() -> None:
    partial = fill_user_md_identity_fields(
        _template_body(),
        {UserIdentityFieldLabel.GENDER: "男"},
    )
    hint = build_cohort_profile_probe_hint(partial)
    assert UserIdentityFieldLabel.AGE in hint
    assert UserIdentityFieldLabel.LOCATION in hint
    assert UserIdentityFieldLabel.GENDER not in hint


def test_build_cohort_profile_probe_hint_empty_when_filled() -> None:
    filled = fill_user_md_identity_fields(
        _template_body(),
        {
            UserIdentityFieldLabel.GENDER: "男",
            UserIdentityFieldLabel.AGE: "26-35",
            UserIdentityFieldLabel.LOCATION: "Shanghai",
        },
    )
    assert build_cohort_profile_probe_hint(filled) == ""


def test_identity_field_values_for_snapshot_partial_fields() -> None:
    snapshot = UserProfileSnapshot(
        gender=Gender.FEMALE,
        age_group=UserAgeGroup.AGE_18_25,
        location=None,
        iana_timezone=None,
    )
    values = identity_field_values_for_snapshot(snapshot)
    assert values[UserIdentityFieldLabel.GENDER] == "女"
    assert values[UserIdentityFieldLabel.AGE] == "18-25"


def test_fill_creates_section_when_missing() -> None:
    merged = fill_user_md_identity_fields(
        "# 用户档案\n",
        {UserIdentityFieldLabel.GENDER: "男"},
    )
    lines = merged.splitlines()
    assert USER_PROFILE_SECTION in lines
    assert "- 性别：男" in lines


def test_cohort_probe_labels_present_in_user_template() -> None:
    template = _template_body()
    for label in COHORT_PROBE_LABELS:
        assert f"- {label.value}：" in template
