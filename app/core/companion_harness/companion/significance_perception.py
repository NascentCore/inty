"""Dual-LLM chat branch: significance scores (1-10) + user-facing reply in one JSON envelope.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final, Literal
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

SIGNIFICANCE_PERCEPTION_REL: Final[str] = "SIGNIFICANCE_PERCEPTION.md"


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
    reply_modality: Literal["text", "voice_message"] = Field(
        default="text",
        description=(
            "How this turn is primarily delivered. "
            "`text`: normal chat bubble (optional spoken playback may mirror "
            "`user_facing_reply`). "
            "`voice_message`: you are sending a short voice note as a person would; "
            "then fill `voice_message_script` with natural spoken words for synthesis "
            "(not stage directions). "
            "`user_facing_reply` may carry an optional caption or transcript preview."
        ),
    )
    voice_message_script: str = Field(
        default="",
        description=(
            "When `reply_modality` is `voice_message`, the exact wording to speak "
            "for the voice clip (first-person, conversational). "
            "Use empty string when `reply_modality` is `text`."
        ),
    )

    @field_validator("reply_modality", mode="before")
    @classmethod
    def _coerce_reply_modality(cls, v: object) -> str:
        if v is None:
            return "text"
        if isinstance(v, str):
            s = v.strip().lower()
            if s == "voice_message":
                return "voice_message"
            return "text"
        return "text"

    @field_validator("voice_message_script", mode="before")
    @classmethod
    def _coerce_voice_script(cls, v: object) -> str:
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        return str(v)

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

    @model_validator(mode="after")
    def _clear_voice_script_when_text_modality(self) -> DualLlmChatBranchEnvelope:
        if self.reply_modality == "text":
            self.voice_message_script = ""
        return self


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


def default_significance_perception_markdown() -> str:
    return (
        "## Significance perception (operator guidance)\n\n"
        "Score **importance** on a **1-10** scale (10 = highest): one score for the **whole turn** "
        "in context, one for the **latest user message** alone, and one for the **assistant reply** "
        "you are about to give (`user_facing_reply`).\n\n"
        "Use higher scores when the moment affects trust, safety, boundaries, major life events, "
        "or durable relationship state; use lower scores for small talk or repetition.\n"
    )


def _strip_markdown_json_fence(raw: str) -> str:
    """If the model wraps the envelope in a ```json ... ``` fence, return inner JSON text."""

    s = (raw or "").strip()
    m = _MARKDOWN_JSON_FENCE_RE.fullmatch(s)
    if m:
        return m.group(1).strip()
    return s


def parse_dual_llm_chat_envelope_json(raw: str) -> DualLlmChatBranchEnvelope | None:
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
    reply_modality: Literal["text", "voice_message"]
    voice_message_script: str


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
        *_string_candidates_from_value(_message_field(message, "reasoning_details")),
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


def split_dual_llm_chat_branch_content(raw: str) -> DualLlmChatBranchSplit:
    env = parse_dual_llm_chat_envelope_json(raw)
    if env is None:
        return DualLlmChatBranchSplit(
            visible_text=(raw or "").strip(),
            significance_meta=None,
            output_to_user=None,
            reply_modality="text",
            voice_message_script="",
        )
    return DualLlmChatBranchSplit(
        visible_text=env.user_facing_reply.strip(),
        significance_meta=envelope_to_assistant_metadata_dict(env),
        output_to_user=env.output_to_user,
        reply_modality=env.reply_modality,
        voice_message_script=(env.voice_message_script or "").strip(),
    )


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
            reply_modality=env.reply_modality,
            voice_message_script=(env.voice_message_script or "").strip(),
        )
    content = _message_field(message, "content")
    raw = content if isinstance(content, str) else ""
    return DualLlmChatBranchSplit(
        visible_text=(raw or "").strip(),
        significance_meta=None,
        output_to_user=None,
        reply_modality="text",
        voice_message_script="",
    )
