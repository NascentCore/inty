# LLM Messages Stack Exploration

> Generated entirely by the Cursor agent as a throwaway demo for probing LLM message-stack behavior.

This experiment calls `LlmClient(...).async_llm_client.chat_completion(...)` with hand-built OpenAI-style message arrays to test whether providers honor `system` messages in different positions:

- leading prefix system slices
- post-transcript tail system slices
- mid-transcript system slices
- push/pop stack mutation

The result is observational evidence only. It does not change companion harness prompt assembly.

## Run Offline

```bash
PYTHONPATH=. uv run python experimental/llm_messages_stack_exploration/stack_probe.py --print-stack-only --experiment all
```

This applies YAML steps and prints the messages that would be sent. It does not import config or call an LLM.

## Run Live

```bash
export INTY_CONFIG_YAML=devops/config.yaml.local
export OPENROUTER_API_KEY=sk-...
PYTHONPATH=. uv run python experimental/llm_messages_stack_exploration/stack_probe.py --experiment all
```

Live runs write JSON artifacts under `experimental/llm_messages_stack_exploration/runs/`.

## Interpretation

If mid-transcript and push/pop probes pass, the provider likely respects later or interleaved `system` slices strongly enough to support future prompt-projection experiments. If they fail or behave inconsistently, keep durable doctrine and persona in the stable prefix and reserve post-transcript slices for short-lived runtime context.
