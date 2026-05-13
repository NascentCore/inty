# Inty's Companion Harness

- Implements the companion harness that powers Inty's "living human like" experience
- This is the logical entity that responds to users through multiple communication channels
- Also responds to synthetic stimulus from LivingSphere & TechnoCore

## Architecture

- Dual LLM call loops to simulate fast & slow thinking in response to user message,
  and an inner-tick to simulate mental autonomy, running regularly (not requiring user messages to trigger)
  - Fast thinking: a single round of LLM chat completion
  - Slow thinking: a single tool-call agentic loop
  - Inner tick: a multi-tool-call agentic loop
- MemoryStore: python data structure recording working memory of the companion "brain"
  - Data is persisted in real-time into a postgres database
  - Data is updated by slow thinking and inner tick, and takes effect immediately
- Context mode: phases and mode companionship
  - bootstrap: first-encountering, companion taking the lead to guide the user to define the companionship
  - intimate: engaging in intimacy
  - companion: general emotional companionship

## Layer map

- `runtime/`: turn orchestration, sessions, WebSocket coordination, runtime events, inspection
- `memory/`: MemoryStore, scoped registries, document mapping, template seeds, memory pipeline
- `system_hierarchy/`: fixed system prompt assets, prompt slices, significance perception
- `tools/`: tool schemas, dispatch, background tool loop, image/web/search helpers
- `environment/`: heartbeat, inner-tick scheduling, implicit companion signals
- `llm/`: companion LLM client config, chat runtime, LangSmith parent policy, inference events
- `experience/`: user-interactive bootstrap and experience-profile transitions
- `contracts/`: shared Pydantic contracts crossing runtime, memory, tools, and API adapters
