"""Dual-LLM chat branch: significance scores (1-10) + user-facing reply in one JSON envelope.

Implementation (schema, ``response_format``, parse/split): ``dual_llm_chat_branch_envelope``.

**Where the three importance integers flow (read this when changing the contract):**

- **Produced**: Foreground ``chat.completions`` may set ``response_format`` to
  ``DUAL_LLM_CHAT_RESPONSE_FORMAT`` (derived from ``DualLlmChatBranchEnvelope`` via
  ``_build_dual_llm_chat_response_format()``; ``turn.run_turn``) so the model returns JSON with
  ``user_facing_reply``, ``output_to_user``, plus ``importance_round`` /
  ``importance_user_message`` / ``importance_assistant_message``. The same envelope is used
  for async ``tool_background`` finish (see ``tool_bg_routing``). Operator guidance for scoring lives in
  ``prompts/SIGNIFICANCE_PERCEPTION.md`` (injected when
  ``include_significance_perception_slice`` is on; see ``prompts/system_messages.py`` and
  ``prompt_stack.companion_turn_tools_and_system_messages``).
- **Parsed / split**: ``split_dual_llm_chat_branch_message`` reads ``message.content`` first and
  then validated provider side-channel envelopes from ``message.reasoning`` /
  ``message.reasoning_details``. ``split_dual_llm_chat_branch_content`` handles raw string callers.
  Both return ``DualLlmChatBranchSplit`` (visible text, optional significance metadata dict whose keys
  match the three importance JSON field names, optional ``output_to_user``, ``reply_modality``,
  ``voice_message_script``). Validated payloads deserialize as ``DualLlmChatBranchEnvelope``.
  ``output_to_user`` is present only when JSON validated, else ``None``.
- **Kernel return**: ``CompanionTurnResult.significance_perception`` (``models.py``) carries
  the dict for one turn; may be ``None`` if the model returned non-JSON or parse failed
  (visible text may still be the raw string).
- **Transcript**: ``turn.run_turn`` appends an assistant JSONL row with optional
  ``significance_perception``; ``turn_engine.persist_repl_turn_transcript_rows`` can attach
  the same via ``assistant_extra`` for REPL-style paths.
- **Product DB / WS**: Foreground turns: ``app/api/v1/endpoints/chat._companion_ai_meta_from_turn_result``
  copies non-empty ``significance_perception`` into ``chat_history`` AI ``meta_data`` / WS payload.
  ``voice_message_script`` is written only when ``reply_modality`` is ``voice_message`` and the script
  is non-empty (aligned with transcript assistant rows in ``turn.run_turn``).
  Async ``tool_bg`` follow-up rows: ``ToolOutputEvent.significance_perception`` (from unified finish
  envelope via ``tool_bg_routing``) is mirrored in ``chat._build_companion_tool_background_ws_payload``.
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

from typing import Final

from .dual_llm_chat_branch_envelope import (
    DUAL_LLM_CHAT_RESPONSE_FORMAT,
    DualLlmChatBranchEnvelope,
    DualLlmChatBranchSplit,
    _build_dual_llm_chat_response_format,
    envelope_to_assistant_metadata_dict,
    parse_dual_llm_chat_envelope_from_message,
    parse_dual_llm_chat_envelope_json,
    split_dual_llm_chat_branch_content,
    split_dual_llm_chat_branch_message,
)

SIGNIFICANCE_PERCEPTION_REL: Final[str] = "SIGNIFICANCE_PERCEPTION.md"


def default_significance_perception_markdown() -> str:
    return (
        "## Significance perception (operator guidance)\n\n"
        "Score **importance** on a **1-10** scale (10 = highest): one score for the **whole turn** "
        "in context, one for the **latest user message** alone, and one for the **assistant reply** "
        "you are about to give (`user_facing_reply`).\n\n"
        "Use higher scores when the moment affects trust, safety, boundaries, major life events, "
        "or durable relationship state; use lower scores for small talk or repetition.\n"
    )
