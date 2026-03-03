# CREATED_BY_AGENT
from app.core.agent import agent as agent_module
from app.core.agent import prompts
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


def _find_message_by_prefix(contents: list[str], prefix: str) -> str:
    return next(content for content in contents if content.startswith(prefix))


MANUAL_PROMPT_CONTENT = "\n".join(
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
)
CHANGE_LOGS_PROMPT_CONTENT = "\n".join(
    [
        "# IntelliMate Change Logs",
        "",
        "> CREATED_BY_AGENT",
        "",
        "> This content is injected into the Inty official assistant system message.",
        "> Lines starting with \">\" will be removed during injection.",
        "",
        "CHANGE_LOG_LINE_1",
        "CHANGE_LOG_LINE_2",
    ]
)
MINIMAL_MANUAL_CONTENT = "# IntelliMate User Guide\nMANUAL_CONTENT"
MINIMAL_CHANGE_LOGS_CONTENT = "# IntelliMate Change Logs\nCHANGE_LOG_CONTENT"
OFFICIAL_RENAME_MESSAGE_PREFIX = "##Official Assistant Naming Update\n"
OFFICIAL_RENAME_MESSAGE_LINE = (
    "- The official assistant in the IntelliMate app is now named Inty."
)


def _patch_manual_and_change_logs(
    monkeypatch, manual_path, change_logs_path
) -> None:
    monkeypatch.setattr(agent_module, "INTELLIMATE_USER_MANUAL_PATH", manual_path)
    monkeypatch.setattr(agent_module, "INTELLIMATE_CHANGE_LOGS_PATH", change_logs_path)
    agent_module._load_intellimate_user_manual.cache_clear()
    agent_module._load_intellimate_change_logs.cache_clear()


def test_intellimate_change_logs_default_path_points_to_android_app_docs():
    expected_path = agent_module.REPO_ROOT / "android_app" / "docs" / "CHANGE_LOGS.md"
    assert agent_module.INTELLIMATE_CHANGE_LOGS_PATH == expected_path


def test_intellimate_official_injects_repo_change_logs_content(tmp_path, monkeypatch):
    manual_path = tmp_path / "INTELLIMATE.md"
    manual_path.write_text(MINIMAL_MANUAL_CONTENT, encoding="utf-8")
    _patch_manual_and_change_logs(
        monkeypatch, manual_path, agent_module.INTELLIMATE_CHANGE_LOGS_PATH
    )

    expected_change_logs = "\n".join(
        line
        for line in agent_module.INTELLIMATE_CHANGE_LOGS_PATH.read_text(
            encoding="utf-8"
        ).splitlines()
        if not line.lstrip().startswith(">")
    ).strip()

    agent = _build_agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name=INTELLIMATE_AGENT_NAME,
        personality="Warm personality.",
    )
    contents = _get_contents(agent.build_system_messages("", None))
    change_logs_message = _find_message_by_prefix(
        contents, "##IntelliMate Change Logs\n"
    )
    rename_message = _find_message_by_prefix(contents, OFFICIAL_RENAME_MESSAGE_PREFIX)

    assert change_logs_message == (
        "##IntelliMate Change Logs\n" + expected_change_logs
    )
    assert OFFICIAL_RENAME_MESSAGE_LINE in rename_message
    assert "CREATED_BY_AGENT" not in change_logs_message


def test_intellimate_official_injects_manual_prompt(tmp_path, monkeypatch):
    manual_path = tmp_path / "INTELLIMATE.md"
    manual_path.write_text(MANUAL_PROMPT_CONTENT, encoding="utf-8")
    change_logs_path = tmp_path / "CHANGE_LOGS.md"
    change_logs_path.write_text(CHANGE_LOGS_PROMPT_CONTENT, encoding="utf-8")
    _patch_manual_and_change_logs(monkeypatch, manual_path, change_logs_path)

    agent = _build_agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name=INTELLIMATE_AGENT_NAME,
        personality="Warm personality.",
    )
    contents = _get_contents(agent.build_system_messages("", None))

    manual_message = _find_message_by_prefix(contents, "##IntelliMate User Manual\n")
    rename_message = _find_message_by_prefix(contents, OFFICIAL_RENAME_MESSAGE_PREFIX)
    assert manual_message.startswith(
        "##IntelliMate User Manual\n# IntelliMate User Guide"
    )
    assert OFFICIAL_RENAME_MESSAGE_LINE in rename_message
    assert "MANUAL_LINE_1" in manual_message
    assert "MANUAL_LINE_2" in manual_message
    assert ">" not in manual_message
    assert "CREATED_BY_AGENT" not in manual_message
    assert "Content should be copied to" not in manual_message
    assert "拷贝时，以 > 开头的文本行会被删除掉" not in manual_message


