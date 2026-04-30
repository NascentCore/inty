"""Structured routing for async tool_background: output_to_user gate (+ optional user_visible_text)."""

from __future__ import annotations

import json
import re
from typing import Any, Final

from loguru import logger
from pydantic import BaseModel, Field, ValidationError

_MARKDOWN_JSON_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*\r?\n?(.*?)\r?\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)

TOOL_BG_ROUTING_RESPONSE_FORMAT: Final[dict[str, Any]] = {
    "type": "json_schema",
    "json_schema": {
        "name": "tool_bg_output_to_user_routing",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "output_to_user": {
                    "type": "boolean",
                    "description": (
                        "True if the client should receive a follow-up assistant message "
                        "summarizing tool outcomes (read/search/list/status/etc.). "
                        "False if nothing user-visible remains (e.g. only silent writes)."
                    ),
                },
                "user_visible_text": {
                    "type": "string",
                    "description": (
                        "Short optional summary for the user when output_to_user is true; "
                        "may be empty when delivery is artifact-only."
                    ),
                },
            },
            "required": ["output_to_user", "user_visible_text"],
            "additionalProperties": False,
        },
    },
}


class ToolBgRoutingEnvelope(BaseModel):
    output_to_user: bool = False
    user_visible_text: str = Field(default="")


_ROUTING_SYSTEM_PROMPT = (
    "## Tool-loop routing (machine-readable)\n\n"
    "The tool execution loop has finished. Respond with **JSON only** matching the API "
    "`response_format` schema (no markdown fences, no extra prose).\n"
    "- `output_to_user` (boolean): set **true** if the user should see a follow-up bubble "
    "with outcomes from tools such as workspace_read_file, workspace_list_dir, "
    "google_web_search, companion_runtime_inspect, or tool_update_agent_status_line.\n"
    "- `user_visible_text` (string): optional concise summary for that bubble; may be empty "
    "when images or other artifacts alone suffice.\n"
    "Set `output_to_user` **false** when only silent persistence ran (e.g. USER profile bullets, "
    "workspace_write_file to SOUL/MEMORY) and no user-visible recap is needed.\n"
)


def _strip_json_fence(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    m = _MARKDOWN_JSON_FENCE_RE.match(s)
    if m:
        return (m.group(1) or "").strip()
    return s


def parse_tool_bg_routing_content(raw: str) -> ToolBgRoutingEnvelope | None:
    """Parse assistant message body into routing envelope; None if invalid."""
    body = _strip_json_fence(raw)
    if not body:
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    try:
        return ToolBgRoutingEnvelope.model_validate(data)
    except ValidationError:
        return None


def resolve_tool_bg_routing_sync(
    *,
    client: Any,
    model: str,
    create_completion_sync: Any,
    conversation_messages: list[dict[str, Any]],
    final_assistant_content: str,
    trace_id: str | None = None,
) -> ToolBgRoutingEnvelope:
    """
    Prefer routing JSON from the model's final assistant message; if missing/invalid,
    run one extra completion (no tools, strict JSON schema).

    trace_id: optional correlation id for DEBUG logs (tool_bg_routing / repl.turn.bg policy).
    """
    tid = trace_id or "-"
    parsed = parse_tool_bg_routing_content(final_assistant_content)
    if parsed is not None:
        logger.debug(
            "tool_bg_routing trace_id={} source=final_assistant_message "
            "output_to_user={} user_visible_text_chars={}",
            tid,
            parsed.output_to_user,
            len(parsed.user_visible_text or ""),
        )
        return parsed
    logger.debug(
        "tool_bg_routing trace_id={} source=extra_completion_request "
        "(final_assistant_not_valid_routing_json)",
        tid,
    )
    routing_tail = [
        {"role": "system", "content": _ROUTING_SYSTEM_PROMPT},
    ]
    payload = [{k: v for k, v in m.items() if not str(k).startswith("_")} for m in conversation_messages]
    payload.extend(routing_tail)
    resp = create_completion_sync(
        client,
        model=model,
        messages_payload=payload,
        tools=[],
        response_format=TOOL_BG_ROUTING_RESPONSE_FORMAT,
    )
    content = getattr(resp.choices[0].message, "content", None)
    if not isinstance(content, str):
        logger.debug(
            "tool_bg_routing trace_id={} source=fallback_conservative_non_string_content",
            tid,
        )
        return ToolBgRoutingEnvelope(output_to_user=False, user_visible_text="")
    fallback = parse_tool_bg_routing_content(content)
    if fallback is not None:
        logger.debug(
            "tool_bg_routing trace_id={} source=extra_completion_response "
            "output_to_user={} user_visible_text_chars={}",
            tid,
            fallback.output_to_user,
            len(fallback.user_visible_text or ""),
        )
        return fallback
    logger.debug(
        "tool_bg_routing trace_id={} source=fallback_conservative_invalid_json",
        tid,
    )
    return ToolBgRoutingEnvelope(output_to_user=False, user_visible_text="")
