# Memory

## 2026-05-10

### Experience profiles: one authoritative frozenset, derive subsets

When companion `context_mode` / experience profiles use StrEnum, derive overlapping subsets with set algebra on the authoritative frozenset (e.g. `_PRIVATE_MEMORY_PROFILE_IDS - {ExperienceContextMode.INTIMATE}` for shared clause bodies) instead of maintaining a second parallel frozenset that can drift.

### Session state naming paradigm (Binding / Corpus / Sidecar)

Full spec: [/.agents/maintenance/AGENTIC_KERNEL_ARCH_ENHANCEMENT.md](/.agents/maintenance/AGENTIC_KERNEL_ARCH_ENHANCEMENT.md). Summary: replace overloaded `workspace` with **`SessionBinding`** + **`SessionCorpus`** (`corpus_rel_key`) + **`DurableSidecar`** / **`ProcessPrivate`** by durability contract; **no `data_mount` in the core paradigm** when corpus authority is repository/DB and REPL is not a companion runtime.

### Pytest looked stuck: LangSmith plugin + `MagicMock` in dual-LLM message parsing

`pytest -m "not noci" tests/` appeared to hang after `test_tool_bg_routing` (often with unrelated log lines on the same line due to `-s`). **Cause**: [`parse_dual_llm_chat_envelope_from_message`](/app/core/agentic_kernel/companion/significance_perception.py) walks `reasoning` / `reasoning_details` via `_string_candidates_from_value`; `unittest.mock.MagicMock` exposes a callable fake `model_dump`, causing pathological recursion—worse once **`langsmith` pytest plugin** is loaded (typical venv: `langsmith-0.*` registers `langsmith_plugin`). **Fix**: at the start of `_string_candidates_from_value`, treat `unittest.mock.Base` instances as non-sources (`return []`). Repro guard: run `test_significance_perception_envelope.py` then `test_tool_bg_routing.py` before the fix; `-p no:langsmith_plugin` also masks it but drops LangSmith’s pytest hooks.
