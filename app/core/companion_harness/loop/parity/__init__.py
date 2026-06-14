"""Parity harness for the sidecar agentic loop (fake LLM, no network).

Verifies that ``run_agentic_loop`` matches legacy Phase 0/0.5 companion entries
(``run_bootstrap_track_sync_tool_loop``, dual-LLM foreground + tool background)
on fixed golden scenarios before wiring the sidecar into production ``run_turn``.

Fixtures live under ``loop/parity/`` rather than ``tests/`` so the smoke CLI and
pytest share the same fakes without production code importing test helpers.

- ``fixtures`` — fake 1-LLM and dual-LLM clients plus OpenAI-shaped responses
- ``golden`` — four named scenarios and ``build_golden_scenario`` bundles
- ``smoke`` — cyclopts CLI: ``run`` one scenario; ``compare-legacy`` sidecar vs bootstrap wrapper

Manual smoke::

    uv run python -m app.core.companion_harness.loop.parity.smoke compare-legacy --scenario tool_feedback
"""
