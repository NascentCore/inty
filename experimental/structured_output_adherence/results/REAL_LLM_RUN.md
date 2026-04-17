# Real LLM run (fixture transcript)

- **When**: 2026-04-17 (agent VM)
- **Provider**: OpenRouter (`https://openrouter.ai/api/v1`)
- **Model**: `openai/gpt-4o-mini`
- **Data**: synthetic fixture only ([fixtures/sample_turns.jsonl](../fixtures/sample_turns.jsonl)), no production DB

## Command

```bash
cd /workspace && source .venv/bin/activate
python experimental/structured_output_adherence/run_experiment.py \
  --fixture experimental/structured_output_adherence/fixtures/sample_turns.jsonl \
  --max-turns-per-chat 4 \
  --model openai/gpt-4o-mini \
  --temperature 0.2 \
  --max-tokens 512 \
  --out-dir experimental/structured_output_adherence/results/real_llm_fixture_run
```

## Summary (`real_llm_fixture_run/summary.json`)

- `n_calls`: 3 (turn indices 0, 1, 2 for a 3-message transcript)
- `adherence_rate`: 1.0 (all three completions passed `ConversationScenario.model_validate_json` after optional unwrap of a single-key `ConversationScenario` wrapper)
- `failure_count`: 0

## Artifacts

- [real_llm_fixture_run/summary.json](real_llm_fixture_run/summary.json)
- [real_llm_fixture_run/turns.jsonl](real_llm_fixture_run/turns.jsonl) (contains `raw_head` previews; no production user text beyond the small fixture)

## Code notes from this run

- OpenRouter needs `base_url`; when only `OPENROUTER_API_KEY` is set, the script defaults `base_url` to `https://openrouter.ai/api/v1`.
- Without listing allowed `emotional_tone` literals in the system prompt, the model sometimes returned values outside the schema (e.g. `empathetic`).
