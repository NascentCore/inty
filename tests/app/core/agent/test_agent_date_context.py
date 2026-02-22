from datetime import datetime, timezone

from app.core.agent.agent import Agent
from langchain_core.messages import AIMessage, HumanMessage


def _build_agent() -> Agent:
    return Agent(
        agent_id="agent-date-context-test",
        name="DateContextAgent",
        model_config={},
    )


def _count_system_messages(messages) -> int:
    return sum(1 for message in messages if message.type == "system")


def test_build_messages_with_date_system_prompts_inserts_prompt_on_day_change():
    agent = _build_agent()
    history_messages = [
        HumanMessage(
            content="history-1",
            additional_kwargs={"created_at": "2026-02-20T10:00:00+00:00"},
        ),
        AIMessage(
            content="history-2",
            additional_kwargs={"created_at": "2026-02-20T11:00:00+00:00"},
        ),
        HumanMessage(
            content="history-3",
            additional_kwargs={"created_at": "2026-02-21T09:00:00+00:00"},
        ),
    ]
    current_messages = [HumanMessage(content="today-message")]

    result = agent._build_messages_with_date_system_prompts(
        history_messages=history_messages,
        current_messages=current_messages,
        now_utc=datetime(2026, 2, 22, 8, 30, tzinfo=timezone.utc),
    )

    assert [message.type for message in result] == [
        "system",
        "human",
        "ai",
        "system",
        "human",
        "system",
        "human",
    ]
    assert "2026-02-20" in result[0].content
    assert "2026-02-21" in result[3].content
    assert "2026-02-22" in result[5].content


def test_build_messages_with_date_system_prompts_same_day_has_single_prompt():
    agent = _build_agent()
    history_messages = [
        HumanMessage(
            content="history-1",
            additional_kwargs={"created_at": "2026-02-22T10:00:00+00:00"},
        ),
        AIMessage(
            content="history-2",
            additional_kwargs={"created_at": "2026-02-22T10:01:00+00:00"},
        ),
    ]
    current_messages = [HumanMessage(content="today-message")]

    result = agent._build_messages_with_date_system_prompts(
        history_messages=history_messages,
        current_messages=current_messages,
        now_utc=datetime(2026, 2, 22, 18, 0, tzinfo=timezone.utc),
    )

    assert _count_system_messages(result) == 1
    assert "2026-02-22" in result[0].content
    assert [message.type for message in result] == ["system", "human", "ai", "human"]


def test_build_messages_with_date_system_prompts_without_history_starts_with_date_prompt():
    agent = _build_agent()

    result = agent._build_messages_with_date_system_prompts(
        history_messages=[],
        current_messages=[HumanMessage(content="hello")],
        now_utc=datetime(2026, 2, 23, 7, 0, tzinfo=timezone.utc),
    )

    assert [message.type for message in result] == ["system", "human"]
    assert "2026-02-23" in result[0].content
