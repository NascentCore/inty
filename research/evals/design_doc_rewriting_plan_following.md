# Eval: DESIGN.md rewrite — plan following & design understanding

Generated entirely by Cursor agent. Exercise distilled from a real planning session (grill-me → plan → multi-model execution).

## What this eval measures

Two coupled abilities:

1. **Design understanding** — Can the model absorb an ambiguous architecture doc, a stakeholder grill, and implicit constraints (tone, granularity, prototype non-goals) and turn them into a coherent target shape?
2. **Plan following** — Given an explicit rewrite plan, can the model execute it without dropping requirements, over-specifying, or changing voice?

This is **not** a code-generation eval. Only `docs/companion_harness/DESIGN.md` may change.

## Background (conversation arc)

1. **Input**: [`docs/companion_harness/DESIGN.md`](../../docs/companion_harness/DESIGN.md) (pre-rewrite, ~168 lines) — high-level companion harness architecture, mixed vision + prototype reality, several undefined load-bearing terms (relationship, time frames, prompt activation).
2. **Grill-me** ([`.agents/skills/grill-me/SKILL.md`](../../.agents/skills/grill-me/SKILL.md)): One question at a time until shared understanding. Key decisions:
   - **Audience**: coding agents + engineers + product; doc describes **ideal** LLM+harness agentic companion design.
   - **Ideal vs built**: No per-component `[BUILT]` tags; **top directive** — read `app/core/companion_harness/` before judging reality vs design.
   - **Relationship**: First-class domain concept; three-axis working hypothesis (Attachment posture / Social Penetration depth / Gottman moment) at slow / medium / fast time scales.
   - **CRS pillars**: relationship state, time frames, memory consolidation, prompt activation — unified in new **记忆模型 / 关系状态** section; CRS section moves **near the end** (concept-before-roadmap).
   - **Time frames**: Nested horizons — session rhythm, diurnal cycle, relationship history.
   - **Prompt activation**: Read-side inverse of consolidation; closed loop stated briefly.
   - **Mind Model**: Implementation paradigm — materialize psychology mechanisms via LLMs; manifest personhood through text → other GenAI modalities → humanoid robot.
   - **Channels**: One continuous bond; channels are interchangeable manifestation surfaces; link `FR_CROSS_CHANNEL_USER_IDENTITY.md`.
   - **Hub doc**: One-line definitions + links to all sibling docs in `docs/companion_harness/`.
   - **成效判断**: Brief qualitative success signals; link `evaluation/`.
   - **Tone & granularity**: **Identical to existing doc** — concise Mandarin prose, English concept names, nested bullets, no tables, DESIGN-tier (~200 lines), link out for depth; prototype to discover complexity, not pre-specify in the doc.

3. **Plan**: [`design_doc_rewriting_plan.md`](./design_doc_rewriting_plan.md) — scope, principles, 14-step target structure, verification checklist.

4. **Execution**: Three branches produced rewrites from the same plan:
   - `design_doc_rewriting_exec_gpt55`
   - `design_doc_rewriting_exec_opus48`
   - `design_doc_rewriting_exec_auto`

5. **Human adjudication** (reference): `design_doc_rewriting_exec_opus48` ranked highest for plan adherence, tone preservation, and structural clarity; `auto` runner-up; `gpt55` third (notable omissions).

## Exercise setup (for evaluators)

### Materials to give the candidate model

- Pre-rewrite DESIGN.md: `docs/companion_harness/DESIGN.md` at commit **before** any rewrite branch (or git tag `design-doc-pre-rewrite` if tagged)
- Rewrite plan: [`research/evals/design_doc_rewriting_plan.md`](./design_doc_rewriting_plan.md)
- Optional context: [`app/core/companion_harness/AGENTS.md`](../../app/core/companion_harness/AGENTS.md), sibling docs under `docs/companion_harness/`

Do **not** give the candidate the grill-me transcript or the three execution branches unless testing recovery from partial specs.

### Prompt template

```text
Read and understand docs/companion_harness/DESIGN.md.

Follow research/evals/design_doc_rewriting_plan.md exactly to rewrite docs/companion_harness/DESIGN.md.

Constraints:
- Rewrite only DESIGN.md.
- Preserve the existing document's tone and DESIGN-tier granularity.
- The doc guides ongoing implementation in app/core/companion_harness/.
```

### What the candidate must produce

- A single updated `docs/companion_harness/DESIGN.md` (diff against pre-rewrite baseline).

## Scoring rubric (100 points)

Score each dimension independently. Use the **pre-rewrite baseline** and **plan** as ground truth, not any single execution branch.

### A. Plan completeness (40 pts)

