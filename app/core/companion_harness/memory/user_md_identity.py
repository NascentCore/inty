"""Keep USER.md «身份信息» slots aligned with structured user profile data.

USER.md stores long-term user knowledge as markdown; identity bullets start as
empty template slots (e.g. 性别、年龄). Structured profile updates (database,
tools, channel provisioning) are mapped here into those bullets without altering
the rest of the document. Unfilled slots can also drive bootstrap hints so the
companion may ask naturally for missing cohort fields without blocking bootstrap
completion.
"""

from __future__ import annotations

from enum import StrEnum

from app.core.companion_harness.memory.memory_store_path_constants import (
    USER_MD_REL as USER_MD_REL,
)
from app.core.companion_harness.memory.memory_store_scope import (
    load_template_seed_text,
)
from app.models.user import Gender
from app.schemas.user import UserProfileSnapshot

USER_PROFILE_SECTION = "## 身份信息"
_IDENTITY_BULLET_PREFIX = "- "
_FULLWIDTH_COLON = "："


class UserIdentityFieldLabel(StrEnum):
    """Canonical USER.md «基础信息» bullet labels."""

    NAME = "姓名"
    GENDER = "性别"
    AGE = "年龄"
    LOCATION = "所在地"
    TIMEZONE = "时区"
    NATIONALITY = "国籍"


COHORT_PROBE_LABELS: tuple[UserIdentityFieldLabel, ...] = (
    UserIdentityFieldLabel.GENDER,
    UserIdentityFieldLabel.AGE,
    UserIdentityFieldLabel.LOCATION,
)


def _identity_line_prefix(label: str) -> str:
    return f"{_IDENTITY_BULLET_PREFIX}{label}{_FULLWIDTH_COLON}"


def _slot_value_after_colon(line: str, label: str) -> str | None:
    prefix = _identity_line_prefix(label)
    stripped = line.strip()
    if not stripped.startswith(prefix):
        return None
    return stripped[len(prefix) :].strip()


def is_identity_slot_unfilled(line: str, label: str) -> bool:
    """True when the line is an identity slot with no user value yet."""
    value = _slot_value_after_colon(line, label)
    if value is None:
        return False
    if value == "":
        return True
    return value.startswith("（")


def list_unfilled_identity_labels(
    text: str,
    labels: tuple[str, ...],
) -> tuple[str, ...]:
    """Return labels whose template slot is still empty in USER.md body."""
    assert labels
    label_set = set(labels)
    unfilled: list[str] = []
    for line in text.splitlines():
        for label in label_set:
            if label in unfilled:
                continue
            if is_identity_slot_unfilled(line, label):
                unfilled.append(label)
    return tuple(label for label in labels if label in unfilled)


def fill_user_md_identity_fields(
    text: str,
    field_values: dict[str, str],
) -> str:
    """Replace «身份信息» template slot lines; create missing lines when section exists."""
    assert field_values
    lines = text.splitlines()
    if USER_PROFILE_SECTION not in lines:
        block_lines = [
            "",
            USER_PROFILE_SECTION,
            "",
            *[
                f"{_identity_line_prefix(label)}{value}"
                for label, value in field_values.items()
            ],
        ]
        return text.rstrip() + "\n".join(block_lines) + "\n"

    section_idx = lines.index(USER_PROFILE_SECTION)
    updated = set[str]()
    for i in range(section_idx + 1, len(lines)):
        if lines[i].startswith("## "):
            break
        for label, value in field_values.items():
            if label in updated:
                continue
            if _slot_value_after_colon(lines[i], label) is not None:
                lines[i] = f"{_identity_line_prefix(label)}{value}"
                updated.add(label)

    missing = [label for label in field_values if label not in updated]
    if missing:
        insert_at = section_idx + 1
        while insert_at < len(lines) and lines[insert_at].strip() == "":
            insert_at += 1
        while insert_at < len(lines) and not lines[insert_at].startswith("## "):
            insert_at += 1
        new_lines = [
            f"{_identity_line_prefix(label)}{field_values[label]}"
            for label in missing
        ]
        for offset, bullet in enumerate(new_lines):
            lines.insert(insert_at + offset, bullet)

    return "\n".join(lines) + "\n"


def _gender_display(gender: Gender) -> str:
    match gender:
        case Gender.MALE:
            return "男"
        case Gender.FEMALE:
            return "女"
        case Gender.OTHER:
            return "其他"


def identity_field_values_for_snapshot(
    snapshot: UserProfileSnapshot,
) -> dict[str, str]:
    """Map UserProfileSnapshot fields to USER.md label → display value."""
    values: dict[str, str] = {}
    if snapshot.gender is not None:
        values[UserIdentityFieldLabel.GENDER] = _gender_display(snapshot.gender)
    if snapshot.age_group is not None:
        values[UserIdentityFieldLabel.AGE] = snapshot.age_group.value
    if snapshot.location is not None and snapshot.location != "":
        values[UserIdentityFieldLabel.LOCATION] = snapshot.location
    if snapshot.iana_timezone is not None and snapshot.iana_timezone != "":
        values[UserIdentityFieldLabel.TIMEZONE] = snapshot.iana_timezone
    return values


def build_cohort_profile_probe_hint(user_md_text: str) -> str:
    """One-line bootstrap hint listing unfilled Telegram cohort identity slots."""
    cohort_labels = tuple(label.value for label in COHORT_PROBE_LABELS)
    unfilled = list_unfilled_identity_labels(user_md_text, cohort_labels)
    if not unfilled:
        return ""
    joined = "、".join(unfilled)
    return (
        f"USER.md 身份信息中仍待自然了解的字段：{joined}。"
        "每次只问一个；用户不愿回答时不要强求；勿因此延迟 bootstrap complete。"
    )


def load_user_md_template_text() -> str:
    """Load package USER.md seed template for tests and sync checks."""
    return load_template_seed_text(USER_MD_REL)
