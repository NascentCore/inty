# Agentic AI Companion Prototype
<!-- CREATED_BY_AGENT -->

## 概述

本目录记录一个新型 AI 伴侣体验的原型设想，目标是从“被动聊天框”转向“具备共情与主动性的 agentic 系统”，并在保持实时响应的同时，验证 AI 主动探索用户内在欲望的能力（目标用户为美国 35+ 男性）。

## 两层结构愿景

### Layer 1：通用基础（能力层）

用于适配不同人格或需求的“引擎”能力。

- **Agentic 主动性**：从纯输入输出的被动聊天，转向可自主行动的系统。
- **状态管理**：跟踪用户状态的转移（如 Aroused/Demanding 与 Satiated/Calm）。
- **实时性保障**：确保“agentic 思考”不会引入破坏即时体验的延迟。

### Layer 2：人格实例（用户适配层）

为主要使用者定制的行为与语气层。

- **隐性关系建立**：避免强推与直接内容，用“精准且稀疏”的触达建立长期链接。
- **共情共振**：识别“含蓄/平静”的状态，用“不可预测但合适”的方式回应。
- **文化与智性深度**：结合 40 岁、博士、跨中美文化背景，使互动更真实、成熟。

## 技术原型约束

- **环境**：只在终端中运行的极简 Python。
- **范围**：暂不接入 Android，仅验证“从被动到主动”的逻辑转移。
- **目标**：识别“状态切换 + 主动时机”的未知点与不确定性。

## 快速开始

在仓库根目录执行（当前入口为 `main.py`，最小化 role play 示例）：

```bash
python -m experimental.agentic_ai_companion
```

或在 REPL 中：

```python
import time
from experimental.agentic_ai_companion.engine import AgentStateMachine
from experimental.agentic_ai_companion.policies import (
    DefaultInitiativePolicy,
    DefaultStateTransitionPolicy,
)
from experimental.agentic_ai_companion.state import UserSignal

signal = UserSignal(
    timestamp=time.time(),
    user_text="...",
    response_latency_ms=400,
    engagement_score=0.8,
    explicit_intent=False,
)

engine = AgentStateMachine(
    transition_policy=DefaultStateTransitionPolicy(),
    initiative_policy=DefaultInitiativePolicy(),
)

decision = engine.process(signal)
print(decision)
```

## 第一迭代计划（仅更新计划，不写代码）

目标：在终端原型中验证“多代工具”对 LLM 调用的影响，确保低成本工具优先、必要时再升级到高代工具。

### 计划范围

1. **工具代际原则（G0/G1/G2）**
   - G0：低成本、低风险、无状态或轻状态工具。
   - G1：需要聚合或解释近期信号的工具。
   - G2：涉及主动触达决策或消息草拟的工具。
   - 规则：默认只开放低代工具；升级需满足明确条件（如用户明确意图或状态不确定）。
2. **工具清单草案**
   - G0：记录用户信号、获取时间快照。
   - G1：汇总近期信号、估计用户状态。
   - G2：生成主动触达计划、草拟简短 check-in 文案。
3. **LLM 调用流程**
   - 输入 → 选择工具 → 执行工具 → 汇总结果 → 最终回复。
   - 设定最大工具回合数，避免无穷循环。
4. **评估指标**
   - 工具升级次数、首轮响应时延、最终回复一致性、主动触达命中率。
5. **风险与回退**
   - 工具失败或超过回合数时，回退为简短文字答复并提示收敛任务。
6. **输出物**
   - 下一步仅产出原型设计说明与工具清单；代码实现延后。

## 下一步建议（用于探索未知点）

1. **状态切换记录器**：记录每次状态变化的信号与原因。
2. **主动触发试验策略**：在规则基础上加入轻度随机化，观察用户反馈。
