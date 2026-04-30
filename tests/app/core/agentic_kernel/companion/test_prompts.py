from __future__ import annotations

from app.core.agentic_kernel.companion.models import ContextMeta, PromptBundle
from app.core.agentic_kernel.companion.prompts import build_system_prompt


def _minimal_bundle() -> PromptBundle:
    return PromptBundle(
        identity="id",
        soul="sl",
        user_md="usr",
        memory_md="mem",
    )


def test_build_system_prompt_basic() -> None:
    text = build_system_prompt(
        _minimal_bundle(),
        ContextMeta(),
    )
    assert "情感伴侣型助手" in text
    assert "## IDENTITY" in text
    assert "## SOUL" in text
    assert "## USER" in text
    assert "亲密主会话" in text
    assert "仅自然语言文本回复" in text


def test_build_system_prompt_heartbeat() -> None:
    text = build_system_prompt(
        _minimal_bundle(),
        ContextMeta(),
        heartbeat_turn=True,
    )
    assert "## 本轮（陪伴心跳）" in text
    assert "用户尚未发送新消息" in text


def test_build_system_prompt_tools() -> None:
    text = build_system_prompt(
        _minimal_bundle(),
        ContextMeta(),
        enable_tools=True,
    )
    assert "user_profile_record" in text
    assert "workspace_read_file" in text


def test_build_system_prompt_interactive_bootstrap_injects_spec() -> None:
    text = build_system_prompt(
        _minimal_bundle(),
        ContextMeta(workspace_bootstrap_user_interactive_completed=False),
        enable_tools=True,
        interactive_bootstrap_active=True,
    )
    assert "INTERACTIVE_BOOTSTRAP" in text
    assert "companion_update_prompt_slice" in text
    assert "companion_bootstrap_user_interactive_complete" in text


def test_build_system_prompt_intimate_memory() -> None:
    b = PromptBundle(
        identity="i",
        soul="s",
        user_md="u",
        memory_md="long mem",
        memory_raw_diary_today_md="raw today",
        memory_day_summary_today_md="summary today",
    )
    text = build_system_prompt(b, ContextMeta(context_mode="intimate"))
    assert "## MEMORY 日记（今日原始）" in text
    assert "raw today" in text
    assert "## MEMORY 当日总结" in text
    assert "summary today" in text
    assert "## MEMORY（长期记忆定稿）" in text
    assert "long mem" in text


def test_build_system_prompt_emotional_companion_memory_same_as_intimate() -> None:
    b = PromptBundle(
        identity="i",
        soul="s",
        user_md="u",
        memory_md="long mem",
        memory_raw_diary_today_md="raw today",
        memory_day_summary_today_md="summary today",
    )
    text = build_system_prompt(b, ContextMeta(context_mode="emotional_companion"))
    assert "## MEMORY 日记（今日原始）" in text
    assert "raw today" in text
    assert "## MEMORY（长期记忆定稿）" in text
    assert "long mem" in text
    assert "情感陪伴" in text


def test_build_system_prompt_non_intimate_no_memory() -> None:
    b = PromptBundle(
        identity="i",
        soul="s",
        user_md="u",
        memory_md="should not appear",
        memory_raw_diary_today_md="raw",
        memory_day_summary_today_md="sum",
    )
    text = build_system_prompt(
        b,
        ContextMeta(context_mode="public"),
    )
    assert "should not appear" not in text
    assert "raw" not in text
    assert "sum" not in text


def test_build_system_prompt_significance_slice_when_flag() -> None:
    b = _minimal_bundle()
    b.significance_perception_md = "Custom slice body."
    text = build_system_prompt(
        b,
        ContextMeta(),
        enable_user_profile_tool=True,
        include_repl_image_generation_contract=False,
        include_significance_perception_slice=True,
    )
    assert "## SIGNIFICANCE PERCEPTION" in text
    assert "Custom slice body." in text
    assert "Dual-LLM chat branch: structured reply envelope" in text
