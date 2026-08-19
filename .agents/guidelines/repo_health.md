# Repository Health & AI Agent Performance Reference

This repository enforces strict code cleanliness, linting, and formatting standards not only for human maintainers, but as an explicit optimization strategy for autonomous AI coding agents (such as Claude Code, GitHub Copilot Workspace, or custom internal SWE agents).

This is backed by empirical research on how codebase health directly affects the operational cost and structural efficiency of LLMs [1].

## Core Research Reference
* **Study:** *Does Code Cleanliness Affect Coding Agents? A Controlled Minimal-Pair Study* (May 2026)

## Key Findings & Engineering Metrics

### 1. Financial Impact: Clean Code = 7–8% Lower Token Costs

* **Finding:** When operating on codebases with low cognitive complexity and no static-analysis violations, agents achieved the exact same task success while consuming **7% to 8% fewer total tokens** (primarily input tokens).
* **Takeaway:** Writing clean code is a direct financial lever. Maintaining a clean repository acts as a persistent discount on our downstream AI inference budget.

### 2. Efficiency Impact: 34% Reduction in Tool-Call Backtracking
* **Finding:** In messy, highly complex, or poorly factored codebases, agents enter "navigational loops"—repeatedly jumping back and forth between files to maintain a functional mental model. In clean repositories, **file revisitations dropped by ~34%**.
* **Takeaway:** High cognitive complexity bloats the agent's context window and slows down execution speed. Well-modularized code ensures the agent establishes context linearly, reducing latency and tool-use overhead.

### 3. Capability vs. Friction
* **Finding:** Code cleanliness **does not change the ultimate task completion (pass) rate** of advanced agents. Frontier models are smart enough to resolve bugs in messy code, but they suffer from intense structural friction to get there.
* **Takeaway:** Messy code doesn't stop the agent from finishing a task, but it drastically increases the execution time, error potential during intermediate steps, and overall project cost.

## Practical Mandate for Contributors

LLMs suffer from the exact same structural friction that human developers do. To ensure this repository remains optimized for automated AI maintenance, we strictly enforce:
1. **Low Cognitive Complexity:** Keep functions short, avoid deep logical nesting, and extract complex conditional trees into named helper functions.
2. **Zero Static Violations:** All CI/CD linting, formatting (Prettier/Black/Biome), and type-checks must pass perfectly before an AI agent is invoked on a branch.
3. **Explicit Naming Conventions:** Ambiguity forces the LLM to waste context querying surrounding files to infer variable intent. 

[1] Does Code Cleanliness Affect Coding Agents? A Controlled Minimal-Pair Study: https://arxiv.org/abs/2605.20049
