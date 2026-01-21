# CREATED_BY_AGENT
from app.core.agent import agent as agent_module
from app.core.agent.agent import Agent, INTELLIMATE_AGENT_ID, INTELLIMATE_AGENT_NAME


def _build_agent(*, agent_id: str, name: str, personality: str) -> Agent:
    return Agent(
        agent_id=agent_id,
        name=name,
        model_config={},
        personality=personality,
    )


def _get_contents(messages) -> list[str]:
    return [message.content for message in messages]


def test_intellimate_official_injects_manual_prompt(tmp_path, monkeypatch):
    manual_path = tmp_path / "INTELLIMATE.md"
    manual_path.write_text(
        "\n".join(
            [
                "# IntelliMate User Guide",
                "",
                "> CREATED_BY_AGENT",
                "",
                "> Content should be copied to https://www.notion.so/IntelliMate-Help-Center-2b88c199b74b808a985bcaa64e36c322",
                "",
                "> 这里的内容被拷贝到 IntelliMate 官方助手角色系统消息（称为提示词的一部分）",
                "> 拷贝时，以 > 开头的文本行会被删除掉",
                "",
                "MANUAL_LINE_1",
                "MANUAL_LINE_2",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(agent_module, "INTELLIMATE_USER_MANUAL_PATH", manual_path)
    agent_module._load_intellimate_user_manual.cache_clear()

    agent = _build_agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name=INTELLIMATE_AGENT_NAME,
        personality="Warm personality.",
    )
    contents = _get_contents(agent.build_system_messages("", None))

    last = contents[-1]
    assert last.startswith("##IntelliMate User Manual\n# IntelliMate User Guide")
    assert "MANUAL_LINE_1" in last
    assert "MANUAL_LINE_2" in last
    assert ">" not in last
    assert "CREATED_BY_AGENT" not in last
    assert "Content should be copied to" not in last
    assert "拷贝时，以 > 开头的文本行会被删除掉" not in last


def test_non_intellimate_official_does_not_inject_manual_prompt(monkeypatch):
    monkeypatch.setattr(
        agent_module, "_load_intellimate_user_manual", lambda: "MANUAL_CONTENT"
    )
    agent = _build_agent(
        agent_id="not_intellimate",
        name="Not IntelliMate",
        personality="Warm personality.",
    )
    contents = _get_contents(agent.build_system_messages("", None))

    assert not any("##IntelliMate User Manual\n" in content for content in contents)
