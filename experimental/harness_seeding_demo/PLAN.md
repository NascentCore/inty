# harness_seeding_demo implementation plan

**Hard rule**: no edits under `app/core/agentic_kernel/`. All code lives under `experimental/harness_seeding_demo/`.

---

## Phase 0 - Freeze the contract

- Lock the **kernel entrypoint**: `CompanionManager.get_or_create_session` + `run_turn` from `app/core/agentic_kernel/companion/turn.py` (same as production companion path).
- Lock **workspace shape**: required files per `tools/inty_v2_repl/AGENTS.md` (`IDENTITY.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `transcript.jsonl`; optional `context.json`, `TOOLS.md`, etc.).
- Define one **fixed scenario** (user script) and one **quality target** (score threshold) so all seeds are comparable.

---

## Phase 1 - Seed templates (`seeds/`)

- Add four directories (minimal viable set):
  - `seeds/baseline/` - neutral SOUL, minimal TOOLS, short or empty `USER.md`.
  - `seeds/empathic/` - SOUL emphasizes validation-before-advice, emotion vocabulary; optional TOOLS hints aligned with kernel tool contracts.
  - `seeds/functional/` - SOUL emphasizes structure and next steps; less affective language.
  - `seeds/teammate_on/` - same as one of the above but **prefilled `USER.md`** (tastes, boundaries, communication prefs) to model teammate injection.
  - `seeds/teammate_off/` - explicit empty/minimal `USER.md` control for the same base soul (pair with `teammate_on` of matching base if you split).
- Keep **`IDENTITY.md` identical** across seeds unless the experiment explicitly tests persona; document any exception in `README.md`.
- Add **`context.json`** only where needed; prefer one `context_mode` (e.g. `intimate`) for all runs unless testing mode as a variable.

**Exit criteria**: each seed directory copies to a temp path and passes `is_workspace_initialized` / first `run_turn` without kernel changes.

---

## Phase 2 - User script and harness loop (`scripts/`)

- **`fixtures/user_script.jsonl`** (or `.md`): ordered list of user lines for the scenario; same script for every seed run.
- **`scripts/run_trial.py`** (name flexible):
  - Args: `--seed-dir`, `--output-dir`, `--max-turns`, optional `--model` / env for LLM.
  - Steps: copy seed to a fresh workspace under `results/<run_id>/workspace/`; wire `CompanionConfig` (repo-root `config.yaml` + venv as in backend docs); call `run_turn` per script line until script ends or `max-turns`.
  - Persist: copy or symlink final `transcript.jsonl`, optional snapshot of `USER.md` / `SOUL.md` / `MEMORY.md` before and after for evolution demo.
- Optional: **`scripts/run_matrix.py`** loops all `seeds/*` and writes one summary table.

**Exit criteria**: one command produces `results/.../summary.json` with per-seed **turn count to completion** (script exhausted) and paths to transcripts.

---

## Phase 3 - Scorer (`scorer/`)

- Implement **`scorer/score_turn.py`** (or package) that takes:
  - latest assistant reply (and optionally full transcript),
  - returns `score` in `[0, 1]` and `passed` vs configurable threshold.
- Start with **rule-based checks** (keywords, forbidden dismissive phrases, must reflect user emotion label) so runs are cheap and reproducible; optional second mode calling a small LLM **only from experimental code**, not kernel.
- Document **threshold** and rubric in `README.md` so demos do not look arbitrary.

**Exit criteria**: scorer is deterministic for the rule-based mode; JSON summary includes **first turn index** where `passed` is true (primary KPI).

---

## Phase 4 - Metrics and report

- **Primary KPI**: turns until `score >= threshold` (if never, record `null` and flag).
- **Secondary KPIs**: total user script characters; optional count of tool rounds if logged in transcript metadata.
- **`results/`**: gitignored; commit only **example** `summary.json` under `examples/` if you want a fixture without secrets.

**Exit criteria**: a markdown or JSON report compares seeds side-by-side for the same user script.

---

## Phase 5 - Demo packaging

- **CLI demo**: `README.md` section "Quick run" with `PYTHONPATH=.` and venv activation.
- **Optional notebook or static HTML**: reads `summary.json` only; no kernel import in the browser.
- **Narrative**: 2-minute flow - reset workspace, run two seeds, show **turns-to-threshold** difference.

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| LLM variance | fix seed, temperature, model id; repeat runs (e.g. 3x) and report median |
| Memory pipeline delays evolution visibility | tune `INTY_V2_PROTO_*_EVERY_N_TURNS` in env for demo only, or show file diff after N turns |
| Workspace init drift | copy from `seeds/` each run; never mutate templates in place |

---

## Dependency and env

- Reuse repo root **venv** and `config.yaml` per [backend/README.md](/backend/README.md) and [AGENTS.md](/AGENTS.md).
- Add **`requirements.txt`** in this folder only if extra deps are needed (e.g. `python-dotenv`); follow [experimental/AGENTS.md](../AGENTS.md).

---

## Checklist before merge

- [x] No diff in `app/core/agentic_kernel/`
- [x] `seeds/*` runnable with one documented command
- [x] `scorer` + `scripts` produce comparable `summary.json`
- [x] `README.md` updated with run instructions (link this PLAN)
