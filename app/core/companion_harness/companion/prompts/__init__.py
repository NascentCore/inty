"""Companion prompt assets package.

Holds the canonical prompt MD seed files (`AXIOM.md`, `INTY.md`, `SUBCONSCIOUS.md`, `SAFETY.md`,
`BOOTSTRAP.md`, `TOOLS.md`, `SIGNIFICANCE_PERCEPTION.md`) used by
`app.core.companion_harness.memory.memory_store_scope.load_template_seed_text`, plus the
`system_messages` submodule that builds the system-message stack injected before each
companion LLM round.

By convention (see `app/AGENTS.md`) `__init__.py` files contain only this docstring;
import `build_system_messages` from
`app.core.companion_harness.companion.prompts.system_messages` directly.
"""
