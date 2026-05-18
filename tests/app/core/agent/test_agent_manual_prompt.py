# CREATED_BY_AGENT
from app.core.agent import agent as agent_module
from app.core.agent import prompts
from app.core.agent.agent import Agent, INTELLIMATE_AGENT_ID, INTELLIMATE_AGENT_NAME
from app.core.user_time_context_prompt import suffix_user_text_with_time_context_lines
from langchain_core.messages import SystemMessage


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


def test_intellimate_official_does_not_inject_change_logs_by_default(
    tmp_path, monkeypatch
):
    manual_path = tmp_path / "INTELLIMATE.md"
    manual_path.write_text(MINIMAL_MANUAL_CONTENT, encoding="utf-8")
    _patch_manual_and_change_logs(
        monkeypatch, manual_path, agent_module.INTELLIMATE_CHANGE_LOGS_PATH
    )

    agent = _build_agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name=INTELLIMATE_AGENT_NAME,
        personality="Warm personality.",
    )
    contents = _get_contents(agent.build_system_messages("", None))
    rename_message = _find_message_by_prefix(contents, OFFICIAL_RENAME_MESSAGE_PREFIX)

    assert OFFICIAL_RENAME_MESSAGE_LINE in rename_message
    assert not any(content.startswith("##IntelliMate Change Logs\n") for content in contents)


def test_intellimate_official_adds_manual_tool_usage_guidance(tmp_path, monkeypatch):
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

    tool_usage_message = _find_message_by_prefix(contents, "##Official Assistant Tool Usage\n")
    rename_message = _find_message_by_prefix(contents, OFFICIAL_RENAME_MESSAGE_PREFIX)
    assert tool_usage_message.startswith("##Official Assistant Tool Usage\n")
    assert OFFICIAL_RENAME_MESSAGE_LINE in rename_message
    assert "read_user_manual" in tool_usage_message
    assert "read_change_logs" in tool_usage_message
    assert not any("##IntelliMate User Manual\n" in content for content in contents)


def test_intellimate_official_does_not_inject_change_logs_prompt(tmp_path, monkeypatch):
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

    tool_usage_message = _find_message_by_prefix(contents, "##Official Assistant Tool Usage\n")
    rename_message = _find_message_by_prefix(contents, OFFICIAL_RENAME_MESSAGE_PREFIX)
    assert tool_usage_message.startswith("##Official Assistant Tool Usage\n")
    assert OFFICIAL_RENAME_MESSAGE_LINE in rename_message
    assert "read_change_logs" in tool_usage_message
    assert not any(content.startswith("##IntelliMate Change Logs\n") for content in contents)


def test_build_system_messages_for_intellimate_official_assistant_happy_case(
    tmp_path, monkeypatch
):
    """Happy case: new API returns tool guidance and character context."""
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

    tool_usage_message = _find_message_by_prefix(contents, "##Official Assistant Tool Usage\n")
    rename_message = _find_message_by_prefix(contents, OFFICIAL_RENAME_MESSAGE_PREFIX)
    assert tool_usage_message.startswith("##Official Assistant Tool Usage\n")
    assert OFFICIAL_RENAME_MESSAGE_LINE in rename_message
    assert "read_change_logs" in tool_usage_message
    assert not any(content.startswith("##IntelliMate Change Logs\n") for content in contents)

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
    assert any("##Official Assistant Tool Usage" in c for c in contents)
    assert any("read_change_logs" in c for c in contents)
    assert not any("##IntelliMate Change Logs" in c for c in contents)


def test_build_system_messages_excludes_user_time_from_system(monkeypatch):
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

    assert "##User Time Context" not in combined


def test_openai_tail_user_message_includes_time_suffix(monkeypatch):
    monkeypatch.setattr(
        agent_module.global_config.app.features,
        "experimental_enable_chat_with_user_time_context",
        True,
    )
    from langchain_core.messages import HumanMessage

    ctx = {
        "local_time": "2026-02-05T18:30:00",
        "timezone": "Asia/Shanghai",
        "utc_offset_minutes": 480,
    }
    expected = suffix_user_text_with_time_context_lines("hello", ctx, enabled=True)
    msgs = [
        SystemMessage(content="sys"),
        HumanMessage(content="hello"),
    ]
    out = agent_module._openai_messages_from_lc_messages_with_tail_user_time(
        msgs,
        user_name="U",
        agent_name="A",
        user_time_context=ctx,
    )
    assert out[-1]["role"] == "user"
    body = out[-1]["content"]
    assert isinstance(body, str)
    assert body == expected
    assert "user-time-utc-offset" not in body


def test_build_system_messages_can_omit_output_format_prompt():
    agent = Agent(
        agent_id="agent_output_format",
        name="OutputFormatAgent",
        model_config={},
        mode_prompt="purity_mode_0725",
    )

    with_output_format = _get_contents(
        agent.build_system_messages("", None, include_output_format_prompt=True)
    )
    without_output_format = _get_contents(
        agent.build_system_messages("", None, include_output_format_prompt=False)
    )

    output_format_marker = (
        "All actions, expressions, psychology or scene descriptions must be enclosed in brackets ()."
    )
    assert any(output_format_marker in content for content in with_output_format)
    assert not any(output_format_marker in content for content in without_output_format)
    assert any("## Purity Mode" in content for content in without_output_format)


def test_build_system_messages_for_chat_uses_official_builder(monkeypatch):
    agent = _build_agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name=INTELLIMATE_AGENT_NAME,
        personality="Warm personality.",
    )
    official_messages = [SystemMessage(content="OFFICIAL_SYSTEM")]

    monkeypatch.setattr(
        agent,
        "build_system_messages_for_intellimate_official_assistant",
        lambda user_profile, chat_settings, user_time_context: official_messages,
    )

    def _unexpected_default_builder(*args, **kwargs):
        raise AssertionError("default builder should not be used for official assistant")

    monkeypatch.setattr(agent, "build_system_messages", _unexpected_default_builder)

    result = agent._build_system_messages_for_chat(
        user_profile="Name: Alice",
        chat_settings=None,
        user_time_context=None,
    )

    assert result == official_messages


def test_build_system_messages_for_chat_uses_default_builder_for_non_official(
    monkeypatch,
):
    agent = _build_agent(
        agent_id="not_intellimate",
        name="Not IntelliMate",
        personality="Warm personality.",
    )
    default_messages = [SystemMessage(content="DEFAULT_SYSTEM")]
    captured: dict[str, bool] = {"include_output_format_prompt": False}

    monkeypatch.setattr(
        agent,
        "build_system_messages_for_intellimate_official_assistant",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("official builder should not be used for non-official agent")
        ),
    )

    def _default_builder(
        user_profile, chat_settings, user_time_context, include_output_format_prompt
    ):
        captured["include_output_format_prompt"] = include_output_format_prompt
        return default_messages

    monkeypatch.setattr(agent, "build_system_messages", _default_builder)

    result = agent._build_system_messages_for_chat(
        user_profile="Name: Bob",
        chat_settings=None,
        user_time_context=None,
    )

    assert result == default_messages
    assert captured["include_output_format_prompt"] is True


def test_official_tool_usage_prompt_guides_feature_question_answers():
    assert "step-by-step" in agent_module.INTELLIMATE_USER_MANUAL_TOOL_USAGE_SYSTEM_MESSAGE
    assert "prerequisites" in agent_module.INTELLIMATE_USER_MANUAL_TOOL_USAGE_SYSTEM_MESSAGE
    assert (
        "ask one concise clarifying question"
        in agent_module.INTELLIMATE_USER_MANUAL_TOOL_USAGE_SYSTEM_MESSAGE
    )
