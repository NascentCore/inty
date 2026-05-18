import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.messages_compaction import (
    CompactedMessageItem,
    MessagesCompactionPayload,
)


def _safe_isoformat(raw_value: Any) -> Optional[str]:
    if raw_value is None:
        return None
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        return normalized or None
    if isinstance(raw_value, datetime):
        return raw_value.isoformat()
    return str(raw_value)


def _build_compacted_messages(
    history_messages: List[BaseMessage],
) -> List[CompactedMessageItem]:
    compacted_messages: List[CompactedMessageItem] = []
    for message in history_messages:
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            continue
        message_content = getattr(message, "content", "")
        if not isinstance(message_content, str):
            message_content = str(message_content)
        message_content = message_content.strip()
        if not message_content:
            continue
        created_at = _safe_isoformat(
            (getattr(message, "additional_kwargs", None) or {}).get(
                "created_at"
            )
        )
        compacted_messages.append(
            CompactedMessageItem(
                role=role,
                content=message_content,
                created_at=created_at,
            )
        )
    return compacted_messages


def maybe_compact_and_save_overflow_history(
    *,
    sync_engine: Any,
    user_id: str,
    agent_id: str,
    session_id: str,
    history_messages: List[BaseMessage],
    max_messages_limit: int,
) -> bool:
    """
    Compact overflow history and persist by user_id:agent_id key.
    """
    if max_messages_limit <= 0:
        return False
    if len(history_messages) <= max_messages_limit:
        return False

    overflow_messages = history_messages[
        : len(history_messages) - max_messages_limit
    ]
    compacted_messages = _build_compacted_messages(overflow_messages)
    payload = MessagesCompactionPayload(
        source_session_id=session_id,
        max_messages_limit=max_messages_limit,
        original_messages_count=len(overflow_messages),
        compacted_messages_count=len(compacted_messages),
        compacted_messages=compacted_messages,
    )
    return upsert_compaction_payload(
        sync_engine=sync_engine,
        user_id=user_id,
        agent_id=agent_id,
        payload=payload,
    )


def _normalize_payload(
    payload: Union[MessagesCompactionPayload, Dict[str, Any]],
) -> MessagesCompactionPayload:
    if isinstance(payload, MessagesCompactionPayload):
        return payload
    return MessagesCompactionPayload.model_validate(payload)


def upsert_compaction_payload(
    *,
    sync_engine: Any,
    user_id: str,
    agent_id: str,
    payload: Union[MessagesCompactionPayload, Dict[str, Any]],
) -> bool:
    compaction_key = f"{user_id}:{agent_id}"
    normalized_payload = _normalize_payload(payload)

    try:
        with sync_engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO messages_compaction (
                        key, user_id, agent_id, compacted_payload, created_at, updated_at
                    )
                    VALUES (
                        :key, :user_id, :agent_id, CAST(:compacted_payload AS jsonb), now(), now()
                    )
                    ON CONFLICT (key)
                    DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        agent_id = EXCLUDED.agent_id,
                        compacted_payload = EXCLUDED.compacted_payload,
                        updated_at = now()
                    """),
                {
                    "key": compaction_key,
                    "user_id": user_id,
                    "agent_id": agent_id,
                    "compacted_payload": json.dumps(
                        normalized_payload.model_dump(exclude_none=True)
                    ),
                },
            )
        logger.info(
            "Messages compaction saved: "
            "key={}, original_count={}, compacted_count={}".format(
                compaction_key,
                normalized_payload.original_messages_count,
                normalized_payload.compacted_messages_count,
            )
        )
        return True
    except SQLAlchemyError as error:
        logger.error(
            "Messages compaction failed: "
            f"key={compaction_key}, error={error!s}"
        )
        return False


def get_compaction_payload(
    *,
    sync_engine: Any,
    user_id: str,
    agent_id: str,
) -> Optional[Dict[str, Any]]:
    compaction_key = f"{user_id}:{agent_id}"
    try:
        with sync_engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT compacted_payload
                    FROM messages_compaction
                    WHERE key = :key
                    """),
                {"key": compaction_key},
            ).fetchone()
        if row is None:
            return None
        compacted_payload_raw = row[0]
        if isinstance(compacted_payload_raw, dict):
            return compacted_payload_raw
        if isinstance(compacted_payload_raw, str):
            return json.loads(compacted_payload_raw)
        return None
    except SQLAlchemyError as error:
        logger.error(
            f"Messages compaction read failed: key={compaction_key}, error={error!s}"
        )
        return None
