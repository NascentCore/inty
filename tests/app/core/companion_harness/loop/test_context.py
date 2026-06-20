"""Tests for settled ``loop/context.py`` builders (non-bootstrap paths)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
)
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE,
    SOURCE_SINGLE_COMPLETION,
)
from app.core.companion_harness.loop.config import (
    UserTurnLlmLoopMode,
    resolved_user_turn_llm_loop_mode,
)
from app.core.companion_harness.loop.context import (
    build_settled_dual_llm_user_chat_loop_context,
    build_settled_user_chat_loop_context,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
)
from app.core.companion_harness.prompting.bundle import PromptBundle

from tests.app.core.companion_harness.loop.context_builder_test_support import (
    base_user_chat_loop_builder_kwargs,
)


def test_settled_user_chat_loop_context_uses_single_completion_source() -> None:
    context = build_settled_user_chat_loop_context(
        **base_user_chat_loop_builder_kwargs(),
        after_tool_messages_appended=MagicMock(),
    )

    assert context.write_allowlist == MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST
    assert context.langsmith.foreground_source == SOURCE_SINGLE_COMPLETION
    assert context.companion_turn_track == CompanionTurnTrack.USER_CHAT


def test_settled_dual_llm_context_packages_prebuilt_stacks() -> None:
    chat_msgs = ({"role": "user", "content": "hi"},)
    tool_msgs = ({"role": "user", "content": "hi"},)

    context = build_settled_dual_llm_user_chat_loop_context(
        **base_user_chat_loop_builder_kwargs(),
        dual_llm_chat_msgs=chat_msgs,
        dual_llm_tool_msgs=tool_msgs,
        prompt_bundle=PromptBundle(
            identity="",
            soul="",
            user_md="",
            memory_md="",
        ),
        context_meta=ContextMeta(),
    )

    assert context.companion_turn_track == CompanionTurnTrack.USER_CHAT
    assert context.dual_llm_chat_msgs == chat_msgs
    assert context.dual_llm_tool_msgs == tool_msgs
    assert (
        context.langsmith.foreground_source
        == SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE
    )
    assert context.prompt_plan is None


def test_resolved_user_turn_llm_loop_mode_defaults_to_dual_llm() -> None:
    assert resolved_user_turn_llm_loop_mode() == UserTurnLlmLoopMode.DUAL_LLM
