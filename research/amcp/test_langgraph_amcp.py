from __future__ import annotations

from research.amcp.adapters import (
    LangGraphAMCPState,
    build_langgraph_amcp_app,
)
from research.amcp.core import ConsentGrant, build_demo_custodian


def _run_graph(state: LangGraphAMCPState) -> LangGraphAMCPState:
    app = build_langgraph_amcp_app()
    result = app.invoke(state)
    return result


def test_langgraph_allows_original_purpose_read() -> None:
    custodian, memory_id = build_demo_custodian()
    result = _run_graph(
        {
            "custodian": custodian,
            "runner_did": "did:runner:coding-agent-v1",
            "memory_id": memory_id,
            "purpose": "coding_assistant",
        }
    )

    assert result["next_node"] == "llm_node"
    assert result["amcp_last_decision"].allowed is True
    assert "allowed" in result["agent_response"].lower()
    assert result["memory_content"] == custodian.read_memory_content(memory_id)


def test_langgraph_denies_cross_purpose_without_full_consent() -> None:
    custodian, memory_id = build_demo_custodian()
    result = _run_graph(
        {
            "custodian": custodian,
            "runner_did": "did:runner:coding-agent-v1",
            "memory_id": memory_id,
            "purpose": "marketing_analytics",
        }
    )

    assert result["next_node"] == "consent_request_node"
    assert result["amcp_last_decision"].allowed is False
    assert result["amcp_last_decision"].missing_owner_consents == [
        "did:plc:alice",
        "did:plc:bob",
    ]
    assert "need explicit consent" in result["agent_response"].lower()


def test_langgraph_allows_cross_purpose_with_all_owner_consents() -> None:
    custodian, memory_id = build_demo_custodian()
    runner = "did:runner:coding-agent-v1"
    custodian.grant(
        ConsentGrant(
            owner_did="did:plc:alice",
            grantee_runner_did=runner,
            purpose="marketing_analytics",
            scope="single_memory",
            memory_id=memory_id,
        )
    )
    custodian.grant(
        ConsentGrant(
            owner_did="did:plc:bob",
            grantee_runner_did=runner,
            purpose="marketing_analytics",
            scope="single_memory",
            memory_id=memory_id,
        )
    )

    result = _run_graph(
        {
            "custodian": custodian,
            "runner_did": runner,
            "memory_id": memory_id,
            "purpose": "marketing_analytics",
        }
    )

    assert result["next_node"] == "llm_node"
    assert result["amcp_last_decision"].allowed is True
    assert result["memory_content"] == custodian.read_memory_content(memory_id)
