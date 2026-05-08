"""Dual-LLM chat branch: significance scores (1-10) + user-facing reply in one JSON envelope.

**Where the three importance integers flow (read this when changing the contract):**

- **Produced**: Foreground ``chat.completions`` may set ``response_format`` to
  ``DUAL_LLM_CHAT_RESPONSE_FORMAT`` (``turn.run_turn``) so the model returns JSON with
  ``user_facing_reply``, ``output_to_user``, plus ``importance_round`` /
  ``importance_user_message`` / ``importance_assistant_message``. The same envelope is used
  for async ``tool_background`` finish (see ``tool_bg_routing``). Operator guidance for scoring lives in
  ``prompts/SIGNIFICANCE_PERCEPTION.md`` (injected when
  ``include_significance_perception_slice`` is on; see ``prompts/system_messages.py`` and
  ``prompt_stack.companion_turn_tools_and_system_messages``).
- **Parsed / split**: ``split_dual_llm_chat_branch_content`` strips optional markdown fences
  and returns ``(visible_text, metadata_dict, output_to_user_or_none)``; metadata keys match
  the three importance JSON field names. The third tuple element is the parsed envelope's
  ``output_to_user`` when JSON validated, else ``None`` (foreground chat should treat missing
  as unparsed raw text).
- **Kernel return**: ``CompanionTurnResult.significance_perception`` (``models.py``) carries
  the dict for one turn; may be ``None`` if the model returned non-JSON or parse failed
  (visible text may still be the raw string).
- **Transcript**: ``turn.run_turn`` appends an assistant JSONL row with optional
  ``significance_perception``; ``turn_engine.persist_repl_turn_transcript_rows`` can attach
  the same via ``assistant_extra`` for REPL-style paths.
- **Product DB / WS**: ``app/api/v1/endpoints/chat._companion_ai_meta_from_turn_result`` copies
  non-empty ``significance_perception`` into ``chat_history`` AI row ``meta_data`` and WebSocket
  ``message.meta_data`` (companion path only when the kernel populated it).
- **Memory extraction (optional)**: When ``memory_extraction.use_significance_perception_in_extraction``
  is true (``app/utils/config.py``), ``app/services/memory_extraction_service.py`` sorts message
  rows by ``meta_data.significance_perception.importance_round`` and annotates lines in the
  extraction prompt; see ``_prepare_messages_for_memory_extraction`` and
  ``_format_chat_for_prompt``.

Design overview: ``/docs/imate/DESIGN.md`` (Significance / memory extraction sections).
LangSmith tags foreground envelope spans with ``inty_llm_source=foreground_dual_llm_envelope``
(``llm/langsmith_invocation_extra.py``).
"""

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
                "output_to_user": {
                    "type": "boolean",
                    "description": (
                        "Foreground dual-LLM chat branch: always true. "
                        "Tool-background finish: false when only silent persistence ran and no "
                        "user-visible recap is needed."
                    ),
                },
            },
            "required": [
                "user_facing_reply",
                "importance_round",
                "importance_user_message",
                "importance_assistant_message",
                "output_to_user",
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
    output_to_user: bool = True

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
) -> tuple[str, dict[str, Any] | None, bool | None]:
    # TODO(companion-dual-envelope-reasoning-channel): Empty ``raw`` here often means the LLM put
    # the JSON envelope only in ``message.reasoning``; fix extraction before calling this helper.
    env = parse_dual_llm_chat_envelope_json(raw)
    if env is None:
        return ((raw or "").strip(), None, None)
    return (
        env.user_facing_reply.strip(),
        envelope_to_assistant_metadata_dict(env),
        env.output_to_user,
    )
