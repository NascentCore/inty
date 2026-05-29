"""Minimal LLM smoke-reply helper for `/chat/ws/verify`."""

from __future__ import annotations

import asyncio
from typing import Any

from app.utils.openai_client import get_chat_openai_client

async def _verify_ws_simple_llm_reply(
    *,
    agent_row: dict[str, Any],
    user_text: str,
    model_name: str,
) -> str:
    """
    Single chat-completions call (system + user only). No Agent instance, no history, no tools.
    Used by ``/ws/verify`` only.
    """
    name = (agent_row.get("name") or "Assistant").strip() or "Assistant"
    snippet = (
        agent_row.get("personality") or agent_row.get("intro") or ""
    ).strip()
    if snippet:
        system = f"You are {name}. Character notes: {snippet[:1200]}"
    else:
        system = f"You are {name}. Reply concisely in the same language as the user's message."

    client = get_chat_openai_client()

    def _sync_call() -> str:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
            max_tokens=2048,
            temperature=0.7,
        )
        if not resp.choices:
            return ""
        return (resp.choices[0].message.content or "").strip()

    return await asyncio.to_thread(_sync_call)
