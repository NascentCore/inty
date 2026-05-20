from __future__ import annotations

import json
from typing import Any, Dict, List


def _extract_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: List[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text.strip())
        return "\n".join(text_parts)
    return ""


def parse_lc_message_row(message_raw: Any) -> Dict[str, str]:
    """
    Parse chat_history.message JSONB into role + plain text.
    Mirrors app.services.chat_history_service._parse_message_content.
    """
    try:
        if isinstance(message_raw, str):
            message_data = json.loads(message_raw)
        elif isinstance(message_raw, dict):
            message_data = message_raw
        else:
            message_data = json.loads(str(message_raw))

        message_type = message_data.get("type", "human")
        content = ""
        if "data" in message_data and "content" in message_data["data"]:
            content = _extract_text_from_content(
                message_data["data"]["content"]
            )
        elif "content" in message_data:
            content = _extract_text_from_content(message_data["content"])

        if message_type == "system":
            role = "system"
        elif message_type in ["human", "HumanMessage"]:
            role = "user"
        else:
            role = "assistant"

        return {"content": content, "role": role}
    except Exception:
        return {
            "content": str(message_raw) if message_raw else "",
            "role": "unknown",
        }


def transcript_upto(turns: List[Dict[str, str]], end_exclusive: int) -> str:
    lines: List[str] = []
    for i in range(0, max(0, end_exclusive)):
        t = turns[i]
        role = t["role"]
        body = t["content"].replace("\r\n", "\n").strip()
        if not body:
            continue
        label = {
            "user": "User",
            "assistant": "Assistant",
            "system": "System",
        }.get(role, role)
        lines.append(f"{label}: {body}")
    return "\n".join(lines)
