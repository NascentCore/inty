"""Companion Harness memory layer: MemoryStore, document path mapping, registry, and seeds.

This package holds the persisted workspace document model (append-only versions in Postgres
when a repository is bound), the process-local MemoryStore registry keyed by
``CompanionScope``, workspace template seeds, layered memory taxonomy labels, the
post-turn memory update pipeline, and transcript compaction helpers used when assembling
LLM context from ``transcript.jsonl``.

Runtime turn orchestration, tools, and WebSocket coordination live in sibling packages;
they import from here rather than the reverse.

TODO(memory-context-hierarchy): Document conceptual memory layers and path mapping — #3405.
"""
