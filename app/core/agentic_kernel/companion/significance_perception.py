"""Dual-LLM chat branch: significance scores (1-10) + user-facing reply in one JSON envelope."""

from __future__ import annotations

import json
import re
from typing import Any, Final

_MARKDOWN_JSON_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*\r?\n?(.*?)\r?\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)

from pydantic import BaseModel, Field, field_validator

SIGNIFICANCE_PERCEPTION_REL: Final[str] = "SIGNIFICANCE_PERCEPTION.md"

DUAL_LLM_CHAT_RESPONSE_FORMAT: Final[dict[str, Any]] = {
    "type": "json_schema",
    "json_schema": {
        "name": "companion_dual_llm_chat_envelope",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "user_facing_reply": {
                    "type": "string",
                    "description": (
                        "Natural-language reply to the user for this turn. "
                        "May be empty when the parallel tool branch will carry visible text."
                    ),
                },
                "importance_round": {
                    "type": "integer",
                    "description": (
                        "Importance of the overall chat turn (context + user + pending reply), 1-10."
                    ),
                    "minimum": 1,
                    "maximum": 10,
                },
                "importance_user_message": {
                    "type": "integer",
                    "description": "Importance of the latest user message alone, 1-10.",
                    "minimum": 1,
                    "maximum": 10,
                },
                "importance_assistant_message": {
                    "type": "integer",
                    "description": (
                        "Predicted importance of your own assistant reply (user_facing_reply), 1-10."
                    ),
                    "minimum": 1,
                    "maximum": 10,
                },
            },
            "required": [
                "user_facing_reply",
                "importance_round",
                "importance_user_message",
                "importance_assistant_message",
            ],
            "additionalProperties": False,
        },
    },
}


class DualLlmChatBranchEnvelope(BaseModel):
    user_facing_reply: str = ""
    importance_round: int = Field(ge=1, le=10)
    importance_user_message: int = Field(ge=1, le=10)
    importance_assistant_message: int = Field(ge=1, le=10)

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
    except Exception:
        return None


def envelope_to_assistant_metadata_dict(
    env: DualLlmChatBranchEnvelope,
) -> dict[str, Any]:
    return {
        "importance_round": env.importance_round,
        "importance_user_message": env.importance_user_message,
        "importance_assistant_message": env.importance_assistant_message,
    }


def split_dual_llm_chat_branch_content(
    raw: str,
) -> tuple[str, dict[str, Any] | None]:
    env = parse_dual_llm_chat_envelope_json(raw)
    if env is None:
        return ((raw or "").strip(), None)
    return (env.user_facing_reply.strip(), envelope_to_assistant_metadata_dict(env))
