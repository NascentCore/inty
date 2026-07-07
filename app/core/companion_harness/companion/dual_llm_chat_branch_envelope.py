"""Dual-LLM chat branch JSON: schema, OpenAI ``response_format``, parse/split, and pipeline notes.

**This module owns** (1) the ``DualLlmChatBranchEnvelope`` Pydantic model and
``DUAL_LLM_CHAT_RESPONSE_FORMAT`` built from it, and (2) parsing from raw strings or
structured provider ``message`` objects into ``DualLlmChatBranchSplit`` for the
companion turn pipeline.

**Where the three importance integers flow (read this when changing the contract):**

- **Produced**: Foreground ``chat.completions`` may set ``response_format`` to
  ``DUAL_LLM_CHAT_RESPONSE_FORMAT`` (``_build_dual_llm_chat_response_format()``; ``turn.run_turn``)
  so the model returns JSON with ``user_facing_reply``, ``output_to_user``, plus
  ``importance_round`` / ``importance_user_message`` / ``importance_assistant_message``.
  The same envelope is used for async ``tool_background`` finish (see ``tool_bg_routing``).
  Operator guidance lives in ``prompts/SIGNIFICANCE_PERCEPTION.md`` (injected when
  ``include_significance_perception_slice`` is on; see ``prompts/system_messages.py`` and
  ``prompt_stack.companion_turn_tools_and_system_messages``).
- **Parsed / split**: ``split_dual_llm_chat_branch_message``
  returns ``DualLlmChatBranchSplit`` (visible text, optional significance metadata dict,
  ``output_to_user``). Validated payloads deserialize
  as ``DualLlmChatBranchEnvelope``.
- **Kernel return**: ``CompanionTurnResult.significance_perception`` (``models.py``) carries the dict;
  may be ``None`` if parse failed.
- **Transcript**: ``turn.run_turn`` JSONL assistant row.
- **Product DB / WS**: ``app/services/agentic_companion/ws_turn_support.companion_ai_meta_from_turn_result`` mirrors into
  ``chat_history`` / WS. Async ``tool_bg``: ``ToolOutputEvent.significance_perception`` via
  ``tool_bg_routing`` → ``chat_ws._build_companion_tool_background_ws_payload``.
- **Memory extraction (optional)**: ``memory_extraction.use_significance_perception_in_extraction`` →
  ``memory_extraction_service`` sorts by ``meta_data.significance_perception.importance_round``.

TODO(crs-turn-recall): ``importance_*`` scores are **moment-level significance perception**, not — #3343
``turn_recall`` (ephemeral per-turn memory depth / Turn Brief). Phase A (#3342) plumbs
``turn_recall`` on the envelope, transcript, and WS meta; Phase B (#3343) wires prompt +
dreaming curator. CRS epic #3341; do not conflate with ``relationship_phase``
(slow bond in ``COMPANIONSHIP.md``) or ``experience_directives.tone`` (fast stance in
``context.json``). **Blocked until #3485 refactor gate; plumbing only — do not expand.**

TODO(crs-relationship-signal-log): Append significance perception as relationship-signal
events (CQRS fold input), not only transcript meta — #3773 (epic #3341).

Design: ``/docs/imate/DESIGN.md``. LangSmith: ``inty_llm_source=foreground_dual_llm_envelope``
(``llm/langsmith_invocation_extra.py``).

TODO(#3602): Prefer OpenAI SDK ``chat.completions.parse(response_format=Model)`` for
structured paths (#3600 proactive, possibly dual-LLM) instead of duplicating manual
JSON extraction from content/reasoning side channels.

TODO(#3398): Envelope is shared by single-LLM in-turn sync and dual-LLM ``tool_background`` finish;
epic tracks whether user chat stays on one chat model or splits chat vs ``companion_tool_call_model``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final
from unittest.mock import Base as _UnittestMockBase

from loguru import logger
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)
from pydantic_core import PydanticSerializationError

_MARKDOWN_JSON_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*\r?\n?(.*?)\r?\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)


class DualLlmChatBranchEnvelope(BaseModel):
    """Assistant JSON envelope for dual-LLM chat branch (foreground or tool-background finish)."""

    model_config = ConfigDict(extra="forbid")

    user_facing_reply: str = Field(
        default="",
        description=(
            "Natural-language reply to the user for this turn. "
            "May be empty when the parallel tool branch will carry visible text."
        ),
    )
    importance_round: int = Field(
        ...,
        ge=1,
        le=10,
        description=(
            "Importance of the overall chat turn (context + user + pending reply), 1-10."
        ),
    )
    importance_user_message: int = Field(
        ...,
        ge=1,
        le=10,
        description="Importance of the latest user message alone, 1-10.",
    )
    importance_assistant_message: int = Field(
        ...,
        ge=1,
        le=10,
        description=(
            "Predicted importance of your own assistant reply (user_facing_reply), 1-10."
        ),
    )
    output_to_user: bool = Field(
        default=True,
        description=(
            "Foreground dual-LLM chat branch: always true. "
            "Tool-background finish: false when only silent persistence ran and no "
            "user-visible recap is needed."
        ),
    )
    turn_recall: str = Field(
        default="",
        description=(
            "Ephemeral Turn Brief: one-turn recall notes (#3343 operator in "
            "SIGNIFICANCE_PERCEPTION.md). Leave empty when nothing special."
        ),
    )

    @field_validator("output_to_user", mode="before")
    @classmethod
    def _coerce_output_to_user(cls, v: object) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("true", "1", "yes"):
                return True
            if s in ("false", "0", "no"):
                return False
        raise ValueError("output_to_user must be boolean")

    @field_validator("user_facing_reply", mode="before")
    @classmethod
    def _coerce_reply(cls, v: object) -> str:
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        return str(v)

    @field_validator("turn_recall", mode="before")
    @classmethod
    def _coerce_turn_recall(cls, v: object) -> str:
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        return str(v)

    @field_validator(
        "importance_round",
        "importance_user_message",
        "importance_assistant_message",
        mode="before",
    )
    @classmethod
    def _coerce_score(cls, v: object) -> int:
        if isinstance(v, bool):
            raise ValueError("score must not be boolean")
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            return int(round(v))
        if isinstance(v, str) and v.strip().isdigit():
            return int(v.strip())
        raise ValueError("score must be integer 1-10")


def _build_dual_llm_chat_response_format() -> dict[str, Any]:
    """OpenAI ``response_format`` wrapper from ``DualLlmChatBranchEnvelope`` JSON Schema."""
    inner = DualLlmChatBranchEnvelope.model_json_schema()
    inner.pop("title", None)
    defs = inner.get("$defs")
    if isinstance(defs, dict) and not defs:
        inner.pop("$defs", None)
    inner["required"] = list(DualLlmChatBranchEnvelope.model_fields.keys())
    inner["additionalProperties"] = False
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "companion_dual_llm_chat_envelope",
            "strict": True,
            "schema": inner,
        },
    }


DUAL_LLM_CHAT_RESPONSE_FORMAT: Final[dict[str, Any]] = (
    _build_dual_llm_chat_response_format()
)


def _strip_markdown_json_fence(raw: str) -> str:
    """If the model wraps the envelope in a ```json ... ``` fence, return inner JSON text."""

    s = (raw or "").strip()
    m = _MARKDOWN_JSON_FENCE_RE.fullmatch(s)
    if m:
        return m.group(1).strip()
    return s


def parse_dual_llm_chat_envelope_json(
    raw: str,
) -> DualLlmChatBranchEnvelope | None:
    s = _strip_markdown_json_fence((raw or "").strip())
    if not s:
        return None
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    try:
        return DualLlmChatBranchEnvelope.model_validate(obj)
    except ValidationError:
        return None


def envelope_to_assistant_metadata_dict(
    env: DualLlmChatBranchEnvelope,
) -> dict[str, Any]:
    return {
        "importance_round": env.importance_round,
        "importance_user_message": env.importance_user_message,
        "importance_assistant_message": env.importance_assistant_message,
    }


@dataclass(frozen=True)
class DualLlmChatBranchSplit:
    """Parsed foreground / single-shot dual-LLM envelope fields for one assistant turn."""

    visible_text: str
    significance_meta: dict[str, Any] | None
    output_to_user: bool | None
    turn_recall: str | None = None


def _message_field(message: Any, field_name: str) -> Any:
    if isinstance(message, Mapping):
        return message.get(field_name)
    return getattr(message, field_name, None)


def _string_candidates_from_value(value: Any) -> list[str]:
    if isinstance(value, _UnittestMockBase):
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, Mapping):
        out: list[str] = []
        for key in ("content", "text", "summary"):
            out.extend(_string_candidates_from_value(value.get(key)))
        return out
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            out.extend(_string_candidates_from_value(item))
        return out
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        try:
            return _string_candidates_from_value(dump())
        except (PydanticSerializationError, TypeError, ValueError) as exc:
            logger.warning(
                "dual_llm_envelope_candidate_model_dump_failed value_type={} err={}",
                type(value).__name__,
                exc,
            )
            return []
    out: list[str] = []
    for key in ("content", "text", "summary"):
        attr = getattr(value, key, None)
        if isinstance(attr, str):
            out.extend(_string_candidates_from_value(attr))
    if out:
        return out
    return []


def _dual_llm_message_candidate_texts(message: Any) -> list[str]:
    content_candidates = _string_candidates_from_value(
        _message_field(message, "content")
    )
    reasoning_candidates = [
        *_string_candidates_from_value(_message_field(message, "reasoning")),
        *_string_candidates_from_value(
            _message_field(message, "reasoning_details")
        ),
    ]
    return [*content_candidates, *reasoning_candidates]


def parse_dual_llm_chat_envelope_from_message(
    message: Any,
) -> DualLlmChatBranchEnvelope | None:
    """Parse the envelope from content first, then provider reasoning side channels."""

    for raw in _dual_llm_message_candidate_texts(message):
        env = parse_dual_llm_chat_envelope_json(raw)
        if env is not None:
            return env
    return None


def turn_recall_from_envelope(env: DualLlmChatBranchEnvelope) -> str | None:
    text = (env.turn_recall or "").strip()
    return text or None


def split_dual_llm_chat_branch_message(message: Any) -> DualLlmChatBranchSplit:
    """
    Split a structured chat response message.

    Some OpenAI-compatible providers return ``response_format`` JSON under
    ``reasoning`` or ``reasoning_details`` while leaving ``content`` empty. Only
    validated envelopes are accepted from side channels, so chain-of-thought
    text is never surfaced as user-visible content.
    """

    env = parse_dual_llm_chat_envelope_from_message(message)
    if env is not None:
        return DualLlmChatBranchSplit(
            visible_text=env.user_facing_reply.strip(),
            significance_meta=envelope_to_assistant_metadata_dict(env),
            output_to_user=env.output_to_user,
            turn_recall=turn_recall_from_envelope(env),
        )
    content = _message_field(message, "content")
    raw = content if isinstance(content, str) else ""
    return DualLlmChatBranchSplit(
        visible_text=(raw or "").strip(),
        significance_meta=None,
        output_to_user=None,
        turn_recall=None,
    )
