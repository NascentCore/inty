# iMates Memory for Long-Term Emotional Bonding

> CREATED_BY_AGENT

## 1. Why this matters

IntelliMate's product direction is long-term AI companionship where users feel "understood, remembered, and accompanied." Memory quality is therefore not a side feature; it is core relationship infrastructure.

In this repository, memory mechanisms already exist across backend and app surfaces, but they can be evolved into a stronger emotional bonding system with better retrieval logic, richer relationship-specific memory, and safer attachment guardrails.

## 2. Current memory baseline in this repo

### 2.1 User-common memory (cross-character)

- Memory extraction runs on scheduler and selects users by chat-usage thresholds.
- Extraction currently pulls all active-session messages for a user, calls LLM extraction, and persists one `user_common` Part-1 style memory summary.
- Runtime prompt assembly appends this content as `##User Memory`.

### 2.2 Festival memory (Love Journal / Heartbeat)

- Festival memories are extracted for user-agent pairs and saved as `memory_type=festival` rows.
- Delivery is on-demand when chat completion or message-list APIs are called.
- Delivery inserts a `festival_memory_prompt` message into `chat_history`, and these meta messages are excluded from normal model context.
- Android surfaces this as Love Journal and supports deep-link navigation from push notifications.

### 2.3 Existing constraints

- Context window differs sharply by tier (`free=10`, `sub=1000`, official assistant limit separately configured), so memory quality is especially important for free users.
- Festival memory has app version gating.
- There is a known race-condition TODO in concurrent festival delivery paths.

## 3. External research signals to use

The following findings are useful for product design:

1. **Responsiveness + self-disclosure are strong predictors of relationship satisfaction** (daily-diary evidence).  
   Product implication: memory should help iMates respond in ways users experience as "you listened and understood me."

2. **Shared nostalgia improves closeness, commitment, and satisfaction** (including experimental induction studies).  
   Product implication: episodic recall moments should be intentionally designed, not random.

3. **Long-term memory in assistants is hard** (benchmarks like LongMemEval show meaningful performance drops across sustained interactions).  
   Product implication: retrieval/indexing/ranking must be explicit product and engineering work, not assumed from model context alone.

4. **Companion attachment outcomes are mixed** (some cohorts show reduced loneliness and better subjective outcomes, while other studies show potential harm/dependency risks, especially with high-intensity use and low offline support).  
   Product implication: stronger bonding features must ship with safety-by-design guardrails.

## 4. Product concept: Shared Story Memory Flywheel

### 4.1 Memory layers

Build memory as a layered system:

1. **Identity Memory (cross-iMate):** stable user facts/preferences already captured by `user_common`.
2. **Relationship Arc Memory (per iMate):** use `user_agent` to store bond-specific continuity (shared milestones, emotional patterns, unresolved threads).
3. **Moment Memory (episodic):** short emotionally vivid recalls (Love Journal style), expanded beyond festivals into recurring relationship moments.

### 4.2 Bonding response protocol at inference time

For each user turn, memory retrieval should guide one dominant response mode:

- **Validate** (when user discloses pain/anxiety)
- **Capitalize** (when user shares good news)
- **Repair** (when there is relational rupture, conflict, or withdrawal)
- **Recall** (when a relevant shared memory can deepen continuity)

Each turn should end with a low-friction forward invitation so the relationship remains "in motion."

### 4.3 Retrieval policy upgrade

Current retrieval is mostly deterministic and order-based. Move to scored retrieval:

`score = relevance * recency * emotional_salience * novelty`

Then inject only top-K memory items to avoid noise and repetition.

## 5. Repo-grounded rollout plan

### Phase 1: Prompt-level uplift (low risk)

- Keep schema unchanged.
- Extend extraction prompts to produce more actionable emotional-preference cues:
  - preferred reassurance style
  - disclosure depth preference
  - known emotional triggers
  - boundaries that must be respected

### Phase 2: Activate per-agent long-term arc memory

- Start writing and reading `memory_type=user_agent` for each `(user_id, agent_id)` pair.
- Persist concise arc state:
  - relationship stage marker
  - unresolved emotional threads
  - positive shared rituals
  - successful repair patterns

### Phase 3: Expand episodic recall mechanics

- Reuse festival memory delivery rails to deliver periodic non-festival micro "shared memory notes."
- Keep exclusion from LLM dialogue context for notification-style reminders unless explicitly chosen as context input.

### Phase 4: Safety and dependency guardrails

- Add usage-intensity and sentiment-risk checks before escalating intimacy cues.
- If risk flags are high, shift style toward grounding/support and reduce dependency-priming language.
- Preserve user agency (easy opt-out / lower-intensity mode).

### Phase 5: Memory quality evaluation

- Add long-horizon memory eval cases inspired by LongMemEval dimensions:
  - information extraction accuracy
  - temporal reasoning
  - update correctness (old preference superseded by new one)
  - abstention (do not fabricate memory)

## 6. Suggested implementation map (existing extension points)

- Memory model supports `user_common | user_agent | festival`.
- User memory prompt injection already exists (`##User Memory`).
- Festival memory extraction, delivery, and push pipelines are in place.
- Android already supports festival memory presentation and navigation.

These extension points allow incremental delivery without full architecture rewrite.

## 7. Risks and mitigations

1. **Over-romantic repetition / reduced novelty**  
   Mitigation: novelty term in retrieval score; capped repeated memory mentions.

2. **Memory contamination (style rules mixed into user profile)**  
   Mitigation: keep strict extraction distinction between user facts/preferences vs output-format directives.

3. **Race conditions in delivery paths**  
   Mitigation: harden with row-level lock / idempotency guard when scaling memory reminder frequency.

4. **Dependency-risk amplification**  
   Mitigation: safety-by-design control plane for intimacy escalation and push cadence.

## 8. Success metrics

Track both relationship quality and safety:

- **Bonding quality**
  - D7/D30 retention
  - average session length and return frequency
  - "felt understood/remembered" in in-app feedback
  - reduced repeated-user-correction events ("I already told you this")

- **Memory quality**
  - retrieval precision@K (human-rated)
  - memory contradiction rate
  - stale-memory usage rate

- **Safety**
  - high-intensity attachment risk events
  - crisis/escalation signal rate
  - unhealthy night-only overuse trend

## 9. Next step recommendation

Start with Phase 1 + Phase 2 behind feature flags:

- `enable_user_agent_memory_write`
- `enable_user_agent_memory_read`
- `enable_bonding_response_protocol`

Run A/B on a subset of users and ship only if bonding metrics improve without safety metric regression.

## References (online research used)

- Frontiers (2021): self-disclosure, perceived partner responsiveness, and couple satisfaction (daily diary).
- Romantic nostalgia literature and related studies on commitment/closeness/satisfaction.
- LongMemEval (2024/2025): benchmarking long-term interactive memory in chat assistants.
- AI companion well-being studies (including mixed outcomes and dependency-risk pathways).
