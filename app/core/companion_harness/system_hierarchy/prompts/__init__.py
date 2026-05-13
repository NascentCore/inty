"""Companion system hierarchy prompt assets.

Holds the canonical prompt MD seed files (`AXIOM.md`, `BOOTSTRAP.md`, `TOOLS.md`,
`SIGNIFICANCE_PERCEPTION.md`) used by the MemoryStore seeding layer and the
`system_messages` submodule that builds the system-message stack injected before
each companion LLM round.

By convention (see `app/AGENTS.md`) `__init__.py` files contain only this docstring;
import `build_system_messages` / `build_system_prompt` from
`app.core.companion_harness.system_hierarchy.prompts.system_messages` directly.
"""
