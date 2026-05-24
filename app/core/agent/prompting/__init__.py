"""Legacy non-agentic chat agent system message assembly.

This package serves the old HTTP chat-completions ``Agent`` path:
``Agent`` -> ``clean_prompt_system`` -> ``prompting.assembler``.
It is not used by the agentic companion harness or ``/api/v1/chat/ws``;
companion system messages are assembled under
``companion_harness.companion.prompts``.
"""
