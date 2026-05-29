"""``record_user_feedback`` tool: persist companion-behavior feedback to Postgres.

Runs in the inner-tick maintenance track only. The maintenance LLM reflects over the
recent conversation, infers feedback about the companion's behavior across multiple
messages, and calls this tool. Reproduction context (scope ids, recording-run
``trace_id``/``user_msg_uuid``, verbatim quotes) is captured alongside the feedback.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ValidationError, field_validator

from app.core.companion_harness.companion.llm_runtime_events import (
    companion_llm_runtime_event_bind_ctx,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.db.base import SessionLocal
from app.models.agentic_companion.user_feedback import (
    CompanionUserFeedback,
    UserFeedbackCategory,
    UserFeedbackReproContext,
)


class UserFeedbackToolArgs(BaseModel):
    """Validated ``record_user_feedback`` arguments supplied by the LLM."""

    category: UserFeedbackCategory
    feedback_text: str
    user_quote: str | None = None
    offending_assistant_text: str | None = None

    @field_validator("feedback_text")
    @classmethod
    def _non_empty_feedback(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("feedback_text must be non-empty")
        return value


def build_companion_user_feedback(
    *,
    scope: CompanionScope,
    trace_id: str | None,
    user_msg_uuid: str | None,
    arguments: dict[str, object],
) -> CompanionUserFeedback:
    """Validate args + scope/bind context into a persistable row (no DB I/O)."""
    args = UserFeedbackToolArgs.model_validate(arguments)
    assert scope.user_id and scope.companion_id, "feedback requires companion scope"
    repro = UserFeedbackReproContext(
        user_quote=args.user_quote,
        offending_assistant_text=args.offending_assistant_text,
    )
    return CompanionUserFeedback(
        id=uuid.uuid4().hex,
        user_id=scope.user_id,
        companion_id=scope.companion_id,
        chat_id=scope.chat_id,
        category=args.category.value,
        feedback_text=args.feedback_text,
        trace_id=(trace_id or None),
        user_msg_uuid=(user_msg_uuid or None),
        repro_context=repro.model_dump(),
    )


def tool_record_user_feedback(store, arguments: dict[str, object]) -> str:
    """Insert one inferred feedback row; ``trace_id``/``user_msg_uuid`` from bind ctx."""
    bind = companion_llm_runtime_event_bind_ctx.get()
    trace_id = bind.trace_id if bind is not None else None
    user_msg_uuid = bind.user_msg_uuid if bind is not None else None
    try:
        row = build_companion_user_feedback(
            scope=store.scope,
            trace_id=trace_id,
            user_msg_uuid=user_msg_uuid,
            arguments=arguments,
        )
    except (ValidationError, AssertionError, ValueError) as exc:
        return f"ERROR: {exc}"
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        feedback_id = row.id
    return f"OK recorded feedback id={feedback_id} category={row.category}"
