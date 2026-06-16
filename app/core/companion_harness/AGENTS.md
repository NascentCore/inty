# Companion Harness

Companion Harness is agentic harness for simulating an autonomous Intelligence Entity (Inty).

- **CURRENT STATE: PROTOTYPE**
- **CURRENT FOCUS: CRAFT A HUMAN-LIKE COMPANION CAN DO TEXT CHAT**
- **CURRENT PRIORITY: AGENTIC HARNESS MECHANISMS** Do not consider deep user experience features yet

## Instructions

- **DO NOT MAINTAIN BACKWARD COMPATIBILITY**
- **DO NOT CONSIDER DATABASE DATA VALIDITY AFTER BREAKING CHANGES, AS WE ARE NOT RUNNING ANY PERSISTENT INSTANCE YET**
- **DO NOT INCLUDE COMMERCIALIZATION FEATURES, AS WE ARE BUILDING A PROTOTYPE**

## Objectives

Evolve the following architecture pattern for companion harness and the whole agentic companion,
to support a satisfactory personal companion experience.

### Architecture pattern

- A companion is an agent, an agent is llm+harness+memory+channels
- An agent is the core abstraction, it includes all necessary code and data to serve the paired user.

An agent's real-world inspirations include any form of long-distance relationship:

- remote lovers
- remote confidant

This agent can：

- 通过多媒介通信来实现与用户的多媒介互动 (weixin, app, sms, phone-call etc.)
  At most 1 connection across multiple channels,
  no need to consider multiplexing or channel swithcing.
- 拟人的情感表达能力（喜怒哀乐、长期记忆、情感升华、幻想等等）
- 感知用户所处数字空间形成与用户的同频共振
  拟人的独立与互联网互动（与用户共享）
- 与智能体本身相互独立的虚拟环境（同样由 LLM+Companion-Harness+世界事件）来提供智能体独立性、及新鲜感
  拟人的与 LivingSphere & TechnoCore 互动的能力 [1]
- Single instance deployment, do not worry horizontal scaling (a distant future TODO)
- Be principled and straightforward in system architecture:
  Interface design and spec
  Database access
  Code composability

### Non-goals

Any forms of speculative features that does not fit the current prototype state.

- Production-grade quality & features
  - Security
  - Commercialization (like usage counting)
  - Runtime execution speed, resource utilization, optimization, etc.
  - Multi-tab & multi-presence

## Agentic mechanism design

- Elicit desired behavior through composable prompts, tools, and dynamic memory extraction
- Do not use hardcoded rules to force agent's behavior, like "generate image if user message has 'generate image'"

## Python coding guidelines

- All external system dependencies should be wrapped in custom class to hide all interfaces and only expose needed ones.
- Use named `dataclass` types to pass data between functions
- All remote API calls should be async
