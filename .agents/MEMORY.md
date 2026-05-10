# Memory

## 2026-05-10

### Experience profiles: one authoritative frozenset, derive subsets

When companion `context_mode` / experience profiles use StrEnum, derive overlapping subsets with set algebra on the authoritative frozenset (e.g. `_PRIVATE_MEMORY_PROFILE_IDS - {ExperienceContextMode.INTIMATE}` for shared clause bodies) instead of maintaining a second parallel frozenset that can drift.

### Session state naming paradigm (Binding / Corpus / Sidecar)

Full spec: [/.agents/maintenance/AGENTIC_KERNEL_ARCH_ENHANCEMENT.md](/.agents/maintenance/AGENTIC_KERNEL_ARCH_ENHANCEMENT.md). Summary: replace overloaded `workspace` with **`SessionBinding`** + **`SessionCorpus`** (`corpus_rel_key`) + **`DurableSidecar`** / **`ProcessPrivate`** by durability contract; **no `data_mount` in the core paradigm** when corpus authority is repository/DB and REPL is not a companion runtime.
