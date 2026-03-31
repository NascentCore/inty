from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelRetry

from .core import AccessRequest, MemoryCustodian


@dataclass
class AccessAttempt:
    memory_id: str
    purpose: str
    allowed: bool
    reason: str
    missing_owner_consents: list[str] = field(default_factory=list)


class PydanticAIDeps(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    custodian: MemoryCustodian
    runner_did: str
    attempts: list[AccessAttempt] = Field(default_factory=list)


def create_pydantic_ai_amcp_agent(model: Any = "test") -> Agent[PydanticAIDeps, str]:
    agent: Agent[PydanticAIDeps, str] = Agent(
        model,
        deps_type=PydanticAIDeps,
        output_type=str,
        retries=1,
        instructions=(
            "Use `read_memory_with_amcp` for memory reads. "
            "If access is denied, ask for explicit user consent."
        ),
    )

    @agent.tool
    def read_memory_with_amcp(
        ctx: RunContext[PydanticAIDeps],
        memory_id: str,
        purpose: str,
    ) -> str:
        decision = ctx.deps.custodian.evaluate_access(
            AccessRequest(
                memory_id=memory_id,
                requester_runner_did=ctx.deps.runner_did,
                purpose=purpose,
            )
        )
        ctx.deps.attempts.append(
            AccessAttempt(
                memory_id=memory_id,
                purpose=purpose,
                allowed=decision.allowed,
                reason=decision.reason,
                missing_owner_consents=decision.missing_owner_consents,
            )
        )
        if not decision.allowed:
            raise ModelRetry(
                "AMCP_DENY "
                f"purpose={purpose} "
                f"missing={','.join(decision.missing_owner_consents)}"
            )
        return ctx.deps.custodian.memories[memory_id].content

    return agent


def langgraph_amcp_node_architecture_note() -> dict:
    # 中文注释：当前仓库没有安装 langgraph，这里先提供可执行架构约定。
    return {
        "graph_state": {
            "runner_did": "str",
            "memory_id": "str",
            "purpose": "str",
            "messages": "list",
            "amcp_last_decision": "AccessDecision | None",
        },
        "nodes": [
            "policy_check_node: AccessRequest -> AccessDecision",
            "llm_node: only when access allowed",
            "consent_request_node: when access denied",
        ],
        "edge_rule": "if denied route to consent_request_node; if allowed route to llm_node",
    }
