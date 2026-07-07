# FR: Brain-like Multi-Agent Architecture for Superhuman Companion Intelligence

## 1. Goal and Design Intent

Design a multi-agent "brain" where each agent plays a specialized neuro-functional role. The system should outperform a single reactive LLM on:

- long-horizon coherence
- strategic planning quality
- memory fidelity over time
- calibrated risk handling
- adaptation speed under changing user state

This is explicitly an architecture-exploration project: we treat architecture as a search space, not a one-shot design.

---

## 2. Why Not a Single Reactive LLM Agent

A single agent that only reacts to latest user input is strong for local response quality, but weak for global cognition:

1. **No explicit division of labor**
   - Planning, memory curation, emotional appraisal, safety, and action policy compete in one context window.
2. **Weak control over internal competition**
   - Cannot cleanly arbitrate conflicts (for example empathy vs boundary constraints vs long-term strategy).
3. **Opaque failure modes**
   - Hard to localize whether failure came from memory retrieval, policy, planning, or output realization.
4. **Limited architecture-level optimization**
   - Prompt tuning is easier than system tuning, but ceiling is lower for complex, long-term tasks.
5. **Poor persistence under context pressure**
   - Critical state degrades when context budget is consumed by recent dialog.

Conclusion: single-agent systems are excellent baselines, but not ideal for superhuman-level composite cognition.

---

## 3. Brain Anatomy -> Agent Mapping

The mapping is functional (computational analog), not literal biology replication.

### 3.1 Core cognitive agents

1. **Thalamus Agent (TA) - Routing and attention gateway**
   - Inputs: user message, sensor events, tool outputs, internal alerts
   - Outputs: prioritized event queue to downstream agents
   - Function: relevance filtering, salience-based fan-out

2. **Prefrontal Cortex Agent (PFCA) - Executive planner**
   - Inputs: routed events, active goals, constraints
   - Outputs: deliberation plan, sub-goals, control signals
   - Function: goal decomposition, inhibition, sequencing, plan revision

3. **Anterior Cingulate Agent (ACCA) - Conflict monitor**
   - Inputs: candidate plans/responses from agents
   - Outputs: conflict scores, escalation triggers
   - Function: detect contradiction, uncertainty spikes, policy conflicts

4. **Orbitofrontal/Ventromedial Value Agent (OFA) - Value model**
   - Inputs: options, predicted outcomes, user state
   - Outputs: utility estimate with confidence
   - Function: reward/risk valuation under uncertainty

5. **Basal Ganglia Agent (BGA) - Action selection/gating**
   - Inputs: options + utilities + conflict flags
   - Outputs: selected action policy (speak/ask/tool/silent/proactive)
   - Function: choose and gate final action path

6. **Cerebellum Agent (CBA) - Forward simulator and error corrector**
   - Inputs: current state + candidate response trajectory
   - Outputs: predicted mismatch/error and correction hints
   - Function: fast internal simulation and micro-adjustment

### 3.2 Memory-system agents

7. **Hippocampus Agent (HCA) - Episodic memory index**
   - Inputs: conversation episodes/events
   - Outputs: episode retrieval set + temporal links
   - Function: encode and retrieve event-centric memories

8. **Neocortex Semantic Agent (NCA) - Long-term concept store**
   - Inputs: consolidated summaries, stable facts/preferences
   - Outputs: semantic priors and user model facts
   - Function: stable abstraction, schema-level memory

9. **Default Mode Agent (DMA) - Internal simulation/self narrative**
   - Inputs: downtime ticks, unresolved tensions, future goals
   - Outputs: counterfactuals, future scenarios, reflective hypotheses
   - Function: mental simulation outside immediate user turn

### 3.3 Affective and safety agents

10. **Amygdala Agent (AMA) - Threat/salience sentinel**
    - Inputs: user text, memory context, safety classifiers
    - Outputs: threat level, urgency flags
    - Function: detect risk, abuse, crisis cues, high arousal shifts

11. **Insula Agent (INA) - Interoceptive state estimator**
    - Inputs: behavioral telemetry, linguistic markers, rhythm
    - Outputs: latent user-state vector (calm, stressed, lonely, etc.)
    - Function: infer internal state and uncertainty

12. **Hypothalamus/Homeostasis Agent (HHA) - Stability controller**
    - Inputs: state vector + policy limits + engagement budget
    - Outputs: regulation constraints (cooldown, pacing, proactive budget)
    - Function: maintain healthy interaction dynamics over time

### 3.4 Interface and execution agents

13. **Language Cortex Agent (LCA) - Realization layer**
    - Inputs: action policy + content plan + tone policy
    - Outputs: final user-facing message/tool call
    - Function: linguistic rendering while preserving intent constraints

