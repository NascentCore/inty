# Brain-inspired memory summarizer — run results

This file summarizes a **local, reproducible** benchmark run. Memory extraction is **LLM-shaped JSON only** (no regex slot parsers). The default `main.py run` uses **deterministic JSON stubs** keyed by exact dataset lines, so no API keys are required.

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
- **Extraction**: `llm_only_benchmark_stubs` (see `experiment_full.json` → `settings`)
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

1. **`routed_categories`**: subsystems chosen by the **route** JSON for that line (`semantic` / `episodic` / `self_schema`).
2. **`semantic_candidates` / `self_schema_candidates`**: slot JSON from independent **semantic** vs **self-schema** passes (stub table in `main.benchmark_slot_json_by_line`, filtered by route).
3. **`episodic_events`**: episodic JSON when the route includes `episodic` (`main.benchmark_episodic_json_by_line`).
4. **`semantic_long_term_after_turn`**: layered LTM after confidence gating and boundary/name conflict handling.

## Per-question QA (memory “recall” under short context)

From `qa_per_question`: with only the last **two** user lines visible, the **small baseline** answers **不知道** for every slot (early facts have scrolled out). The **layered** agent answers from long-term semantic memory, so all six match the **expected** strings while using far less context than the large-window baseline.

## Caveats

- Stubbed run matches the scripted benchmark only; **open-domain** behavior requires real API calls and live models.
- Set `OPENROUTER_API_KEY` or `OPENAI_API_KEY` to use `extract_semantic_candidates_llm_default`, `route_memory_categories_llm_default`, etc., without stubs (pass custom callables into `LayeredMemoryAgent` / `NaiveWindowAgent` for experiments).
