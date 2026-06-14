"""Sidecar agentic loop: interchangeable 1-LLM / 2-LLM mechanisms with per-call-streaming.

Delegates to Phase 0/0.5 public entries (``run_in_turn_sync_tool_loop``,
``run_dual_llm_foreground_chat``, ``run_tool_background_loop``). Single entry:
``run_agentic_loop`` in ``runner`` module.
"""