def test_intellimate_official_injects_change_logs_prompt(tmp_path, monkeypatch):
    manual_path = tmp_path / "INTELLIMATE.md"
    manual_path.write_text(MINIMAL_MANUAL_CONTENT, encoding="utf-8")
    change_logs_path = tmp_path / "CHANGE_LOGS.md"
    change_logs_path.write_text(CHANGE_LOGS_PROMPT_CONTENT, encoding="utf-8")
    _patch_manual_and_change_logs(monkeypatch, manual_path, change_logs_path)

    agent = _build_agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name=INTELLIMATE_AGENT_NAME,
        personality="Warm personality.",
    )
    contents = _get_contents(agent.build_system_messages("", None))

    change_logs_message = _find_message_by_prefix(
        contents, "##IntelliMate Change Logs\n"
    )
    rename_message = _find_message_by_prefix(contents, OFFICIAL_RENAME_MESSAGE_PREFIX)
    assert change_logs_message.startswith(
        "##IntelliMate Change Logs\n# IntelliMate Change Logs"
    )
    assert OFFICIAL_RENAME_MESSAGE_LINE in rename_message
    assert "CHANGE_LOG_LINE_1" in change_logs_message
    assert "CHANGE_LOG_LINE_2" in change_logs_message
    assert ">" not in change_logs_message
    assert "CREATED_BY_AGENT" not in change_logs_message
    assert "Lines starting with" not in change_logs_message


def test_build_system_messages_for_intellimate_official_assistant_happy_case(
    tmp_path, monkeypatch
):
    """Happy case: new API returns User Manual, Change Logs, and character context."""
    manual_path = tmp_path / "INTELLIMATE.md"
    manual_path.write_text(MINIMAL_MANUAL_CONTENT, encoding="utf-8")
    change_logs_path = tmp_path / "CHANGE_LOGS.md"
    change_logs_path.write_text(CHANGE_LOGS_PROMPT_CONTENT, encoding="utf-8")
    _patch_manual_and_change_logs(monkeypatch, manual_path, change_logs_path)

    agent = _build_agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name=INTELLIMATE_AGENT_NAME,
        personality="Warm personality.",
    )
    contents = _get_contents(
        agent.build_system_messages_for_intellimate_official_assistant("", None)
    )

    manual_message = _find_message_by_prefix(contents, "##IntelliMate User Manual\n")
    rename_message = _find_message_by_prefix(contents, OFFICIAL_RENAME_MESSAGE_PREFIX)
    assert manual_message.startswith("##IntelliMate User Manual\n")
    assert OFFICIAL_RENAME_MESSAGE_LINE in rename_message

    change_logs_message = _find_message_by_prefix(
        contents, "##IntelliMate Change Logs\n"
    )
    assert change_logs_message.startswith("##IntelliMate Change Logs\n")
    assert "CHANGE_LOG_LINE_1" in change_logs_message

    assert any("Warm personality." in c for c in contents)


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
    assert not any("##IntelliMate Change Logs\n" in content for content in contents)
    assert not any(
        OFFICIAL_RENAME_MESSAGE_PREFIX in content for content in contents
    )


def test_intellimate_official_has_empty_main_and_mode_prompts(tmp_path, monkeypatch):
    """IntelliMate 的 main_prompt 与 mode_prompt 应为空，不注入默认角色扮演提示词。"""
    manual_path = tmp_path / "INTELLIMATE.md"
    manual_path.write_text(MINIMAL_MANUAL_CONTENT, encoding="utf-8")
    change_logs_path = tmp_path / "CHANGE_LOGS.md"
    change_logs_path.write_text(MINIMAL_CHANGE_LOGS_CONTENT, encoding="utf-8")
    _patch_manual_and_change_logs(monkeypatch, manual_path, change_logs_path)

    agent = _build_agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name=INTELLIMATE_AGENT_NAME,
        personality="Warm personality.",
    )

    assert agent._get_effective_main_prompt() == ""
    assert agent._get_effective_mode_prompt() == ""

    contents = _get_contents(agent.build_system_messages("", None))
    default_main = prompts.ROMANTIC_ROLEPLAY_PROMPT.main_prompt
    default_mode = prompts.ROMANTIC_ROLEPLAY_PROMPT.mode_prompt
    assert not any(default_main in c for c in contents)
    assert not any(default_mode in c for c in contents)
    assert any("##IntelliMate User Manual" in c for c in contents)
    assert any("##IntelliMate Change Logs" in c for c in contents)


def test_build_system_messages_includes_time_context(monkeypatch):
    monkeypatch.setattr(
        agent_module.global_config.app.features,
        "experimental_enable_chat_with_user_time_context",
        True,
    )
    agent = _build_agent(
        agent_id="agent_time_context",
        name="TimeAware",
        personality="Warm personality.",
    )
    user_time_context = {
        "local_time": "2026-02-05T18:30:00",
        "timezone": "Asia/Shanghai",
        "utc_offset_minutes": 480,
    }
    contents = _get_contents(
        agent.build_system_messages("", None, user_time_context=user_time_context)
    )
    combined = "\n".join(contents)

    assert "##User Time Context" in combined
    assert "2026-02-05T18:30:00" in combined
    assert "Asia/Shanghai" in combined
    assert "UTC+08:00" in combined
    assert "Do not claim to need sleep or be offline." in combined
