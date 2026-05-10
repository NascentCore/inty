# Memory

## 2026-05-10

### Experience profiles: one authoritative frozenset, derive subsets

When companion `context_mode` / experience profiles use StrEnum, derive overlapping subsets with set algebra on the authoritative frozenset (e.g. `_PRIVATE_MEMORY_PROFILE_IDS - {ExperienceContextMode.INTIMATE}` for shared clause bodies) instead of maintaining a second parallel frozenset that can drift.
