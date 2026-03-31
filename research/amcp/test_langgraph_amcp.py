from __future__ import annotations

from research.amcp.adapters import run_langgraph_amcp_flow
from research.amcp.core import ConsentGrant, build_demo_custodian


def _run_flow(
    *,
    custodian,
    runner_did: str,
    memory_id: str,
    purpose: str,
) -> dict:
    return run_langgraph_amcp_flow(
        custodian=custodian,
        runner_did=runner_did,
        memory_id=memory_id,
        purpose=purpose,
    )


def test_langgraph_allows_original_purpose_read() -> None:
    custodian, memory_id = build_demo_custodian()
    result = _run_flow(
        custodian=custodian,
        runner_did="did:runner:coding-agent-v1",
        memory_id=memory_id,
        purpose="coding_assistant",
    )

    assert result["allowed"] is True
    assert result["route"] == "llm_node"
    assert "allowed" in result["response"].lower()


def test_langgraph_denies_cross_purpose_without_full_consent() -> None:
    custodian, memory_id = build_demo_custodian()
    result = _run_flow(
        custodian=custodian,
        runner_did="did:runner:coding-agent-v1",
        memory_id=memory_id,
        purpose="marketing_analytics",
    )

    assert result["allowed"] is False
    assert result["route"] == "consent_request_node"
    assert result["missing_owner_consents"] == [
        "did:plc:alice",
        "did:plc:bob",
    ]
    assert "denied:missing" in result["response"].lower()


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

    result = _run_flow(
        custodian=custodian,
        runner_did=runner,
        memory_id=memory_id,
        purpose="marketing_analytics",
    )

    assert result["allowed"] is True
    assert result["route"] == "llm_node"
    assert "allowed:" in result["response"].lower()
