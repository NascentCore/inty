"""Regression tests for best-effort LangSmith completion metadata enrichment."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from loguru import logger

from app.core.companion_harness.llm.langsmith_completion_enrich import (
    _LS_WRAPPED_LLM_RUN_ID,
    completion_with_langsmith_trace_id,
    langsmith_llm_run_id_from_completion,
    langsmith_trace_id_from_completion,
)


class _BrokenString:
    def __str__(self) -> str:
        raise RuntimeError("cannot stringify langsmith id")


class _CompletionWithBrokenRunId:
    langsmith_llm_run_id = _BrokenString()


class _CompletionWithBrokenTraceId:
    langsmith_trace_id = _BrokenString()


class _CompletionWithFailingCopy:
    langsmith_trace_id = None

    def model_copy(
        self, *, update: dict[str, Any]
    ) -> "_CompletionWithFailingCopy":
        assert update == {"langsmith_llm_run_id": "llm-run-1"}
        raise RuntimeError("copy failed")


def _debug_messages_from(action: Callable[[], None]) -> list[str]:
    messages: list[str] = []

    def _sink(message: Any) -> None:
        messages.append(message.record["message"])

    sink_id = logger.add(_sink, level="DEBUG", format="{message}")
    try:
        action()
    finally:
        logger.remove(sink_id)
    return messages


def test_langsmith_llm_run_id_extraction_logs_unreadable_value() -> None:
    result = ""

    def _act() -> None:
        nonlocal result
        result = langsmith_llm_run_id_from_completion(
            _CompletionWithBrokenRunId()
        )

    messages = _debug_messages_from(_act)

    assert result == ""
    assert messages == [
        "langsmith llm run id extraction skipped: cannot stringify langsmith id"
    ]


def test_langsmith_trace_id_extraction_logs_unreadable_value() -> None:
    result = ""

    def _act() -> None:
        nonlocal result
        result = langsmith_trace_id_from_completion(
            _CompletionWithBrokenTraceId()
        )

    messages = _debug_messages_from(_act)

    assert result == ""
    assert messages == [
        "langsmith trace id extraction skipped: cannot stringify langsmith id"
    ]


def test_completion_enrichment_logs_model_copy_failure() -> None:
    raw = _CompletionWithFailingCopy()
    result: object | None = None
    token = _LS_WRAPPED_LLM_RUN_ID.set("llm-run-1")

    def _act() -> None:
        nonlocal result
        result = completion_with_langsmith_trace_id(raw)

    try:
        messages = _debug_messages_from(_act)
    finally:
        _LS_WRAPPED_LLM_RUN_ID.reset(token)

    assert result is raw
    assert messages == ["langsmith completion enrichment skipped: copy failed"]
