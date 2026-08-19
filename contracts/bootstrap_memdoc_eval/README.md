# Bootstrap MemDoc golden chat recall eval

L1 report-only harness comparing `awake_write` vs `dreaming_only_fast` on **chat recall** after bootstrap. Refs [#3606](https://github.com/NascentCore/inty/issues/3606).

## Matrix

- **1 scenario** × **2 policies** = **2 cells**
- Scenario: `recall_baseline` in [`scenarios.yaml`](scenarios.yaml)
- Config: `devops/config.yaml.bootstrap_memdoc_eval.yaml` — restart Ops once per policy group (2 restarts total)

## Flow

### awake_write

```
bootstrap → batch recall (POST_DOCS) → post_recall
```

### dreaming_only_fast

```
pre agent:  bootstrap → batch recall (PRE_DREAM, diagnostic)
post agent: bootstrap → force dream (no recall chat) → batch recall (POST_DREAM) → post_recall
```

Dual-agent for dreaming: recall probes are chat turns; dreaming requires transcript ending at bootstrap boundary (`assert_dreaming_transcript_boundary_unchanged`).

## Run

Dry-run plan:

```bash
./.cursor/skills/scripts/run_bootstrap_memdoc_eval_matrix.sh
```

Live matrix (Ops required):

```bash
RUN_LIVE=1 ./.cursor/skills/scripts/run_bootstrap_memdoc_eval_matrix.sh tmp/bootstrap-memdoc-eval-live.json
```

Driver: [`.cursor/skills/scripts/run_bootstrap_memdoc_eval.py`](../../.cursor/skills/scripts/run_bootstrap_memdoc_eval.py)

## Scoring

Deterministic substring match on assistant visible reply for `user_address`, `assistant_name`, `relationship_framing`.

**Policy decision uses `post_recall` only** (dreaming `post_recall` vs awake `post_recall`). Dreaming `pre_recall` is diagnostic.

## Results summary template

| Policy | Phase | Score |
|--------|-------|-------|
| awake_write | after bootstrap | `post_recall` |
| dreaming_only_fast | after bootstrap | `pre_recall` (diagnostic) |
| dreaming_only_fast | after dream | `post_recall` |

Record outcomes on issue #3606; exit code always 0 (does not gate CI).

Generated entirely by Cursor agent for Bootstrap MemDoc L1 eval (#3606).
