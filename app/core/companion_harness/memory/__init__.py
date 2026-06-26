"""Companion Harness memory layer: MemoryStore, document path mapping, registry, and seeds.

This package holds the persisted workspace document model (append-only versions in Postgres
when a repository is bound), the process-local MemoryStore registry keyed by
``CompanionScope``, workspace template seeds, layered memory taxonomy labels, the
post-turn memory update pipeline, and transcript compaction helpers used when assembling
LLM context from ``transcript.jsonl``.

MemoryStore is the single source of truth. Read-side **activation** (which slices enter
the prompt) is specified in ``memory.retrieval`` and implemented toward
``prompting.projection`` → ``PromptPlan`` (#3521, #3523). Write-side consolidation
stays in dreaming batch only.

Runtime turn orchestration, tools, and WebSocket coordination live in sibling packages;
they import from here rather than the reverse.

TODO(memory-hierarchy-design): Agree conceptual & logical memory hierarchy in docs—#3405.
"""
