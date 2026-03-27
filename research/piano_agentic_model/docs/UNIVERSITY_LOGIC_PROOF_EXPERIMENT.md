# PIANO Agentic Model Experiment

- Run time (UTC): 2026-03-26T12:04:25.503217+00:00
- Model: google/gemini-2.5-flash-lite
- Config source: `/workspace/devops/config.yaml.dev`
- Task: `logic_proof_university`
- Task description: University-level first-order logic proof: from forall x (H(x)->M(x)), forall x (M(x)->L(x)), exists x H(x), prove exists x L(x). The task requires witness introduction, universal instantiation, two implication eliminations, and existential introduction.
- Required checkpoints: ['WitnessChosen', 'HaDerived', 'MaDerived', 'LaDerived', 'Conclusion']

## Summary
- **baseline_no_monitor**: success=False, reached_goal=False, invalid_actions=1, steps=1
- **piano_with_monitor_and_evaluator**: success=True, reached_goal=True, invalid_actions=0, steps=7

## Key Behavior
- Baseline uses first actor proposal directly (no monitor).
- PIANO run filters actions with monitor then selects via evaluator.
