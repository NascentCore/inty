from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelRetry

from .core import AccessDecision, AccessRequest, MemoryCustodian


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
    # 中文注释：给出与实现保持一致的节点/边契约，便于多框架共用核心策略层。
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


class LangGraphAMCPState(TypedDict):
    runner_did: str
    memory_id: str
    purpose: str
    amcp_last_decision: AccessDecision | None
    route: str
    result: str


def build_langgraph_amcp_app(custodian: MemoryCustodian):
    def policy_check_node(state: LangGraphAMCPState) -> dict:
        decision = custodian.evaluate_access(
            AccessRequest(
                memory_id=state["memory_id"],
                requester_runner_did=state["runner_did"],
                purpose=state["purpose"],
            )
        )
        return {"amcp_last_decision": decision}

    def llm_node(state: LangGraphAMCPState) -> dict:
        memory_text = custodian.read_memory_content(state["memory_id"])
        return {"route": "llm_node", "result": f"allowed:{memory_text}"}

    def consent_request_node(state: LangGraphAMCPState) -> dict:
        decision = state["amcp_last_decision"]
        missing = decision.missing_owner_consents if decision else []
        return {
            "route": "consent_request_node",
            "result": f"denied:missing={','.join(missing)}",
        }

    def route_by_policy(state: LangGraphAMCPState) -> str:
        decision = state["amcp_last_decision"]
        if decision is None:
            raise ValueError("amcp_last_decision must be set before routing.")
        if decision.allowed:
            return "llm_node"
        return "consent_request_node"

    graph = StateGraph(LangGraphAMCPState)
    graph.add_node("policy_check_node", policy_check_node)
    graph.add_node("llm_node", llm_node)
    graph.add_node("consent_request_node", consent_request_node)
    graph.add_edge(START, "policy_check_node")
    graph.add_conditional_edges(
        "policy_check_node",
        route_by_policy,
        {"llm_node": "llm_node", "consent_request_node": "consent_request_node"},
    )
    graph.add_edge("llm_node", END)
    graph.add_edge("consent_request_node", END)
    return graph.compile()


class LangGraphAMCPFlowResult(TypedDict):
    allowed: bool
    route: str
    response: str
    missing_owner_consents: list[str]
    reason: str


def run_langgraph_amcp_flow(
    custodian: MemoryCustodian,
    runner_did: str,
    memory_id: str,
    purpose: str,
) -> LangGraphAMCPFlowResult:
    app = build_langgraph_amcp_app(custodian)
    final_state = app.invoke(
        {
            "runner_did": runner_did,
            "memory_id": memory_id,
            "purpose": purpose,
            "amcp_last_decision": None,
            "route": "",
            "result": "",
        }
    )
    decision = final_state["amcp_last_decision"]
    if decision is None:
        raise ValueError("LangGraph flow finished without AMCP decision.")
    return {
        "allowed": decision.allowed,
        "route": final_state["route"],
        "response": final_state["result"],
        "missing_owner_consents": decision.missing_owner_consents,
        "reason": decision.reason,
    }
