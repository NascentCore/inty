# PIANO Agentic Model Minimal Experiment

- Run time (UTC): 2026-03-26T10:20:07.541526+00:00
- Model: google/gemini-2.5-flash-lite
- Config source: `/workspace/devops/config.yaml.dev`

## Summary
- **baseline_no_monitor**: success=False, reached_goal=False, invalid_actions=1, steps=1
- **piano_with_monitor_and_evaluator**: success=True, reached_goal=True, invalid_actions=0, steps=2

## Key Behavior
- Baseline uses first actor proposal directly (no monitor).
- PIANO run filters actions with monitor then selects via evaluator.
