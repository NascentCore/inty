"""Proactive inner-tick JSON envelope: schema, ``response_format``, and fail-closed parse.

Proactive and scheduled inner ticks (``InnerTickActivity.PROACTIVE_CHAT``) require the model
to return ``output_to_user`` plus optional ``message`` instead of a legacy ``[SILENT]`` token.
Parsing mirrors ``dual_llm_chat_branch_envelope`` (content then reasoning side channels) but
never falls back to raw ``content`` on failure.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final, Self
from unittest.mock import Base as _UnittestMockBase

from loguru import logger
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticSerializationError

_MARKDOWN_JSON_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*\r?\n?(.*?)\r?\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)


class ProactiveChatEnvelope(BaseModel):
    """Proactive/scheduled inner-tick JSON: whether to send user-visible text this round."""

    model_config = ConfigDict(extra="forbid")

    output_to_user: bool = Field(
        description="True when the companion should send a proactive message now."
    )
    message: str = Field(
        default="",
        description="In-character proactive text; must be non-empty when output_to_user is true.",
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

    @field_validator("message", mode="before")
    @classmethod
    def _coerce_message(cls, v: object) -> str:
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        return str(v)

    @model_validator(mode="after")
    def _message_matches_output_flag(self) -> Self:
        has_message = bool(self.message.strip())
        if self.output_to_user and not has_message:
            raise ValueError(
                "message must be non-empty when output_to_user is true"
            )
        if not self.output_to_user and has_message:
            raise ValueError(
                "message must be empty when output_to_user is false"
            )
        return self


def _build_proactive_chat_response_format() -> dict[str, Any]:
    """OpenAI ``response_format`` wrapper from ``ProactiveChatEnvelope`` JSON Schema."""
    inner = ProactiveChatEnvelope.model_json_schema()
    inner.pop("title", None)
    defs = inner.get("$defs")
    if isinstance(defs, dict) and not defs:
        inner.pop("$defs", None)
    inner["required"] = list(ProactiveChatEnvelope.model_fields.keys())
    inner["additionalProperties"] = False
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "companion_proactive_chat_envelope",
            "strict": True,
            "schema": inner,
        },
    }


PROACTIVE_CHAT_RESPONSE_FORMAT: Final[dict[str, Any]] = (
    _build_proactive_chat_response_format()
)


def _strip_markdown_json_fence(raw: str) -> str:
    s = (raw or "").strip()
    m = _MARKDOWN_JSON_FENCE_RE.fullmatch(s)
    if m:
        return m.group(1).strip()
    return s


def parse_proactive_chat_envelope_json(
    raw: str,
) -> ProactiveChatEnvelope | None:
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
        return ProactiveChatEnvelope.model_validate(obj)
    except ValidationError:
        return None


@dataclass(frozen=True)
class ProactiveChatSplit:
    """Parsed proactive envelope fields for one assistant turn."""

    output_to_user: bool
    visible_text: str


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
                "proactive_envelope_candidate_model_dump_failed value_type={} err={}",
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


def _proactive_message_candidate_texts(message: Any) -> list[str]:
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


def parse_proactive_chat_envelope_from_message(
    message: Any,
) -> ProactiveChatEnvelope | None:
    """Parse the envelope from content first, then provider reasoning side channels."""
    for raw in _proactive_message_candidate_texts(message):
        env = parse_proactive_chat_envelope_json(raw)
        if env is not None:
            return env
    return None


def split_proactive_chat_message(message: Any) -> ProactiveChatSplit:
    """Split a structured proactive response; fail-closed silent when parse fails."""
    env = parse_proactive_chat_envelope_from_message(message)
    if env is not None:
        if env.output_to_user:
            return ProactiveChatSplit(
                output_to_user=True,
                visible_text=env.message.strip(),
            )
        return ProactiveChatSplit(output_to_user=False, visible_text="")
    return ProactiveChatSplit(output_to_user=False, visible_text="")
