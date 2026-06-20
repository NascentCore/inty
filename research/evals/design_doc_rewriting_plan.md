---
name: rewrite companion design
overview: Rewrite `docs/companion_harness/DESIGN.md` into a clearer DESIGN-tier hub for ideal LLM+harness agentic companion architecture, while preserving the existing bilingual tone, conceptual granularity, and role as guidance for ongoing `app/core/companion_harness/` implementation.
todos:
  - id: rewrite-directive-summary
    content: Add the top directive and refresh the executive summary without changing the doc's tone.
    status: pending
  - id: rewrite-mind-domain
    content: Introduce Mind Model and first-class relationship domain concepts at DESIGN-tier granularity.
    status: pending
  - id: rewrite-memory-relationship
    content: Replace the memory stub with the concise relationship-state closed-loop section.
    status: pending
  - id: rewrite-runtime-channels
    content: Refresh turn tracks and channels with links and continuity invariants.
    status: pending
  - id: rewrite-roadmap-docmap
    content: Move CRS near the end and add success signals plus the companion harness doc map.
    status: pending
  - id: verify-design-doc
    content: Self-check style, links, diagrams, and ideal-vs-code directive after the rewrite.
    status: pending
isProject: false
---

# Companion Harness DESIGN Rewrite Plan

## Scope

Rewrite only `docs/companion_harness/DESIGN.md`.

Do not change code, sibling docs, AGENTS files, diagrams beyond necessary wording/placement, or implementation behavior. The rewrite should preserve the current doc's style: concise Mandarin architecture prose, English concept names and identifiers, nested bullets, no tables, ASCII diagrams with English labels, and DESIGN-tier granularity.

## Rewrite Principles

- Keep the document about the **ideal target-state design** of an agentic companion built on LLM + harness.
- Add a top directive: readers must inspect `app/core/companion_harness/` before judging which parts are implemented today.
- Make the doc guide implementation without becoming a code inventory or SPEC.
- Prefer one-line definitions and links to sibling docs over long elaboration.
- Keep CRS, relationship state, time frames, memory consolidation, and prompt activation conceptual enough for prototypes to reveal complexity.
- Length budget: stay DESIGN-tier (around 200 lines total); each newly added section is only a few lines so the doc does not bloat past its current granularity.
- Mark any axis-to-mechanism mapping as a current working hypothesis, consistent with the top directive to read code before judging reality.

## Target Structure

1. Keep the title: `# Companion Harness: 架构说明`.
2. Add a short directive block immediately after the title:
   - This doc describes ideal design, not a reality checklist.
   - `companion_harness` is still **PROTOTYPE** (retain this marker from the current 现状 subsection).
   - Coding agents and engineers must read `app/core/companion_harness/` before making implementation claims.
   - Use this doc to guide ongoing implementation direction.
3. Refresh `概要（Executive Summary）` while preserving its current tone:
   - Keep the formulas `Companion Harness + LLM = Inty` and `Inty + Memory = Personal Companion`.
   - Keep the “把聊天变成关系” framing.
   - Remove the standalone `现状` subsection or fold it into the directive.
4. Add `Mind Model` after the summary:
   - Define it as an implementation paradigm: materialize psychology-research mechanisms using LLMs to simulate a person.
   - Mention manifestation through text now, other GenAI modalities soon, eventually humanoid embodiment.
   - Keep outward loop / inner life as one concise current-materialization paragraph.
5. Move `重要下一步工作` near the end, after architecture and runtime concepts.
6. Keep `目标态：内核与产品`, but align wording with prototype non-goals:
   - Avoid over-emphasizing commercialization as an implementation concern for the harness prototype.
   - Link world-engine / sub-agent detail to `docs/companion_harness/FR_WORLD_ENGINE.md`.
7. Expand `Domain concepts` at the same bullet granularity as today:
   - Add `relationship` as the first-class center.
   - Define the current working decomposition: `Attachment posture`, `Social Penetration depth`, `Gottman moment`.
   - Keep these as design hypotheses CRS will test, not a full psychology spec.
   - Add one-line links for `Living Sphere`, `Techno Core`, `World Engine`, `Autonomy`, `MemoryStore`, and `Prompt slice` where useful.
8. Preserve `目标架构图` and `Harness 内核（职责展开）` diagrams with only minimal label/section placement changes.
9. Replace `记忆模型` with `记忆模型 / 关系状态`:
   - State the closed loop briefly: behavior creates relationship signals; consolidation writes them into memory; prompt activation reads them back into future behavior.
   - Define `time frames` as nested horizons: session rhythm, diurnal cycle, relationship history.
   - Map relationship axes to mechanisms at high level (phrased as a current working hypothesis, not committed implementation):
     - `Gottman moment` → per-turn appraisal signals such as significance / recall.
     - `Social Penetration depth` → dreaming / memory consolidation.
     - `Attachment posture` → long-lived semantic memory and prompt posture.
   - Link details to `MEMORY_STORE.md`, `MEMORY_PROJECTION.md`, and relevant code rather than expanding fields.
10. Keep `Turn 轨道` section, but tune wording to match the current ideal-doc role:
    - Keep trigger / visibility bullets.
    - Link `AUTONOMY.md` from `AUTONOMY`.
    - Keep `Dreaming` explicitly non-turn.
11. Refresh `Channels`:
    - State that channels are interchangeable manifestation surfaces for one continuous relationship.
    - Preserve the social-scenario analogy, but keep it short.
    - Link identity-resolution detail to `FR_CROSS_CHANNEL_USER_IDENTITY.md`.
12. Add a concise `成效判断` section:
    - Qualitative signals only: re-engagement, remembered disclosures, successful bids/repairs, welcome proactivity.
    - Link to `evaluation/` for evaluation machinery.
13. Add `重要下一步工作` near the end:
    - Keep CRS as the single next step.
    - Keep epic-only reference style: `Epic [#3341](...) — psychology × time frames × harness`.
    - Cross-reference the `记忆模型 / 关系状态` section instead of restating relationship state / time frames / consolidation / activation, to avoid duplication.
    - Do not add implementation subplans here.
14. Add `文档地图 / See also`:
    - One-line purpose for each sibling doc in `docs/companion_harness/`.
    - Include `GLOSSARY.md`, `MEMORY_STORE.md`, `MEMORY_PROJECTION.md`, `AUTONOMY.md`, `LIVING_SPHERE.md`, `FR_WORLD_ENGINE.md`, `FR_CROSS_CHANNEL_USER_IDENTITY.md`, and `SPECULATIVE_IDEAS.md`.

## Verification

- Read the rewritten `docs/companion_harness/DESIGN.md` end-to-end and check that it still sounds like the existing doc: concise, conceptual, bilingual, and architecture-level.
- Confirm diagrams remain ASCII and diagram labels remain English.
- Confirm no markdown tables were introduced.
- Confirm the doc does not claim implementation reality without telling readers to inspect code.
- Confirm every sibling doc in `docs/companion_harness/` is either linked in context or listed in the doc map.
- Confirm every markdown link in the doc resolves to an existing path (sibling docs, `evaluation/`, code paths, epic URL).
- Confirm the doc stays within the DESIGN-tier length budget (around 200 lines) and that new sections did not change the existing granularity.
- Confirm the rewrite guides `app/core/companion_harness/` implementation direction without drifting into product/commercialization detail or SPEC-level field lists.