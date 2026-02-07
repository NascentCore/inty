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

## Python 类结构草案（Layer 1：状态机）
下面是仅包含核心逻辑的最小类结构，用于验证 Aroused/Satiated 状态切换与主动触发的时机控制。

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol
import time


class UserState(Enum):
    AROUSED = "aroused"
    SATIATED = "satiated"


@dataclass(frozen=True)
class UserSignal:
    timestamp: float
    user_text: str
    response_latency_ms: int
    engagement_score: float  # 0.0 - 1.0
    explicit_intent: bool


@dataclass(frozen=True)
class TransitionContext:
    current_state: UserState
    last_state_change_ts: float
    last_initiative_ts: float


class StateTransitionPolicy(Protocol):
    def next_state(self, signal: UserSignal, ctx: TransitionContext) -> UserState:
        ...


class InitiativePolicy(Protocol):
    def should_initiate(self, signal: UserSignal, ctx: TransitionContext) -> bool:
        ...


@dataclass
class DefaultStateTransitionPolicy:
    aroused_threshold: float = 0.7
    satiated_threshold: float = 0.3
    min_state_duration_sec: int = 300

    def next_state(self, signal: UserSignal, ctx: TransitionContext) -> UserState:
        now = signal.timestamp
        if now - ctx.last_state_change_ts < self.min_state_duration_sec:
            return ctx.current_state

        if signal.engagement_score >= self.aroused_threshold or signal.explicit_intent:
            return UserState.AROUSED

        if signal.engagement_score <= self.satiated_threshold:
            return UserState.SATIATED

        return ctx.current_state


@dataclass
class DefaultInitiativePolicy:
    min_initiative_interval_sec: int = 3600
    max_latency_ms: int = 800

    def should_initiate(self, signal: UserSignal, ctx: TransitionContext) -> bool:
        now = signal.timestamp
        if now - ctx.last_initiative_ts < self.min_initiative_interval_sec:
            return False

        if signal.response_latency_ms > self.max_latency_ms:
            return False

        if ctx.current_state == UserState.AROUSED:
            return True

        if ctx.current_state == UserState.SATIATED and signal.engagement_score >= 0.5:
            return True

        return False


@dataclass
class AgentDecision:
    next_state: UserState
    should_initiate: bool


class AgentStateMachine:
    def __init__(
        self,
        transition_policy: StateTransitionPolicy,
        initiative_policy: InitiativePolicy,
    ) -> None:
        self._transition_policy = transition_policy
        self._initiative_policy = initiative_policy
        self._current_state = UserState.SATIATED
        self._last_state_change_ts = time.time()
        self._last_initiative_ts = 0.0

    def process(self, signal: UserSignal) -> AgentDecision:
        ctx = TransitionContext(
            current_state=self._current_state,
            last_state_change_ts=self._last_state_change_ts,
            last_initiative_ts=self._last_initiative_ts,
        )

        next_state = self._transition_policy.next_state(signal, ctx)
        if next_state != self._current_state:
            self._current_state = next_state
            self._last_state_change_ts = signal.timestamp

        should_initiate = self._initiative_policy.should_initiate(signal, ctx)
        if should_initiate:
            self._last_initiative_ts = signal.timestamp

        return AgentDecision(
            next_state=self._current_state,
            should_initiate=should_initiate,
        )
```

## 终端内最小测试方式
```python
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

## 下一步建议（用于探索未知点）
1. **状态切换记录器**：记录每次状态变化的信号与原因。
2. **主动触发试验策略**：在规则基础上加入轻度随机化，观察用户反馈。
