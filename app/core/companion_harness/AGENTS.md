# Inty's Companion Harness

- Implements the companion harness that powers Inty's "living human like" experience
- This is the logical entity that responds to users through multiple communication channels
- Also respond to sythetic stimulus from LivingSphere & TechnoCore

## Architecture

- Dual LLM call loops to simulate fast & slow thinking in response to user message,
  and an inner-tick to simulate mental autonomy, running regularly (not requiring user messages to trigger)
  - Fast thinking: a single round of LLM chat completion
  - Slow thinking: a single tool-call agentic loop
  - Inner tick: a multi-tool-call agentic loop
- MemoryStore: python data structure recording working memory of the agentic "brain"
  - Data is persisted in real-time into a postgres database
  - Data is updated by slow thinking and inner tick, and takes effect immediately
- Context mode: phases and mode companionship
  - bootstrap: first-encountering, agentic taking the lead to guide the user to define the comapnionship
  - intimate: engaging in intimacy
  - companion: general emotional compaionship