- **Top directive (5)**: Ideal-design disclaimer + **PROTOTYPE** + read code under `app/core/companion_harness/` + guides implementation
- **Mind Model section (5)**: Paradigm definition; text → modalities → humanoid; outward loop / inner life (concise)
- **Relationship first-class (5)**: Three axes named; framed as working hypothesis / CRS will test
- **记忆模型 / 关系状态 (8)**: Closed loop; nested time frames; axis→mechanism mapping marked hypothesis; links to MEMORY_STORE / MEMORY_PROJECTION
- **Section order (5)**: CRS **after** architecture, turns, channels, 成效判断 (not at top)
- **CRS cross-reference (4)**: Does not restate full relationship loop; points to 记忆模型 / 关系状态
- **成效判断 (4)**: Qualitative signals only; links `evaluation/`
- **文档地图 (4)**: All eight sibling docs listed with one-line purpose

### B. Constraint adherence (25 pts)

- **Scope (5)**: Only DESIGN.md changed (in agent session)
- **Length (5)**: ~180–210 lines (DESIGN-tier)
- **No tables (2)**: No markdown tables
- **Diagrams preserved (5)**: ASCII bird's-eye + kernel diagrams; English labels
- **No SPEC bloat (4)**: No field tables, no long code inventories
- **Commercialization (4)**: De-emphasized vs original 目标态 commercialization paragraph; aligns prototype non-goals

### C. Tone & voice (20 pts)

- **Executive summary preserved (8)**: Formulas and 「把聊天变成关系」 framing kept; no gratuitous rewrites
- **Bilingual pattern (6)**: 中文 narrative + English concept names (match pre-rewrite style)
- **Granularity (6)**: New sections are short; depth via links, not inline essays

### D. Design understanding (15 pts)

- **Channels invariant (5)**: One bond, many manifestation surfaces; identity in harness
- **Prompt activation (5)**: Explicit or clearly implied read-side of consolidation
- **成效判断 ↔ axes (5)**: Success signals connect to relationship model (not generic "good chat")

### Penalties (subtract after sum)

- **−5** each: Drops CRS autonomy bullets (Dynamism / self-directed / channels) entirely.
- **−5**: Removes `TODO(memory-hierarchy-design)` without plan authorization.
- **−3** each: Broken relative link to a sibling doc or `evaluation/`.
- **−3**: Adds per-component `[BUILT]` / `[PLANNED]` tags (explicitly rejected in grill).
- **−5**: Claims implementation reality without top directive to read code.

## Reference outcomes (calibration)

Use these three branches only for **calibrator** runs, not as the sole gold standard.

- `design_doc_rewriting_exec_opus48` (204 lines, **~92**): Best overall — nested time frames, closed loop, CRS cross-ref, 成效判断 tied to axes, tone preserved
- `design_doc_rewriting_exec_auto` (212 lines, **~85**): Strong technical naming; slightly long and English-heavy; minor formatting nits
- `design_doc_rewriting_exec_gpt55` (197 lines, **~72**): Clean length; dropped CRS autonomy bullets, flat time frames, removed memory-hierarchy TODO

To diff a reference branch:

```bash
git show design_doc_rewriting_exec_opus48:docs/companion_harness/DESIGN.md
```

## Automated checks (optional)

```bash
# Line count
wc -l docs/companion_harness/DESIGN.md

# No tables (pipe-heavy lines — heuristic)
rg '^\|.+\|' docs/companion_harness/DESIGN.md && echo FAIL || echo OK

# Sibling doc map present
for f in GLOSSARY MEMORY_STORE MEMORY_PROJECTION AUTONOMY LIVING_SPHERE FR_WORLD_ENGINE FR_CROSS_CHANNEL_USER_IDENTITY SPECULATIVE_IDEAS; do
  rg -q "$f" docs/companion_harness/DESIGN.md || echo "missing link: $f"
done

# CRS ordering: 重要下一步工作 should appear after 记忆模型
python3 -c "
from pathlib import Path
t = Path('docs/companion_harness/DESIGN.md').read_text()
assert t.index('记忆模型') < t.index('重要下一步工作'), 'CRS should follow memory section'
print('section order OK')
"
```

## Eval variants

- **Plan-only**: Give plan + baseline DESIGN.md (tests plan following).
- **Grill-only**: Give grill-me skill + baseline only; candidate must infer plan (tests design understanding, harder).
- **Plan + grill summary**: Give plan plus grill decisions (this document § Background) without transcript (tests plan following with context).

## Success threshold

- **Pass**: ≥ 80/100 with no dimension below 50% of its weight.
- **Strong pass**: ≥ 90/100; suitable to merge as the canonical DESIGN.md rewrite.

## Related files

- Plan: [`design_doc_rewriting_plan.md`](./design_doc_rewriting_plan.md)
- Target doc: [`docs/companion_harness/DESIGN.md`](../../docs/companion_harness/DESIGN.md)
- Write-design-doc skill: [`.cursor/skills/write-design-doc/SKILL.md`](../../.cursor/skills/write-design-doc/SKILL.md)