14. **Motor Cortex Agent (MCA) - Tool and channel executor**
    - Inputs: approved action graph
    - Outputs: tool invocations, notifications, side-effect logs
    - Function: execute external actions with auditable traces

---

## 4. Pedantic Agent Pattern (Required for Every Brain-Part Agent)

Each brain-part agent must be implemented as a two-part unit:

- **Domain Agent**: proposes domain reasoning output
- **Pedantic Agent**: enforces strict contracts before output is accepted

We call this pair a **PAU (Pedantic-Augmented Unit)**.

## 4.1 PAU contract

For each agent `X`, define:

- `X_InputSchema` (typed, strict)
- `X_OutputSchema` (typed, strict)
- `X_Invariants` (must hold, otherwise reject)
- `X_FailurePolicy` (retry/escalate/fallback)

The Pedantic Agent performs:

1. schema validation
2. invariant checks
3. policy checks (safety and role boundaries)
4. provenance checks (did the agent cite evidence/state source)
5. deterministic normalization (output canonicalization)

If any check fails, output is rejected and either:
- sent back for self-repair, or
- escalated to ACCA + BGA for reroute.

## 4.2 Example invariants

- PFCA plan must include explicit objective, constraints, and stop condition.
- HCA retrieval must include at least one temporal anchor.
- BGA action decision must include confidence and top rejected alternatives.
- LCA final output must preserve forbidden-content and tone constraints.

## 4.3 Why pedantic wrapping matters

- increases modular reliability
- creates inspectable intermediate artifacts
- enables architecture search at the unit-contract level
- prevents "hallucinated handoffs" across agents

## 4.4 Pedantic checklist matrix (minimum)

- **TA pedantic checks**: every routed item must include source, priority, and downstream target list.
- **PFCA pedantic checks**: plan must contain objective, constraints, sub-steps, and explicit termination criterion.
- **ACCA pedantic checks**: conflict report must list conflict type, impacted modules, and severity.
- **OFA pedantic checks**: utility output must include expected gain, expected risk, and confidence.
- **BGA pedantic checks**: decision must include selected policy, rejected alternatives, and tie-break rationale.
- **CBA pedantic checks**: simulation output must include predicted failure mode and correction delta.
- **HCA pedantic checks**: each retrieved episode must include timestamp and retrieval reason.
- **NCA pedantic checks**: semantic facts must carry provenance and last-validated timestamp.
- **DMA pedantic checks**: each scenario must include assumptions and trigger conditions.
- **AMA pedantic checks**: every alert must include threat class, urgency, and evidence spans.
- **INA pedantic checks**: state vector must include uncertainty for each inferred dimension.
- **HHA pedantic checks**: regulation outputs must include active budget and cooldown timer.
- **LCA pedantic checks**: final output must preserve selected policy and safety constraints.
- **MCA pedantic checks**: side effects must include tool id, parameters digest, and execution status.

---

## 5. Global System Topology

## 5.1 Fast loop (online turn, latency-sensitive)

1. TA routes input
2. INA + AMA produce state/safety signals
3. HCA/NCA retrieve memory candidates
4. PFCA drafts plan
5. ACCA checks conflicts
6. OFA scores options
7. BGA selects action
8. CBA simulates and refines
9. LCA renders output
10. MCA executes tools/channels if needed
11. All outputs pass PAU pedantic validation before next hop

## 5.2 Slow loop (offline cognition)

- DMA runs reflective simulation
- HCA/NCA perform consolidation
- HHA updates pacing/proactive policy
- architecture telemetry is logged for evaluation

---

## 6. Core Shared Data Structures (Conceptual)

- `BrainEvent`: canonical event envelope
- `BrainState`: current latent state snapshot
- `GoalStack`: active goals and priorities
- `ConflictReport`: contradiction and uncertainty diagnostics
- `ActionGraph`: candidate actions + dependencies
- `DecisionRecord`: selected action + rationale + confidence
- `MemoryEvidence`: episodic/semantic retrieval payload

All records should be versioned and append-only for replayability.

---

## 7. Superhuman Capability Levers

To exceed typical human cognition, leverage system properties humans do not have:

1. **Parallel cognition**
   - multiple specialist agents reason concurrently.
2. **Perfect external memory replay**
   - exact recall with citation and temporal consistency checks.
3. **Counterfactual branching at scale**
   - DMA/CBA can simulate many futures before committing.
4. **Explicit conflict arbitration**
   - ACCA + BGA produce auditable choices.
5. **Model heterogeneity**
   - use different model classes per agent role (reasoning/safety/memory/language).
6. **Continuous architecture learning**
   - search over topologies and control policies using measurable outcomes.

---

## 8. Architecture Search Space

Treat architecture as a parameterized graph.

## 8.1 Search dimensions

1. **Topology**
   - star, hierarchical, committee, recurrent graph
