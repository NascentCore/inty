# Brain-inspired memory summarizer — run results

This file summarizes a **local, reproducible** benchmark run (regex extraction, no external LLM). Raw machine-readable output is in the JSON files next to this document.

## How to reproduce

```bash
cd research/brain_inspired_memory_summarizer
python3 main.py run
```

Outputs:

| File | Contents |
|------|----------|
| [experiment_results.json](experiment_results.json) | Aggregate metrics only |
| [experiment_full.json](experiment_full.json) | Metrics + per-turn routing/extraction trace + per-question QA breakdown |

Optional paths: `python3 main.py run --out /tmp/metrics.json --full-out /tmp/full.json`.

## Settings (this run)

- **Window size** (baseline small + layered working-memory analogue): 2 user lines
- **Extraction mode**: `regex` (deterministic slot + episodic fallback)
- **Dataset**: single episode `ep-001` (synthetic dialogue with early facts, overwrite, long distractor tail)

## Aggregate metrics

| Arm | Accuracy | Avg context chars / question |
|-----|----------|------------------------------|
| Baseline small window | 0% (0/6) | 26 |
| Baseline large window | 100% (6/6) | 144 |
| Layered memory | 100% (6/6) | 39 |

Derived:

- **Accuracy gain vs small**: +100% (layered 1.0 − small 0.0)
- **Context reduction vs large**: ~72.9% fewer characters than full dialogue per question
- **Layered long-term slot count** after ingest: 6 keys (`preferred_name`, `city`, `pet`, `rest_day`, `coffee_preference`, `boundary`)

## What the extraction trace shows

See `experiment_full.json` → `extraction_traces_by_episode` → `ep-001` for each user turn:

1. **`routed_categories`**: which memory subsystems run (rule-based mapping from dialogue text), e.g. `semantic` vs `episodic` vs `self_schema`, including **both** when a line matches multiple cues (e.g. “今天搬家…” → episodic + semantic).
2. **`semantic_candidates` / `self_schema_candidates`**: independent regex extractions for durable slots vs boundaries.
3. **`episodic_events`**: gist + salience when the turn is routed to episodic (regex fallback: one trace per qualifying turn).
4. **`semantic_long_term_after_turn`**: the layered agent’s consolidated semantic store after salience gating (confidence floor 0.75) and cross-slot boundary checks.

## Per-question QA (memory “recall” under short context)

From `qa_per_question`: with only the last **two** user lines visible, the **small baseline** answers **不知道** for every slot (early facts have scrolled out). The **layered** agent answers from long-term semantic memory, so all six match the **expected** strings while using far less context than the large-window baseline.

## Caveats

- Results are for this **fixed synthetic script** and **regex** backends; they illustrate routing + layered retention, not production chat quality.
- With `OPENROUTER_API_KEY` / `OPENAI_API_KEY`, slot extraction can switch to LLM-backed passes; routing remains rule-based (`utterance_memory_categories`).
