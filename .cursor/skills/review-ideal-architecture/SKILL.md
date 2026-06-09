---
name: review-ideal-architecture
description: Review a codebase snapshot against a refactoring plan and synthesize the target ideal architecture (current state + plan → modules, seams, dependency rules). Use when user wants plan-guided architecture review, ideal target structure, plan-vs-reality delta, or lifecycle closure before grill-with-docs / to-issues / TDD.
---

# Review Ideal Architecture

Synthesize **ideal architecture** = authoritative refactoring plan + current codebase snapshot + domain docs. Output is a target implementation map agents and humans can implement against — not a list of opportunistic refactors (that is `improve-codebase-architecture`).

## Lifecycle position

See [LIFECYCLE.md](LIFECYCLE.md). Typical loop: explore friction → **this skill** → grill → issues → TDD → diagnose → re-run after major merges.

## Inputs

Resolve in order; stop when a path is missing and ask the user.

| Input | Inty default | Role |
| --- | --- | --- |
| Refactoring plan | `docs/companion_harness/REFACTOR_PLAN.md` | Target package tree, phases, out-of-scope |
| Domain glossary | `docs/companion_harness/GLOSSARY.md`, `ARCH.md` | Vocabulary + invariants |
| ADRs | `docs/adr/` if present | Do not re-litigate recorded decisions |
| Code root | `app/core/companion_harness/` | Snapshot boundary |

User may pass a different plan path or scope (e.g. another package). Honor it.

## Process

### 1. Anchor

Read the plan end-to-end. Extract: target directory layout, phase order, dependency rules between layers, explicit non-goals, acceptance criteria.

Read domain docs and ADRs in the scoped area. Note terms the ideal architecture must use (`Companion Harness`, `SessionBinding`, etc.).

### 2. Snapshot

Explore the code root with the Agent tool (`subagent_type=Explore`) or direct reads. Record:

- Actual package / module tree (not aspirational)
- Files still in legacy namespaces the plan says to remove
- Import edges that violate plan dependency rules
- Tests directory mirror vs production tree

Do not guess file locations — verify with search.

### 3. Reconcile (plan ↔ reality)

Build a **phase status table**: each plan phase → `done` | `partial` | `not started` | `drift` (code moved but plan doc stale). Cite evidence (paths, import patterns).

Flag **drift** and **blockers** separately:

- **Drift**: implementation ahead of or divergent from plan wording
- **Blocker**: dependency cycle, shared file serving two target layers, missing seam

Do not propose new phases unless drift forces a plan amendment; mark those as `plan-amendment candidate`.

### 4. Synthesize ideal architecture

Merge plan target with reconciled reality into one coherent target state. Required sections — full template in [OUTPUT-FORMAT.md](OUTPUT-FORMAT.md):

1. **Scope & non-goals** — copied from plan, unchanged unless user already amended
2. **Target package tree** — every package with one-line responsibility
3. **Dependency matrix** — allowed import direction (e.g. `runtime → memory`, never reverse)
4. **Module placement** — for each not-yet-migrated file, its single target package
5. **Key seams** — where interfaces live; use vocabulary from [LANGUAGE.md](../../.agents/skills/improve-codebase-architecture/LANGUAGE.md) when describing depth
6. **Remaining migration path** — ordered slices tied to plan phases, AFK vs HITL
7. **Acceptance checks** — grep patterns, pytest scopes, smoke paths from plan

Ideal architecture describes **where code should live after the plan completes**, not optional deepenings.

### 5. Deliver

Write a self-contained HTML report to OS temp: `<tmpdir>/ideal-architecture-<timestamp>.html` (`$TMPDIR` or `/tmp`). Tailwind + Mermaid via CDN. Include:

- Mermaid diagram of **target** package dependencies
- Side-by-side **current vs ideal** tree (collapsible)
- Phase status table with badges
- Remaining migration path as ordered list

Open for the user (`xdg-open` / `open` / `start`) and give the absolute path.

Ask: **"Does this ideal architecture match your intent? Amend plan, grill, or break into issues?"**

### 6. Follow-up routing

| User says | Next skill |
| --- | --- |
| Stress-test naming / constraints | `grill-with-docs` |
| Break slices into tracker issues | `to-issues` |
| Opportunistic depth / shallow modules | `improve-codebase-architecture` |
| Hand off to another session | `handoff` (reference HTML path, do not duplicate) |

Only write into the repo (`docs/…`) when the user explicitly asks to persist the ideal architecture as a spec.

## Anti-patterns

- Do not substitute `improve-codebase-architecture` friction hunt for plan reconciliation.
- Do not invent packages not in the plan without marking `plan-amendment candidate`.
- Do not design full public APIs here — placement and seams only; interface design stays in grilling.
- Do not land HTML reports in the workspace unless asked.