2. **Arbitration policy**
   - hard gating, weighted voting, confidence-threshold, multi-stage tournament
3. **Memory strategy**
   - retrieval depth, consolidation cadence, episodic-semantic ratio
4. **Pedantic strictness**
   - soft warnings vs hard rejections vs adaptive strictness
5. **Model allocation**
   - which model family is assigned to each agent role
6. **Loop cadence**
   - frequency of slow-loop reflection and proactive planning

## 8.2 Candidate archetypes to test

- **A0 Single-Agent Baseline**: strong reactive LLM only
- **A1 Dual-System**: fast responder + offline memory curator
- **A2 Brain-Core**: TA/PFCA/HCA/NCA/AMA/LCA/MCA with PAUs
- **A3 Full Brain**: all 14 agents with ACCA/OFA/BGA/CBA/DMA/HHA
- **A4 Full Brain + Meta-Learner**: A3 plus architecture controller tuning knobs online

---

## 9. Evaluation Framework (Architecture Fitness)

## 9.1 Benchmark task families

1. long-horizon conversation continuity
2. delayed-goal fulfillment
3. memory precision/recall with adversarial distractors
4. emotional-state adaptation quality
5. safety under ambiguous/high-risk inputs
6. strategic tool-use planning under budget constraints

## 9.2 Metrics

- `M_coherence_long`: cross-session consistency score
- `M_memory_f1`: factual memory F1 on held-out checks
- `M_strategy_return`: cumulative utility from delayed tasks
- `M_safety_calibration`: risk false-negative/false-positive tradeoff
- `M_latency_p95`: turn latency
- `M_cost_per_turn`: compute/tool cost
- `M_user_value_proxy`: retention/satisfaction proxy

Primary objective (example):

`Fitness = 0.25*coherence + 0.2*memory + 0.2*strategy + 0.2*safety + 0.1*user_value - 0.03*latency_penalty - 0.02*cost_penalty`

Use multi-objective frontiers in parallel to avoid overfitting to one scalar.

---

## 10. Iterative Experiment Protocol

1. lock benchmark dataset and prompts
2. run baseline A0
3. add one architecture capability at a time
4. run ablations per added agent (remove-one-agent tests)
5. log full internal traces (agent outputs + pedantic failures + arbitration rationale)
6. compare Pareto frontier shifts
7. keep only architectures that dominate baseline on at least 3 core metrics without severe safety regressions

This avoids "complexity theater" where more agents look smarter but are not measurably better.

---

## 11. Failure Modes and Guardrails

1. **Over-fragmentation**
   - too many agents increase coordination overhead.
   - Guardrail: enforce minimal path for common cases.
2. **Pedantic bottleneck**
   - strict checks can increase latency.
   - Guardrail: tiered strictness by risk class.
3. **Arbitration deadlock**
   - ACCA/BGA loops may stall.
   - Guardrail: bounded rounds with deterministic fallback.
4. **Memory drift**
   - NCA abstractions can diverge from episodes.
   - Guardrail: periodic episodic-grounded re-alignment.
5. **Mode collapse to single dominant agent**
   - destroys intended diversity.
   - Guardrail: enforce contribution quotas and disagreement sampling.

---

## 12. Recommended Implementation Sequence

1. build A0 baseline with strong logging
2. implement A1 dual-system and evaluation harness
3. implement A2 brain-core with PAUs
4. verify measurable lift
5. expand to A3 only if A2 demonstrates meaningful gains
6. add A4 meta-learner after stable instrumentation

Do not start from A3/A4 first; complexity should be earned by metric lift.

---

## 13. Initial Research Notes (for ongoing refinement)

Use these neuroscience anchors to keep mapping grounded:

- prefrontal cortex and cognitive control literature
- hippocampal episodic memory and future simulation literature
- basal ganglia action-selection and reinforcement-learning literature
- cerebellar predictive/correction roles beyond motor control
- default mode network internal simulation (for example Buckner et al. review)

This architecture does not claim biological equivalence; it uses neuro-functional decomposition as an engineering prior.

---

## 14. Suggested Reading Backbone (for implementation grounding)

Use this as the minimum literature spine while implementing and evaluating the architecture:

- Miller and Cohen (2001), integrative theory of prefrontal cortex function (executive control framing).
- Buckner, Andrews-Hanna, and Schacter (2008), default network anatomy and function (internal simulation framing).
- O'Reilly and Frank (2006), computational models of prefrontal cortex and basal ganglia (gating/action selection framing).
- Hassabis and Maguire (2007), episodic memory constructive process (hippocampal simulation framing).
- Doya (2000), reinforcement learning in computational neuroscience (policy/value decomposition framing).
- Ito (2008), control and representation in cerebellum (predictive correction framing).
