"""Layered memory path labels for companion MemoryStore (psych-style naming).

Maps logical paths to episodic / gist / semantic terminology used in system injection
headings and docs. Paths remain implemented as ``memory/daily/{date}.md``,
``memory/{date}.md``, and ``MEMORY.md``."""

from __future__ import annotations

# System injection section titles (must stay stable for tests and LLM-visible rubric).
MEMORY_SYSTEM_HEADING_EPISODIC = (
    "## MEMORY - episodic memory / 情景记忆（memory/daily/{date}.md）\n\n"
)
MEMORY_SYSTEM_HEADING_GIST = (
    "## MEMORY - gist memory / 单日摘要（memory/{date}.md）\n\n"
)
MEMORY_SYSTEM_HEADING_SEMANTIC = (
    "## MEMORY - semantic memory / 语义记忆（MEMORY.md）\n\n"
)
