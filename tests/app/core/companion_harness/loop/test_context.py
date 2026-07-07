"""Tests for settled ``loop/context.py`` builders (non-bootstrap paths)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
)
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    LangsmithLlmSource,
)
from app.core.companion_harness.loop.config import (
    BatchUserMessagesLlmCallMode,
    UserTurnLlmLoopMode,
    resolved_user_turn_batch_messages_llm_call_mode,
    resolved_user_turn_llm_loop_mode,
)
from app.core.companion_harness.loop.context import (
    build_settled_dual_llm_user_chat_loop_context,
    build_settled_user_chat_loop_context,
)
from app.core.companion_harness.loop.track_policy import TRACK_POLICY
from app.core.companion_harness.prompting.bundle import PromptBundle

from tests.app.core.companion_harness.loop.context_builder_test_support import (
    base_user_chat_loop_builder_kwargs,
    loop_execution_for_track,
)


def test_settled_user_chat_loop_context_uses_single_completion_source() -> None:
    context = build_settled_user_chat_loop_context(
        **base_user_chat_loop_builder_kwargs(),
        after_tool_messages_appended=MagicMock(),
        execution=loop_execution_for_track(
            track=CompanionTurnTrack.USER_CHAT,
            user_text="hi",
            has_openai_tools=False,
        ),
    )

    execution = context.execution
    assert (
        execution.write_allowlist
        == TRACK_POLICY[CompanionTurnTrack.USER_CHAT].write_allowlist
    )
    assert execution.foreground_source == LangsmithLlmSource.SINGLE_COMPLETION
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
        execution=loop_execution_for_track(
            track=CompanionTurnTrack.USER_CHAT,
            user_text="hi",
            has_openai_tools=False,
        ),
    )

    assert context.companion_turn_track == CompanionTurnTrack.USER_CHAT
    assert context.dual_llm_chat_msgs == chat_msgs
    assert context.dual_llm_tool_msgs == tool_msgs
    assert context.prompt_plan is None


def test_resolved_user_turn_llm_loop_mode_defaults_to_dual_llm() -> None:
    assert resolved_user_turn_llm_loop_mode() == UserTurnLlmLoopMode.DUAL_LLM


def test_resolved_user_turn_batch_messages_mode_defaults_to_multi() -> None:
    assert (
        resolved_user_turn_batch_messages_llm_call_mode()
        == BatchUserMessagesLlmCallMode.MULTI_USER_MESSAGES
    )
