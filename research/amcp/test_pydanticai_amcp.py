from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from research.amcp.adapters import PydanticAIDeps, create_pydantic_ai_amcp_agent
from research.amcp.core import ConsentGrant, build_demo_custodian


def _build_memory_reader_model(memory_id: str, purpose: str) -> FunctionModel:
    def function(messages: list, _: AgentInfo) -> ModelResponse:
        saw_tool_return = False
        for message in messages:
            if isinstance(message, ModelRequest):
                for part in message.parts:
                    if isinstance(part, ToolReturnPart):
                        saw_tool_return = True
        if not saw_tool_return:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="read_memory_with_amcp",
                        args={"memory_id": memory_id, "purpose": purpose},
                    )
                ],
                model_name="memory-reader-test-model",
            )
        return ModelResponse(
            parts=[TextPart(content="done")],
            model_name="memory-reader-test-model",
        )

    return FunctionModel(function=function, model_name="memory-reader-test-model")


def test_pydantic_ai_allows_original_purpose_read() -> None:
    custodian, memory_id = build_demo_custodian()
    deps = PydanticAIDeps(
        custodian=custodian,
        runner_did="did:runner:coding-agent-v1",
    )
    model = _build_memory_reader_model(memory_id=memory_id, purpose="coding_assistant")
    agent: Agent[PydanticAIDeps, str] = create_pydantic_ai_amcp_agent(model=model)

    result = agent.run_sync("Read memory for coding task", deps=deps)

    assert result.output == "done"
    assert len(deps.attempts) == 1
    assert deps.attempts[0].allowed is True
    assert deps.attempts[0].purpose == "coding_assistant"


def test_pydantic_ai_denies_cross_purpose_without_full_consent() -> None:
    custodian, memory_id = build_demo_custodian()
    deps = PydanticAIDeps(
        custodian=custodian,
        runner_did="did:runner:coding-agent-v1",
    )
    model = _build_memory_reader_model(memory_id=memory_id, purpose="marketing_analytics")
    agent: Agent[PydanticAIDeps, str] = create_pydantic_ai_amcp_agent(model=model)

    try:
        agent.run_sync("Read memory for analytics", deps=deps)
    except UnexpectedModelBehavior as exc:
        assert "exceeded max retries" in str(exc).lower()
    else:
        raise AssertionError("Expected AMCP denial to trigger model retry failure.")

    assert len(deps.attempts) == 2
    assert all(attempt.allowed is False for attempt in deps.attempts)
    assert deps.attempts[-1].missing_owner_consents == ["did:plc:alice", "did:plc:bob"]


def test_pydantic_ai_allows_cross_purpose_with_all_owner_consents() -> None:
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
    deps = PydanticAIDeps(custodian=custodian, runner_did=runner)
    model = _build_memory_reader_model(memory_id=memory_id, purpose="marketing_analytics")
    agent: Agent[PydanticAIDeps, str] = create_pydantic_ai_amcp_agent(model=model)

    result = agent.run_sync("Read memory for analytics with consent", deps=deps)

    assert result.output == "done"
    assert len(deps.attempts) == 1
    assert deps.attempts[0].allowed is True
    assert deps.attempts[0].missing_owner_consents == []
