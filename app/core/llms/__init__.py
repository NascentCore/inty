"""LLM client entry points for companion harness and legacy OpenAI-compatible callers.

``client`` holds companion-specific ``CompanionLLMClient`` / ``AsyncLlmClient``.
``openai_client`` holds legacy global-config factories and memory-extraction helpers.
Both delegate HTTP transport to ``companion_harness.providers.openai_compatible_clients``.
"""
