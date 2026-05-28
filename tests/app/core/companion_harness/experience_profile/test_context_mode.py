from __future__ import annotations

import pytest

from app.core.companion_harness.experience_profile import (
    EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING,
    experience_profile_injects_private_memory,
    experience_profile_system_clause,
    normalize_experience_profile_id,
)


def _assert_clause_heading(out: str) -> None:
    assert out.startswith(f"{EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING}\n\n"), out[:80]


def test_experience_profile_system_clause_intimate_heading_and_body() -> None:
    out = experience_profile_system_clause("intimate")
    _assert_clause_heading(out)
    assert "亲密主会话（intimate）" in out


def test_experience_profile_system_clause_case_insensitive_intimate() -> None:
    out = experience_profile_system_clause("  INTIMATE ")
    _assert_clause_heading(out)
    assert "亲密主会话（intimate）" in out


def test_experience_profile_system_clause_emotional_companion() -> None:
    out = experience_profile_system_clause("emotional_companion")
    _assert_clause_heading(out)
    assert "情感陪伴（emotional_companion）" in out


def test_experience_profile_system_clause_remote_lover() -> None:
    out = experience_profile_system_clause("remote_lover")
    _assert_clause_heading(out)
    assert "异地 AI 伴侣（remote_lover）" in out
    assert "节奏拟人" in out
    assert "口语微信风" in out
    assert "不完美人设" in out


def test_experience_profile_system_clause_unspecific_uses_emotional_companion_body() -> None:
    out = experience_profile_system_clause("unspecific")
    _assert_clause_heading(out)
    assert "情感陪伴（emotional_companion）" in out


def test_experience_profile_system_clause_roleplay() -> None:
    out = experience_profile_system_clause("roleplay")
    _assert_clause_heading(out)
    assert "角色扮演（roleplay）" in out


def test_experience_profile_system_clause_interactive_fiction() -> None:
    out = experience_profile_system_clause("interactive_fiction")
    _assert_clause_heading(out)
    assert "互动小说（interactive_fiction）" in out


def test_experience_profile_system_clause_public() -> None:
    out = experience_profile_system_clause("public")
    _assert_clause_heading(out)
    assert "public。不注入私人记忆层" in out


def test_experience_profile_system_clause_bootstrap() -> None:
    out = experience_profile_system_clause("bootstrap")
    _assert_clause_heading(out)
    assert "交互式关系建立（bootstrap）" in out


def test_experience_profile_system_clause_unknown_mode() -> None:
    out = experience_profile_system_clause("custom_xyz")
    _assert_clause_heading(out)
    assert "custom_xyz。不注入私人记忆层" in out


def test_experience_profile_system_clause_empty_raises() -> None:
    with pytest.raises(ValueError, match="context_mode"):
        experience_profile_system_clause("")


def test_normalize_experience_profile_id_empty_raises() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        normalize_experience_profile_id("")


def test_experience_profile_injects_private_memory_covers_known_ids() -> None:
    assert experience_profile_injects_private_memory("intimate") is True
    assert experience_profile_injects_private_memory("remote_lover") is True
    assert experience_profile_injects_private_memory("unspecific") is True
    assert experience_profile_injects_private_memory("emotional_companion") is True
    assert experience_profile_injects_private_memory("bootstrap") is True
    assert experience_profile_injects_private_memory("public") is False
