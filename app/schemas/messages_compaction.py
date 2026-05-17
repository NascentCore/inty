from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class CompactedMessageItem(BaseModel):
    role: Literal["user", "assistant"] = Field(
        ..., description="Message role after compaction"
    )
    content: str = Field(..., description="Compacted message content")
    created_at: Optional[str] = Field(
        None, description="Original message creation time in ISO format"
    )


class MessagesCompactionPayload(BaseModel):
    source_session_id: str = Field(
        ..., description="Chat session that was compacted"
    )
    max_messages_limit: int = Field(
        ..., description="Current chat history window limit used for truncation"
    )
    original_messages_count: int = Field(
        ..., description="Number of overflowing original history messages"
    )
    compacted_messages_count: int = Field(
        ..., description="Number of compacted message items"
    )
    compacted_messages: List[CompactedMessageItem] = Field(
        default_factory=list,
        description="Compacted messages that preserve key context",
    )
