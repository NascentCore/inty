# BRAIN INSPIRED MEMORY SUMMARIZER: EXPERIMENT DESIGN

## Goal

Validate whether a brain-inspired layered-memory agent can:

1. improve memory QA accuracy versus a short-context baseline, and
2. achieve comparable accuracy to a long-context baseline with less context.

## Hypothesis

- H1 (accuracy): `layered_memory` accuracy > `baseline_small_window` accuracy.
- H2 (context efficiency): `layered_memory` average context chars < `baseline_large_window` average context chars.
- H3 (combined): `layered_memory` keeps high accuracy while reducing context size.

## Controlled Setup

- Synthetic deterministic dialogue with:
  - memory facts introduced early,
  - one overwrite event (same key, newer value),
  - long distractor tail so early facts fall out of short window.
- Deterministic QA set over final stable facts.
- **Extraction is LLM-shaped only**: slot, route, and episodic outputs are JSON parsed like real LLM responses. The bundled benchmark uses **fixed JSON stubs** per dataset line (`main.benchmark_*_by_line`) so `main.py run` needs **no API keys** and stays reproducible.
- With `OPENROUTER_API_KEY` / `OPENAI_API_KEY`, `extractor` calls the real API: independent instruction passes for **semantic**, **self-schema**, **episodic**, and **routing** (`route_memory_categories_llm_default`).

## Arms

1. `baseline_small_window`
   - only last N messages visible at answer time; each visible line is passed through the **slot** LLM (stub or API).
2. `baseline_large_window`
   - full dialogue visible; same slot LLM per line.
3. `layered_memory`
   - same short window as arm #1 + salience-gated semantic long-term store;
   - route LLM selects subsystems per turn; episodic buffer + consolidation (salient episodic evidence re-run through semantic slot LLM; repeated `(key,value)` promotes to LTM).

## Metrics

- `accuracy`: correct answers / total questions.
- `avg_context_chars`: average characters sent as context per question.
- Derived:
  - `accuracy_gain_vs_small`
  - `context_reduction_vs_large`

## Success Criteria (prototype)

- `accuracy_gain_vs_small >= 0.30`
- `context_reduction_vs_large >= 0.40`
- `layered_memory_accuracy >= 0.80`

## Execution

- Install live-LLM dependency (optional): `pip install -r research/brain_inspired_memory_summarizer/requirements.txt`
- Run experiment (deterministic stubs, no API):
  - `python3 research/brain_inspired_memory_summarizer/main.py run`
- Run experiment (**real model**, needs `OPENROUTER_API_KEY` or `OPENAI_API_KEY`, optional `INTY_MEMORY_EXTRACTOR_MODEL`):
  - `python3 research/brain_inspired_memory_summarizer/main.py run --live-llm`
  - Writes `experiment_results_live.json` and `experiment_full_live.json` by default (many API calls; non-deterministic).
- Run tests:
  - `python3 -m unittest research/brain_inspired_memory_summarizer/test_main.py -v`
