---
name: write-design-doc
description: >-
  Write or refresh DESIGN-tier architecture overview docs from codebase recon,
  not by copying existing doc wording. Covers doc tiers, code discovery order,
  ASCII diagrams, Epic pointers, and self-check against source. Use when the user
  asks to write or update DESIGN.md, architecture overview, companion harness
  design doc, or docs/companion_harness documentation from code.
---

# Write DESIGN-tier architecture doc

Generated entirely by Cursor agent. Workflow: **recon code → pick tier → write ~200-line bird's-eye → self-check**.

**Do not** mirror an existing `DESIGN.md`'s phrasing. **Do** derive structure from code, package `AGENTS.md`, and root [AGENTS.md](/AGENTS.md).

## When to use

- New or major refresh of `docs/**/DESIGN.md` (or equivalent architecture overview).
- User asks to document system architecture **from the codebase**.

**Not for**: SPEC docs (`MEMORY_STORE.md`, `AUTONOMY.md`), glossaries, protocol field lists, gap audit matrices.

## Truth order

1. Code + package `AGENTS.md`
2. Root `AGENTS.md` (product vision, PROTOTYPE, dir boundaries)
3. Existing `docs/` siblings — **link only**, do not duplicate

## Step 0: Declare tier

- **DESIGN-tier**: bird's-eye (~200 lines); nested bullets; no tables; details → issues / SPEC / code paths.
- **SPEC / GLOSSARY / FR**: different depth; see [docs/AGENTS_DRAFT.md](/docs/AGENTS_DRAFT.md) if present.

If tier is DESIGN, **do not** embed SPEC depth (field tables, lifecycle step lists, 15-row gap matrices).

## Step 1: Code recon (before writing)

Generic order for any subsystem:

1. Root + package `AGENTS.md` — PROTOTYPE, non-goals, main entry paths.
2. **Entry / adapter layer** — HTTP, WS, ops bridges; find orchestration shell (not kernel).
3. **Kernel** — manager/service → core execution (`run_turn`, pipelines, state machines).
4. **Runtime loops** — `StrEnum` / track types + class docstrings (trigger, visibility, poll order).
5. **Invariants** — dedicated `*_invariants.py`, CI enforcement scripts.
6. **Persistence** — store module, ORM table names, migration dir.
7. **Observability** — tracing, runtime events, logging.
8. **Roadmap** — `grep 'TODO.*#[0-9]+'` in target tree; cluster Epics for roadmap section.
9. **Exclusions** — `/experimental/`, maintenance-mode APIs, unwired contracts.

Record each stop as: `path` + one-line responsibility + PROTOTYPE note if any.

**Companion Harness**: follow the full checklist in [reference-companion-harness.md](reference-companion-harness.md).

## Step 2: Write (DESIGN-tier sections)

Use recon notes to fill this skeleton (omit sections with no grounded content):

```markdown
# …: 架构说明
## 概要（Executive Summary）
## 重要下一步工作
## 目标态
## 系统实现规范
## 目标架构图
### Harness 内核（职责展开）   ← rename for non-harness systems
### 回合运行时（端到端）
## … domain sections (memory, loops, channels, etc.)
## 代码层技术选型（Tech Stack）
## 扩展设计
```

Section rules:

- **概要**: product gap + harness role; optional formula line; `### 现状` with `**PROTOTYPE**` if code says so.
- **重要下一步工作**: meta lines then Epic-only lines (see Step 3).
- **目标态**: one paragraph; target architecture from module docstrings can enter diagrams.
- **系统实现规范**: short bullets from invariants / fail-visible principles.
- **Runtime loops**: each track — **触发** / **用户可见**; mark non-turn paths (e.g. Dreaming).
- **记忆 / channels / stack**: one-liner + pointer to SPEC or code; list enums from code.
- **扩展设计**: link to FR or sibling docs.

**Depth**: one ASCII diagram + one sentence beats a second paragraph; SPEC topics get a link, not a copy.

## Step 3: Diagrams

Three diagrams when the system has channel + kernel + E2E flow:

1. **System context** — users → channel → access → kernel ↔ adjacent worlds → persistence.
2. **Kernel interior** — entry/orchestration → awake work → memory/tools; side paths (inner tick, batch jobs).
3. **End-to-end** — match actual service call chain; may show target `inbound queue` even if not a package yet — **do not claim implemented** in prose unless code confirms.

Diagram rules ([docs/AGENTS.md](/docs/AGENTS.md)):

- ASCII only; **English** labels inside boxes.
- `·` for lists; `──►` / `◄──►` for flow.
- No mermaid; no file paths inside diagrams.

## Step 4: Format

- Narrative: 简体中文; concepts, enums, diagram text, identifiers: **English** (match code names).
- Multidimensional facts: **nested bullets**; no tables (DESIGN-tier).
- Code pointers: backtick paths; no large paste blocks.
- No ``double-tick`` for concept names.
- Roadmap meta (copy when using Epic-only roadmap):

  ```
  Only reference Epic GitHub issues. Do not include details.
  State of the Epic GitHub issues are in the GitHub issues themselves.
  ```

- Each Epic: one line — `Epic [#NNNN](url) — A × B × C`
- Target vs current: `**还不是…**`, `**PROTOTYPE**`, code `TODO` tensions; no long gap tables.
- Analogies: one sentence max.

## Step 5: Self-check (against code, not old DESIGN.md)

- [ ] Every production track/loop in code appears in doc (including e.g. `INNER_TICK_AUTONOMY` if in `CompanionTurnTrack`).
- [ ] Phase invariants match `*_invariants.py` + CI scripts.
- [ ] All wired channel/entry paths listed (not only WebSocket).
- [ ] Orchestration shell not described as fully realized inbound runtime unless code has it.
- [ ] No maintenance-mode or `/experimental/` paths as primary architecture.
- [ ] Epic numbers from code `TODO`, not memory.
- [ ] No duplicate SPEC content (memory, autonomy, world engine each link once).

## Repo pointers

- Global doc format: [docs/AGENTS.md](/docs/AGENTS.md)
- Draft rationale (optional): [docs/AGENTS_DRAFT.md](/docs/AGENTS_DRAFT.md)
- Companion example output: [docs/companion_harness/DESIGN.md](/docs/companion_harness/DESIGN.md)
- Companion recon detail: [reference-companion-harness.md](reference-companion-harness.md)
