"""Tests for USER.md timezone inference."""

from __future__ import annotations

from app.core.companion_harness.memory.user_timezone_from_user_md import (
    infer_iana_timezone_from_user_md,
)


def test_infer_timezone_from_labeled_bullet() -> None:
    user_md = """# USER

## 身份信息

- 时区：Asia/Shanghai（记录日期 2026-06-13）
"""
    assert infer_iana_timezone_from_user_md(user_md) == "Asia/Shanghai"


def test_infer_timezone_english_label() -> None:
    user_md = """## 身份信息

- timezone: Europe/Berlin
"""
    assert infer_iana_timezone_from_user_md(user_md) == "Europe/Berlin"


def test_infer_timezone_returns_none_without_identity_facts() -> None:
    user_md = """## 偏好与习惯

- 喜欢夜聊
"""
    assert infer_iana_timezone_from_user_md(user_md) is None
