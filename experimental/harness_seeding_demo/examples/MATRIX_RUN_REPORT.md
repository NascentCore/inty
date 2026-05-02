# Harness experiment report: historical vs 2026-05-02 run

**Chinese summary (settings + conclusions)**: [EXPERIMENT_SUMMARY.md](EXPERIMENT_SUMMARY.md)

**One-sentence takeaway**: With a fixed kernel and user script, workspace seeds only separate clearly on first-pass turn once harness noise is removed (e.g. status-line tool without DB), the dialogue arc is long enough, and multiple strict heuristic rubrics are used; short scripts plus a single lenient rubric saturate and make all seeds look the same.

This file contrasts three experiment regimes. Raw JSON for the latest run stays under `results/` (gitignored); this report copies **aggregated numbers only**.

---

## Run A (legacy, noisy)

- **When**: 2026-05-01, path `results/matrix_20260501_155404/` (deleted in later cleanups; figures taken from session notes).
- **Protocol**: 3-line script `work_stress_script.json`, **single** rubric (~`default` @ 0.85), **one** repetition per seed, **before** default disable of `tool_update_agent_status_line` (Postgres often down -> empty `assistant_text` on some turns).

| seed | first_pass (single rubric) |
|------|----------------------------|
| baseline | 2 |
| empathic | 1 |
| functional | 1 |
| teammate_off | 1 |
| teammate_on | null |

**Interpretation**: teammate_on and baseline were distorted by tool/DB failures and empty replies; not comparable to later runs.

---

## Run B (3-line, harness fixed)

- **When**: 2026-05-01, `results/matrix_rerun_20260501_162708/`.
- **Protocol**: same 3-line script, single rubric @ 0.85, 1 rep, status-line tool off by default.

| seed | first_pass |
|------|------------|
| all five | 1 |

**Interpretation**: after removing DB-status noise, **no seed separation** on the short script with one rubric.

---

## Run C (this execution, strict multi-rubric)

- **When**: 2026-05-02.
- **Output dir**: `experimental/harness_seeding_demo/results/matrix_exp_20260502/`
- **Protocol**:
  - Script: **12 lines** `fixtures/work_stress_script_12.json`
  - Rubrics: `default` (0.85), `strict_emotional` (1.0), `premature_solution` (1.0), `boundary_tone` (1.0)
  - Repetitions: **3** per seed
  - Model: `deepseek/deepseek-v3.2` (OpenRouter), key from `devops/config.yaml.local`
  - `matrix_errors.json`: **[]**

### Aggregated `matrix_summary.json`

| seed | median_first_pass_default | all_passed_turn1_default | median strict_emotional | all_passed_turn1_strict | median premature | all_passed_turn1_premature | median boundary | all_passed_turn1_boundary |
|------|---------------------------|--------------------------|-------------------------|-------------------------|------------------|----------------------------|-----------------|-------------------------|
| baseline | 1 | yes | 1 | **no** | 1 | yes | 1 | yes |
| empathic | 1 | yes | 1 | **no** | 1 | yes | 1 | **no** |
| functional | 1 | yes | 1 | **yes** | 1 | yes | 1 | **no** |
| teammate_off | 1 | yes | 2 | **no** | 1 | yes | 1 | yes |
| teammate_on | 1 | yes | **5** | **no** | 1 | yes | **2** | **no** |

### teammate_on strict_emotional by repetition

From `matrix_all_repetitions.json`: turns **1**, **5**, **7** across reps (high variance).

---

## Cross-run conclusions

1. **Infrastructure matters**: Run A vs B shows identical seeds diverged mainly due to **DB-backed tools and empty assistant bodies**, not due to SOUL text alone.
2. **Short script + one lenient rubric saturates**: Run B gives **all first_pass = 1**; the experimental question needs longer stress arcs and/or stricter metrics (Run C).
3. **Multi-rubric separates seeds under Run C**:
   - **functional** is the only seed with **three reps all passing strict_emotional on turn 1** (still fails boundary_tone consistency because the rubric often wants explicit invitation phrases).
   - **teammate_on** pays the highest median cost on **strict_emotional (5)** and **boundary_tone (2)** despite USER prefill; variance across reps (1 / 5 / 7) indicates **sampling noise dominates** for that seed with this model.
   - **premature_solution** stays at **1** for every seed here: with this script and model, **numbered advice rarely appears before reflection** in the first ~320 chars, so this rubric did not discriminate.
4. **What not to claim**: These rubrics are **keyword heuristics**, not human-rated empathy. **teammate_on** underperforming on strict_emotional does **not** prove team prefill hurts users; it may reflect longer tool preamble, style without two strain tokens early, or RNG.

---

## Recommended next steps

- Raise **N** (repetitions) or fix temperature for stable seed comparisons.
- Replace or augment **premature_solution** with a metric that fires more often (e.g. detect bullet lists without preceding empathy sentence anywhere in first reply).
- Add **human spot checks** on `teammate_on` rep 2/3 transcripts where strict_emotional latched late.
