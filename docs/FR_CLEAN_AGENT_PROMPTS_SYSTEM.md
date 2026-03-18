# FR_CLEAN_AGENT_PROMPTS_SYSTEM

## Goal

Add a review-only clean agent prompts system that:

1. Matches current `app/core/agent/agent.py` prompt + official assistant tool-loop behavior.
2. Avoids DB access inside the agent tool loop.
3. Uses dependency passing and structured types at calling boundaries.
4. Does **not** change current production behavior until explicit integration.

## Current system summary (existing behavior)

- Prompt assembly today is in `Agent.build_system_messages*`:
  - main prompt (effective main prompt resolution)
  - character context (`personality`, `scenario`, `message_example`)
  - mode prompt + output format prompt selection
  - style prompt / user profile / user-time context / christmas temporal prompts
  - official assistant rename + tool usage guidance
- Official assistant tool loop resolves tool calls in rounds:
  - `save_user_mbti_type`
  - `read_user_manual`
  - `read_change_logs`
- Existing `save_user_mbti_type` implementation writes DB in loop.
- Existing service call chain largely passes `dict` payloads (`agent_data`).

## New review-only clean implementation

### New files

- `app/core/agent/clean_prompt_system.py`
- `app/services/agent_service_clean.py`

### What is cleaned

- Prompt assembly APIs now use typed models:
  - `AgentPromptContext`
  - `ChatSettingsSnapshot`
  - `UserTimeContextSnapshot`
  - `PromptBuildInput`
- Official assistant tool-loop APIs now use typed models:
  - `OpenAIChatMessageSnapshot`
  - `ChatCompletionSnapshot`
  - `OfficialAssistantToolLoopInput/Output`
- Tool-loop dependencies are explicit and injected:
  - `PromptAssemblyDeps`
  - `OfficialAssistantToolDeps`
- MBTI persistence becomes side-effect intent emission:
  - `SaveUserMbtiSideEffect`
  - loop returns side effects for caller-owned persistence layer
  - no direct DB call in loop

### Compatibility / parity intent

The clean module keeps:

- same prompt order and condition branches
- same official assistant branching behavior
- same MBTI argument validation semantics
- same tool loop max-round behavior and injected system-message insertion logic

## Integration plan (later, after review)

1. Replace dict-based `agent_data` fetch path with `get_agent_for_chat_structured`.
2. Convert current chat loop to call clean prompt assembly and tool-loop module.
3. Wire side-effect persistence at orchestration boundary (outside loop).
4. Keep old path behind a temporary fallback switch until parity verification is complete.
