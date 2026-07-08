"""Companion Harness prompting layer: prompt bundles and track-composed assembly.

Holds value objects consumed when building system-message stacks for LLM invocations.
``system_messages.py`` is the system-prefix slice assembly entry (Doctrine through
Contextual categories). Turn orchestration and MemoryStore I/O live in sibling
packages; they import from here.

Assembly design (content categories vs runtime organization): see
``docs/imate/companion_harness/DESIGN.md`` before changing stack order or adding slices.

``PromptTemplate`` (``prompting.template``) provides named-slot Jinja2 rendering (#3453).

Target memory projection (order + budget + render) lives in ``prompting.projection``
after ``memory.retrieval`` selection (#3521). User-readable summary:
``docs/imate/companion_harness/MEMORY_STORE.md`` § Memory projection.
"""
