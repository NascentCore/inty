"""Memory path labels for companion MemoryStore (psych-style naming).

Maps logical paths to daily gist / semantic terminology used in system injection
headings and docs. Daily gist lives at ``memory/daily/{date}.md``; semantic at ``MEMORY.md``.

TODO(memory-context-hierarchy): Expand into full context-hierarchy taxonomy (pinned blocks,
recall stream, archival semantic, private working stream, external knowledge) per design
issue #3405; align headings with ``docs/companion_harness/DESIGN.md``.
"""

from __future__ import annotations

# System injection section lead-in (plain text, no markdown H2; kept stable for tests).
MEMORY_SYSTEM_HEADING_DAILY_GIST = (
    "MEMORY — daily gist / 单日摘要（memory/daily/{date}.md）\n\n"
)
MEMORY_SYSTEM_HEADING_SEMANTIC = (
    "MEMORY — semantic memory / 语义记忆（MEMORY.md）\n\n"
)
