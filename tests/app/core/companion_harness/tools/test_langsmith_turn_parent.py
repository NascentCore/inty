"""Regression: companion turn groups LangSmith LLM runs under one parent trace."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch


from app.core.companion_harness.companion.llm_chat_runtime import (
    companion_turn_langsmith_parent_trace_id_str,
    create_companion_turn_root_run,
    end_companion_turn_root_run_safe,
)
from app.core.companion_harness.companion.models import (
    InnerTickActivity,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
    LangsmithChannelSource,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.utils.models_catalog import resolve_chat_text_model

_APP_SLICE = CompanionTurnLangsmithSlice.app_default()


def _idle_tool_bg() -> threading.Event:
    ev = threading.Event()
    ev.set()
    return ev


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=False,
)
def test_create_companion_turn_root_run_returns_none_when_disabled(
    _mock: MagicMock,
) -> None:
    assert (
        create_companion_turn_root_run(
            inty_trace_id="t1",
            user_msg_uuid="u1",
            chat_model=resolve_chat_text_model("stub/disabled-chat"),
            tool_model=resolve_chat_text_model("stub/disabled-tool"),
            langsmith_slice=_APP_SLICE,
        )
        is None
    )


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
def test_create_companion_turn_root_run_skips_kernel_placeholder_models(
    _en: MagicMock,
) -> None:
    assert (
        create_companion_turn_root_run(
            inty_trace_id="t1",
            user_msg_uuid="u1",
            chat_model=resolve_chat_text_model("m/chat"),
            tool_model=resolve_chat_text_model("m/tool"),
            langsmith_slice=_APP_SLICE,
        )
        is None
    )


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_builds_and_posts_run_tree(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    out = create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        user_id="u-42",
        companion_id="c-7",
        langsmith_slice=_APP_SLICE,
    )
    assert out is mock_root
    mock_rt_cls.assert_called_once()
    kwargs = mock_rt_cls.call_args.kwargs
    assert kwargs["name"] == "agentic_companion_user_turn user=u-42 agent=c-7"
    assert kwargs["tags"] == [
        "agentic_companion",
        "user_turn",
        "explicit_user_message",
        "runtime_channel_app_ws",
    ]
    assert kwargs["inputs"]["inty_trace_id"] == "t1"
    assert kwargs["inputs"]["user_msg_uuid"] == "u1"
    assert kwargs["inputs"]["chat_model"] == "stub/chat-route"
    assert kwargs["inputs"]["tool_model"] == "stub/tool-route"
    assert isinstance(kwargs["inputs"]["chat_model_catalog"], dict)
    assert isinstance(kwargs["inputs"]["tool_model_catalog"], dict)
    assert kwargs["inputs"]["user_id"] == "u-42"
    assert kwargs["inputs"]["companion_id"] == "c-7"
    assert kwargs["inputs"]["inty_turn_lane"] == "explicit_user_message"
    assert "inner_tick_activity" not in kwargs["inputs"]
    assert (
        kwargs["extra"]["metadata"]["ls_model_name"]
        == "stub/chat-route | stub/tool-route"
    )
    assert kwargs["extra"]["metadata"]["inty_user_id"] == "u-42"
    assert kwargs["extra"]["metadata"]["inty_companion_id"] == "c-7"
    assert (
        kwargs["extra"]["metadata"]["inty_turn_lane"] == "explicit_user_message"
    )
    assert "inner_tick_activity" not in kwargs["extra"]["metadata"]
    mock_root.post.assert_called_once()
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_name_uses_unknown_when_ids_empty(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        langsmith_slice=_APP_SLICE,
    )
    kwargs = mock_rt_cls.call_args.kwargs
    assert (
        kwargs["name"]
        == "agentic_companion_user_turn user=unknown agent=unknown"
    )
    assert kwargs["inputs"]["user_id"] == ""
    assert kwargs["inputs"]["companion_id"] == ""
    assert kwargs["inputs"]["inty_turn_lane"] == "explicit_user_message"
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_implicit_signed_on_lane(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        user_id="u1",
        companion_id="a1",
        implicit_user_signed_on=True,
        langsmith_slice=_APP_SLICE,
    )
    kwargs = mock_rt_cls.call_args.kwargs
    assert kwargs["name"] == "agentic_companion_implicit_turn user=u1 agent=a1"
    assert kwargs["tags"] == [
        "agentic_companion",
        "implicit_turn",
        "implicit_user_signed_on",
        "runtime_channel_app_ws",
    ]
    assert kwargs["inputs"]["inty_turn_lane"] == "implicit_turn"
    assert kwargs["inputs"]["implicit_signal"] == "implicit_user_signed_on"
    assert kwargs["extra"]["metadata"]["inty_turn_lane"] == "implicit_turn"
    assert (
        kwargs["extra"]["metadata"]["implicit_signal"]
        == "implicit_user_signed_on"
    )
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_inner_tick_monolog_lane(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        user_id="u1",
        companion_id="a1",
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.MONOLOG,
        transcript_newest_message_uuid="tail-uuid-1",
        langsmith_slice=_APP_SLICE,
    )
    kwargs = mock_rt_cls.call_args.kwargs
    assert (
        kwargs["name"]
        == "agentic_companion_inner_tick monolog user=u1 agent=a1"
    )
    assert kwargs["tags"] == [
        "agentic_companion",
        "inner_tick",
        "runtime_channel_app_ws",
    ]
    assert kwargs["inputs"]["inty_turn_lane"] == "inner_tick"
    assert kwargs["inputs"]["inner_tick_activity"] == "monolog"
    assert kwargs["inputs"]["transcript_newest_message_uuid"] == "tail-uuid-1"
    assert kwargs["extra"]["metadata"]["inty_turn_lane"] == "inner_tick"
    assert kwargs["extra"]["metadata"]["inner_tick_activity"] == "monolog"
    assert (
        kwargs["extra"]["metadata"]["transcript_newest_message_uuid"]
        == "tail-uuid-1"
    )
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_inner_tick_proactive_lane(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        user_id="u1",
        companion_id="a1",
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.PROACTIVE_CHAT,
        transcript_newest_message_uuid="tail-uuid-2",
        langsmith_slice=_APP_SLICE,
    )
    kwargs = mock_rt_cls.call_args.kwargs
    assert (
        kwargs["name"]
        == "agentic_companion_inner_tick proactive_chat user=u1 agent=a1"
    )
    assert kwargs["inputs"]["inner_tick_activity"] == "proactive_chat"
    assert kwargs["inputs"]["transcript_newest_message_uuid"] == "tail-uuid-2"
    assert (
        kwargs["extra"]["metadata"]["inner_tick_activity"] == "proactive_chat"
    )
    assert (
        kwargs["extra"]["metadata"]["transcript_newest_message_uuid"]
        == "tail-uuid-2"
    )
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_includes_runtime_channel(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    telegram_slice = CompanionTurnLangsmithSlice.from_channel(
        ChannelKind.TELEGRAM,
        LangsmithChannelSource.EXPLICIT_TURN,
    )
    create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        user_id="u1",
        companion_id="a1",
        langsmith_slice=telegram_slice,
    )
    kwargs = mock_rt_cls.call_args.kwargs
    assert kwargs["inputs"]["runtime_channel"] == "telegram"
    assert "runtime_channel_telegram" in kwargs["tags"]
    assert kwargs["extra"]["metadata"]["inty_runtime_channel"] == "telegram"
    assert (
        kwargs["extra"]["metadata"]["inty_runtime_channel_source"]
        == LangsmithChannelSource.EXPLICIT_TURN.value
    )
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_inner_tick_dreaming_lane(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="boundary-u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        user_id="u1",
        companion_id="a1",
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.DREAMING,
        transcript_newest_message_uuid="boundary-u1",
        langsmith_slice=_APP_SLICE,
    )
    kwargs = mock_rt_cls.call_args.kwargs
    assert (
        kwargs["name"]
        == "agentic_companion_inner_tick dreaming user=u1 agent=a1"
    )
    assert kwargs["inputs"]["inner_tick_activity"] == "dreaming"
    assert kwargs["inputs"]["transcript_newest_message_uuid"] == "boundary-u1"
    assert kwargs["extra"]["metadata"]["inner_tick_activity"] == "dreaming"
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


def test_companion_turn_langsmith_parent_trace_id_str_empty_for_none() -> None:
    assert companion_turn_langsmith_parent_trace_id_str(None) == ""


def test_end_companion_turn_root_run_safe_noop_for_none() -> None:
    end_companion_turn_root_run_safe(None)
