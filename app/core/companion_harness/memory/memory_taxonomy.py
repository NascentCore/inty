"""Memory path labels for companion MemoryStore (psych-style naming).

Maps logical paths to daily gist / semantic terminology used in system injection
headings and docs. Daily gist lives at ``memory/daily/{date}.md``; semantic at ``MEMORY.md``.
"""

from __future__ import annotations

# System injection section lead-in (plain text, no markdown H2; kept stable for tests).
MEMORY_SYSTEM_HEADING_DAILY_GIST = (
    "MEMORY — daily gist / 单日摘要（memory/daily/{date}.md）\n\n"
)
MEMORY_SYSTEM_HEADING_SEMANTIC = (
    "MEMORY — semantic memory / 语义记忆（MEMORY.md）\n\n"
)
COMPANIONSHIP_SYSTEM_HEADING = (
    "COMPANIONSHIP — 陪伴关系 framing（COMPANIONSHIP.md）\n\n"
)
