"""Companion Harness prompting layer: prompt bundles and track-composed assembly.

Holds value objects consumed when building system-message stacks for LLM invocations.
Turn orchestration and MemoryStore I/O live in sibling packages; they import from here.

Assembly design (content categories vs runtime organization): see
``docs/imate/companion_harness/DESIGN.md`` before changing stack order or adding slices.

TODO(!3453): Add ``PromptTemplate`` dataclass (named-slot render API aligned with Jinja2).
https://github.com/NascentCore/inty/issues/3453
"""
