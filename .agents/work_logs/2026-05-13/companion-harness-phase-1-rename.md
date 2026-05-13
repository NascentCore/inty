Summary: Completed Phase 1 of the Companion Harness refactor by moving the core package and tests from `agentic_kernel` to `companion_harness`.

- Moved `app/core/agentic_kernel/` to `app/core/companion_harness/`.
- Moved `tests/app/core/agentic_kernel/` to `tests/app/core/companion_harness/`.
- Replaced Python imports and path strings that referenced the old package.
- Added the new package docstring and updated local package guidance.
- Verified the migrated core tests and affected chat/WebSocket test collection paths.

Follow-ups: Phase 2 should move and update remaining docs, tools, skills, and maintenance references that still intentionally point at the old path.
