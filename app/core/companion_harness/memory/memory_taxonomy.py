"""Memory path labels for companion MemoryStore (psych-style naming).

Maps logical paths to daily gist / semantic terminology used in system injection
headings and docs. Daily gist lives at ``memory/daily/{date}.md``; semantic at ``MEMORY.md``.

Target: **slot** moves membership + heading from code into MemDoc frontmatter data;
this module's headings become defaults until ``MemDocFrontmatter.heading`` lands (#3549, #3713).

TODO(memory-hierarchy-design): Design conceptual & logical memory hierarchy (layers, naming, — #3405
lifecycle, injection rules)—#3405. Current headings are placeholders until design closes;
conversation options (Letta context hierarchy, five-layer sketch, etc.) are candidates only.
"""

from __future__ import annotations

# TODO(consolidate-memory-doc-definitions): Should include doc name, attributes, path to a MemDoc type. — #3549
# So to note scatter aspects of memory doc to multiple source files.

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
