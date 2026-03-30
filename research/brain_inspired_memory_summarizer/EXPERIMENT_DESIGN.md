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
- Default experiment: no external LLM calls; per-memory-type extraction uses regex backends so runs are reproducible.
- With API keys, `extractor` can run **independent** LLM instruction passes per type (semantic vs self-schema vs episodic); dialogue→subsystem routing stays **rule-based** (`utterance_memory_categories`), not LLM role-play.

## Arms

1. `baseline_small_window`
   - only last N messages visible at answer time.
2. `baseline_large_window`
   - full dialogue visible at answer time.
3. `layered_memory`
   - same short window as arm #1 + salience-gated semantic long-term store;
   - optional episodic buffer + consolidation (repeated salient episodic evidence can promote semantic slots).

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

- Run experiment:
  - `python3 research/brain_inspired_memory_summarizer/main.py run`
- Run tests:
  - `python3 -m unittest research/brain_inspired_memory_summarizer/test_main.py -v`
