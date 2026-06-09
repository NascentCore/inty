# Ideal architecture — output sections

<!-- Generated entirely by Cursor agent. Template for HTML report body and optional persisted spec. -->

Use project domain vocabulary in every heading and bullet. Architecture depth terms (`module`, `seam`, `depth`) follow [LANGUAGE.md](../../.agents/skills/improve-codebase-architecture/LANGUAGE.md).

## 1. Executive summary

Three sentences max:

- Current migration posture (e.g. "Phase 3.1 done, 3.2–3.6 not started")
- Biggest gap between snapshot and plan
- Recommended next slice

## 2. Scope & non-goals

Quote or paraphrase from the refactoring plan. Do not silently drop non-goals.

## 3. Target package tree

```
app/core/companion_harness/
├── runtime/          # one-line responsibility
├── memory/
├── ...
```

Every leaf package: **responsibility**, **must not** (anti-responsibilities).

## 4. Dependency matrix

| From | May import | Must not import |
| --- | --- | --- |
| `runtime/` | `memory/`, `tools/`, … | — |
| `memory/` | `contracts/`, providers via seams | `runtime/` |

Mermaid `flowchart TB` with allowed edges only.

## 5. Module placement ledger

Table for every file still outside its target package:

| Current path | Target package | Plan phase | Status |
| --- | --- | --- | --- |
| `companion/turn.py` | `runtime/` | 3.4 | not started |

Status: `done` | `partial` | `not started` | `drift`.

## 6. Key seams

For each target package, one **external seam** (what callers depend on) and whether a second adapter exists yet.

Example:

- **MemoryStore** (`memory/`): external seam = scope-scoped document read/write; adapters = Postgres store, test fakes.

No full type signatures — placement and leverage only.

## 7. Phase reconciliation

| Plan phase | Status | Evidence | Notes |
| --- | --- | --- | --- |
| 3.1 `memory/` | partial | `memory/` exists; `companion/` still holds X | … |

## 8. Remaining migration path

Ordered list tied to plan phases. Each item:

- **ID** — align with slice tracker if present (e.g. S2)
- **Title**
- **Type** — AFK | HITL
- **Blocked by**
- **Verification** — pytest path or grep

## 9. Acceptance checks

Concrete commands from plan:

```bash
pytest tests/app/core/companion_harness
rg 'app\.core\.companion_harness\.companion' app/
```

## 10. Plan-amendment candidates

Only if snapshot forces plan doc updates. Each: **what diverged**, **proposed plan edit**, **why not just code drift**.

## HTML styling notes

- Phase badges: `done` green, `partial` amber, `not started` gray, `drift` orange
- Current vs ideal trees: two columns; highlight files that still need `git mv`
- Link to plan paths as `file://` or repo-relative paths in a monospace footer
