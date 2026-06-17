"""LangSmith trace replay for loop parity tests (fake LLM, no network).

Fixture: ``traces/019ec520-b7b5-7ab1-bf7d-38f5c9730dda.json`` (llm runs only).

Regenerate from repo root::

    source .venv/bin/activate
    python .cursor/skills/scripts/download_run.py \\
      --trace-id 019ec520-b7b5-7ab1-bf7d-38f5c9730dda \\
      -o /tmp/trace.json
    # then filter run_type==llm into traces/019ec520-b7b5-7ab1-bf7d-38f5c9730dda.json

This trace's intermediate LLM rounds have empty ``message.content``; tests may
normalize interim visible text from tool ``arguments.text`` to exercise the
delivery pipeline (not to reproduce production interim copy for that trace).

TODO(!3457): Promote interim-visible-text helper so user chat keeps talking while
tools execute — parent !3456.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_TOOL_BACKGROUND_ROUTING_FALLBACK,
)
from app.core.companion_harness.loop.parity.fixtures import (
    FakeSyncToolLoopLLMClient,
)
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model

_TRACE_ID = "019ec520-b7b5-7ab1-bf7d-38f5c9730dda"
_TRACE_FIXTURE = (
    Path(__file__).resolve().parent / "traces" / f"{_TRACE_ID}.json"
)
_IN_TURN_REPLAY_LLM_COUNT = 3
_EXCLUDED_RUN_NAMES = frozenset({SOURCE_TOOL_BACKGROUND_ROUTING_FALLBACK})


def trace_fixture_path() -> Path:
    """Committed LangSmith llm-runs JSON for in-turn replay tests."""
    return _TRACE_FIXTURE


def load_trace_fixture() -> dict[str, Any]:
    """Load committed trace JSON; raises if fixture missing."""
    path = trace_fixture_path()
    assert path.is_file(), f"missing trace fixture: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def llm_runs_for_in_turn_replay(trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Sorted LLM runs for 1-LLM tool loop replay (excludes routing fallback)."""
    runs = [
        r
        for r in trace.get("runs", [])
        if r.get("run_type") == "llm"
        and r.get("name") not in _EXCLUDED_RUN_NAMES
    ]
    runs.sort(key=lambda r: r.get("start_time") or "")
    assert len(runs) >= _IN_TURN_REPLAY_LLM_COUNT
    return runs[:_IN_TURN_REPLAY_LLM_COUNT]


def completion_from_langsmith_outputs(
    outputs: dict[str, Any],
) -> SimpleNamespace:
    """Map LangSmith chat completion outputs to OpenAI-shaped ``SimpleNamespace``."""
    choices = outputs.get("choices")
    assert isinstance(choices, list) and choices
    choice = choices[0]
    raw_msg = choice.get("message") or {}
    tool_calls_raw = raw_msg.get("tool_calls")
    tool_calls: list[SimpleNamespace] | None = None
    if tool_calls_raw:
        tool_calls = []
        for tc in tool_calls_raw:
            fn = tc.get("function") or {}
            tool_calls.append(
                SimpleNamespace(
                    id=tc.get("id"),
                    type=tc.get("type", "function"),
                    function=SimpleNamespace(
                        name=fn.get("name"),
                        arguments=fn.get("arguments") or "",
                    ),
                )
            )
    message = SimpleNamespace(
        content=raw_msg.get("content"),
        tool_calls=tool_calls,
    )
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=message,
                finish_reason=choice.get("finish_reason"),
            )
        ],
        model=outputs.get("model"),
        usage=outputs.get("usage"),
    )


def _tool_argument_text(raw_arguments: str) -> str:
    try:
        payload = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, dict):
        return ""
    text = payload.get("text")
    if not isinstance(text, str):
        return ""
    return text.strip()


def interim_visible_text(completion: SimpleNamespace) -> str:
    """User-visible interim text: ``message.content`` or first tool ``arguments.text``."""
    message = completion.choices[0].message
    body = (message.content or "").strip()
    if body:
        return body
    tool_calls = getattr(message, "tool_calls", None) or []
    if not tool_calls:
        return ""
    fn = tool_calls[0].function
    return _tool_argument_text(fn.arguments or "")


def normalize_completion_for_interim(
    completion: SimpleNamespace,
) -> SimpleNamespace:
    """When tool-only response has empty content, fill content for interim sink tests."""
    message = completion.choices[0].message
    body = (message.content or "").strip()
    tool_calls = getattr(message, "tool_calls", None) or []
    if body or not tool_calls:
        return completion
    fill = interim_visible_text(completion)
    if not fill:
        return completion
    cloned = deepcopy(completion)
    cloned.choices[0].message.content = fill
    return cloned


def completions_from_trace(trace: dict[str, Any]) -> list[SimpleNamespace]:
    """Normalized fake completions for in-turn sync tool loop replay."""
    out: list[SimpleNamespace] = []
    for run in llm_runs_for_in_turn_replay(trace):
        outputs = run.get("outputs")
        assert isinstance(outputs, dict)
        raw = completion_from_langsmith_outputs(outputs)
        out.append(normalize_completion_for_interim(raw))
    return out


class TraceReplayLLMClient(FakeSyncToolLoopLLMClient):
    """Fake client that replays trace-derived completions in order."""

    def __init__(self, responses: list[SimpleNamespace]) -> None:
        super().__init__(responses)
        self.config = CompanionLLMConfig(api_base="https://example.invalid/v1")

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"test/{role}")
