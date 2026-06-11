"""OpenAI-style chat completion wire payloads for companion WS and maintenance REST."""

from __future__ import annotations

import time
import uuid
from typing import Any, List, Optional

from loguru import logger
from pydantic import TypeAdapter

from app.schemas.biz_action import ActionType, BizAction
from app.schemas.chat import ChatCompletionRequest, ChatMessageContentPart
from app.schemas.chat_websocket import (
    ChatWsAssistantMessage,
    ChatWsCompletionChoice,
    ChatWsCompletionData,
    ChatWsCompletionUsage,
    ChatWsCompanionWireMessageMetaData,
)

_content_part_adapter = TypeAdapter(ChatMessageContentPart)


def _normalize_response_content_part(part: Any) -> Optional[dict[str, Any]]:
    if hasattr(part, "model_dump"):
        part = part.model_dump(exclude_none=True)
    if not isinstance(part, dict):
        return None

    part_type = part.get("type")
    if part_type == "text":
        text = part.get("text")
        if isinstance(text, str):
            return {"type": "text", "text": text}
        return None

    if part_type == "image_url":
        image_url = part.get("image_url")
        if hasattr(image_url, "model_dump"):
            image_url = image_url.model_dump(exclude_none=True)
        if not isinstance(image_url, dict):
            return None
        url = image_url.get("url")
        if isinstance(url, str) and url.strip():
            return {"type": "image_url", "image_url": {"url": url}}
        return None

    return None


def _normalize_chat_response_content(
    response_content: Any,
) -> tuple[str, Optional[List[dict[str, Any]]]]:
    if isinstance(response_content, str):
        return response_content, None

    if isinstance(response_content, list):
        normalized_parts: List[dict[str, Any]] = []
        text_parts: List[str] = []
        for part in response_content:
            normalized_part = _normalize_response_content_part(part)
            if normalized_part is None:
                continue
            normalized_parts.append(normalized_part)
            if normalized_part["type"] == "text":
                text = normalized_part.get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text.strip())
        if len(normalized_parts) > 0:
            return "\n".join(text_parts), normalized_parts
        return "", None

    if response_content is None:
        return "", None
    return str(response_content), None


def _content_parts_from_wire_dicts(
    response_content_parts: Optional[List[dict[str, Any]]],
) -> Optional[list[ChatMessageContentPart]]:
    if response_content_parts is None or len(response_content_parts) == 0:
        return None
    return [
        _content_part_adapter.validate_python(part)
        for part in response_content_parts
    ]


def _assistant_message_for_ws_completion(
    *,
    response_text_content: str,
    response_content_parts: Optional[List[dict[str, Any]]],
    latest_message_info: Optional[dict],
    audio_url: Optional[str],
) -> ChatWsAssistantMessage:
    content_parts = _content_parts_from_wire_dicts(response_content_parts)
    if latest_message_info:
        meta_raw = latest_message_info.get("meta_data")
        meta = (
            ChatWsCompanionWireMessageMetaData.model_validate(meta_raw)
            if meta_raw
            else None
        )
        return ChatWsAssistantMessage(
            content=response_text_content,
            content_parts=content_parts,
            id=latest_message_info.get("id"),
            meta_data=meta,
            timestamp=latest_message_info.get("timestamp"),
            audio_url=latest_message_info.get("audio_url") or audio_url,
        )
    if audio_url:
        return ChatWsAssistantMessage(
            content=response_text_content,
            content_parts=content_parts,
            audio_url=audio_url,
        )
    return ChatWsAssistantMessage(
        content=response_text_content,
        content_parts=content_parts,
    )


def build_companion_ws_completion_data(
    *,
    response_text_content: str,
    response_content_parts: Optional[List[dict[str, Any]]],
    last_user_text: str,
    latest_message_info: Optional[dict],
    audio_url: Optional[str],
    request: ChatCompletionRequest,
    source_imate_id: Optional[str],
    user_message_id: Optional[int],
    subscription_actions: Optional[List[BizAction]],
    client_local_id: Optional[str],
) -> ChatWsCompletionData:
    """Build typed companion WS completion ``data`` (issue #3208)."""
    actions = subscription_actions
    if actions is None or len(actions) == 0:
        actions = [BizAction(action_type=ActionType.NONE, message="")]

    assistant = _assistant_message_for_ws_completion(
        response_text_content=response_text_content,
        response_content_parts=response_content_parts,
        latest_message_info=latest_message_info,
        audio_url=audio_url,
    )
    if assistant.audio_url:
        logger.debug(f"响应包含语音URL: {assistant.audio_url}")

    return ChatWsCompletionData(
        id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
        created=int(time.time()),
        model=request.model,
        user_message_id=user_message_id,
        business_actions=actions,
        choices=[
            ChatWsCompletionChoice(
                index=0,
                message=assistant,
                finish_reason="stop",
            )
        ],
        usage=ChatWsCompletionUsage(
            prompt_tokens=len(last_user_text.split()),
            completion_tokens=len(response_text_content.split()),
            total_tokens=len(last_user_text.split())
            + len(response_text_content.split()),
        ),
        local_id=client_local_id,
        source_imate_id=source_imate_id,
    )


def _build_chat_response(
    response_text_content: str,
    response_content_parts: Optional[List[dict[str, Any]]],
    last_user_text: str,
    latest_message_info: Optional[dict],
    audio_url: Optional[str],
    request: ChatCompletionRequest,
    source_imate_id: Optional[str],
    user_message_id: Optional[int] = None,
    subscription_actions: Optional[List[BizAction]] = None,
    client_local_id: Optional[str] = None,
) -> dict:
    """Maintenance REST ``/chat/completions`` only; companion WS uses ``build_companion_ws_completion_data``."""
    completion = build_companion_ws_completion_data(
        response_text_content=response_text_content,
        response_content_parts=response_content_parts,
        last_user_text=last_user_text,
        latest_message_info=latest_message_info,
        audio_url=audio_url,
        request=request,
        source_imate_id=source_imate_id,
        user_message_id=user_message_id,
        subscription_actions=subscription_actions,
        client_local_id=client_local_id,
    )
    return completion.model_dump(exclude_none=True)
