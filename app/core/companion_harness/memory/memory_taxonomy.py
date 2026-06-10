"""Memory path labels for companion MemoryStore (psych-style naming).

Injection headings derive from ``memory_document_catalog`` so path / bundle / taxonomy stay aligned."""

from __future__ import annotations

from .memory_document_catalog import (
    MemoryInjectionSlot,
    memory_injection_heading,
)

MEMORY_SYSTEM_HEADING_DAILY_GIST = memory_injection_heading(
    MemoryInjectionSlot.MEMORY_DAILY_GIST
)
MEMORY_SYSTEM_HEADING_SEMANTIC = memory_injection_heading(
    MemoryInjectionSlot.MEMORY_SEMANTIC
)
