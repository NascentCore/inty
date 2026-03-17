from types import SimpleNamespace

from app.core.agent import agent as legacy_agent_module
from app.core.agent.agent import (
    INTELLIMATE_AGENT_ID,
    INTELLIMATE_AGENT_NAME,
    OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME,
    OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME,
    Agent,
)
from app.core.agent.clean_prompt_system import (
    AgentPromptContext,
    AssistantMessageSnapshot,
    AssistantToolCall,
    AssistantToolCallFunction,
    ChatCompletionChoiceSnapshot,
    ChatCompletionSnapshot,
    ChatSettingsSnapshot,
    OfficialAssistantToolDeps,
    OfficialAssistantToolLoopInput,
    OpenAIChatMessageSnapshot,
    PromptBuildInput,
    UserTimeContextSnapshot,
    build_system_messages,
    build_system_messages_for_chat,
    openai_dicts_from_messages,
    resolve_official_assistant_tool_calls,
)


def _contents(messages) -> list[str]:
    return [message.content for message in messages]


def _build_legacy_response_with_tool_call(
    *, tool_name: str, tool_arguments: str, content: str
):
    function = SimpleNamespace(name=tool_name, arguments=tool_arguments)
    tool_call = SimpleNamespace(id="tool-call-1", type="function", function=function)
    message = SimpleNamespace(content=content, tool_calls=[tool_call])
    choice = SimpleNamespace(message=message, finish_reason="tool_calls")
    return SimpleNamespace(choices=[choice], model="test-model", usage=None)


def _build_legacy_response_without_tool_call(*, content: str):
    message = SimpleNamespace(content=content, tool_calls=None)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice], model="test-model", usage=None)


def test_clean_prompt_builder_matches_legacy_default_path():
    user_profile = "Name: Alice\nBio: Test user"
    old_chat_settings = SimpleNamespace(
        style_prompt="Keep responses concise.",
        premium_mode=False,
        chat_mode=None,
    )
    new_chat_settings = ChatSettingsSnapshot(
        style_prompt="Keep responses concise.",
        premium_mode=False,
        chat_mode=None,
    )
    user_time_context = {
        "local_time": "2026-02-05T18:30:00",
        "timezone": "Asia/Shanghai",
        "utc_offset_minutes": 480,
    }
    old_agent = Agent(
        agent_id="agent-clean-1",
        name="Luna",
        model_config={},
        main_prompt="purity_main_0725",
        mode_prompt="flirting_mode_20250902",
        personality="You are {{char}} chatting with {{user}}.",
        scenario="Late night city walk.",
        message_example="(smiles) Hey there.",
        intro="Intro text.",
    )
    clean_context = AgentPromptContext(
        agent_id="agent-clean-1",
        name="Luna",
        main_prompt="purity_main_0725",
        mode_prompt="flirting_mode_20250902",
        personality="You are {{char}} chatting with {{user}}.",
        scenario="Late night city walk.",
        message_example="(smiles) Hey there.",
        intro="Intro text.",
    )

    legacy_messages = old_agent.build_system_messages(
        user_profile=user_profile,
        chat_settings=old_chat_settings,
        user_time_context=user_time_context,
        include_output_format_prompt=True,
    )
    clean_messages = build_system_messages(
        context=clean_context,
        request=PromptBuildInput(
            user_profile=user_profile,
            chat_settings=new_chat_settings,
            user_time_context=UserTimeContextSnapshot.model_validate(user_time_context),
            include_output_format_prompt=True,
        ),
    )

    assert _contents(clean_messages) == _contents(legacy_messages)


def test_clean_prompt_builder_matches_legacy_official_chat_path():
    user_profile = "Name: Bob"
    old_chat_settings = SimpleNamespace(
        style_prompt="Use precise app instructions.",
        premium_mode=False,
        chat_mode=None,
    )
    new_chat_settings = ChatSettingsSnapshot(
        style_prompt="Use precise app instructions.",
        premium_mode=False,
        chat_mode=None,
    )
    old_agent = Agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name=INTELLIMATE_AGENT_NAME,
        model_config={},
        personality="Official helper personality.",
        intro="",
    )
    clean_context = AgentPromptContext(
        agent_id=INTELLIMATE_AGENT_ID,
        name=INTELLIMATE_AGENT_NAME,
        personality="Official helper personality.",
        intro="",
    )

    legacy_messages = old_agent._build_system_messages_for_chat(
        user_profile=user_profile,
        chat_settings=old_chat_settings,
        user_time_context=None,
    )
    clean_messages = build_system_messages_for_chat(
        context=clean_context,
        request=PromptBuildInput(
            user_profile=user_profile,
            chat_settings=new_chat_settings,
            user_time_context=None,
        ),
    )

    assert _contents(clean_messages) == _contents(legacy_messages)


def test_clean_prompt_builder_matches_legacy_without_output_format_prompt():
    user_profile = "Name: Casey"
    old_agent = Agent(
        agent_id="agent-clean-2",
        name="Nova",
        model_config={},
        mode_prompt="purity_mode_0725",
    )
    clean_context = AgentPromptContext(
        agent_id="agent-clean-2",
        name="Nova",
        mode_prompt="purity_mode_0725",
    )

    legacy_messages = old_agent._build_system_messages_for_chat(
        user_profile=user_profile,
        chat_settings=None,
        user_time_context=None,
        include_output_format_prompt=False,
    )
    clean_messages = build_system_messages_for_chat(
        context=clean_context,
        request=PromptBuildInput(
            user_profile=user_profile,
            chat_settings=None,
            user_time_context=None,
            include_output_format_prompt=False,
        ),
    )

    assert _contents(clean_messages) == _contents(legacy_messages)


def test_clean_tool_loop_matches_legacy_manual_tool_message_flow(
    monkeypatch,
):
    old_agent = Agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name="Inty",
        model_config={"model": "test-model"},
    )
    old_initial_response = _build_legacy_response_with_tool_call(
        tool_name=OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME,
        tool_arguments="{}",
        content="Let me read the manual first.",
    )
    old_final_response = _build_legacy_response_without_tool_call(content="Done.")
    captured_old: dict[str, list[dict]] = {}

    def fake_old_call_openai_api_with_retry(**kwargs):
        captured_old["messages"] = kwargs["openai_messages"]
        return old_final_response

    monkeypatch.setattr(
        old_agent,
        "_call_openai_api_with_retry",
        fake_old_call_openai_api_with_retry,
    )
    monkeypatch.setattr(legacy_agent_module, "_load_intellimate_user_manual", lambda: "MANUAL_X")

    old_response, _ = old_agent._resolve_official_assistant_tool_calls(
        response=old_initial_response,
        openai_messages=[{"role": "system", "content": "BASE_SYSTEM"}],
        client=object(),
        model="test-model",
        temperature=0.7,
        max_tokens=256,
        top_p=0.9,
        extra_body={"user": "user-1"},
        user_id="user-1",
        chat_name="test-chat",
        labels={},
    )

    new_initial_response = ChatCompletionSnapshot(
        choices=[
            ChatCompletionChoiceSnapshot(
                message=AssistantMessageSnapshot(
                    content="Let me read the manual first.",
                    tool_calls=[
                        AssistantToolCall(
                            id="tool-call-1",
                            function=AssistantToolCallFunction(
                                name=OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME,
                                arguments="{}",
                            ),
                        )
                    ],
                ),
                finish_reason="tool_calls",
            )
        ]
    )
    new_final_response = ChatCompletionSnapshot(
        choices=[
            ChatCompletionChoiceSnapshot(
                message=AssistantMessageSnapshot(content="Done.", tool_calls=[]),
                finish_reason="stop",
            )
        ]
    )
    captured_new: dict[str, list[dict]] = {}

    def continue_chat(messages):
        captured_new["messages"] = openai_dicts_from_messages(messages)
        return new_final_response

    new_output = resolve_official_assistant_tool_calls(
        request=OfficialAssistantToolLoopInput(
            response=new_initial_response,
            openai_messages=[
                OpenAIChatMessageSnapshot(role="system", content="BASE_SYSTEM")
            ],
            user_id="user-1",
        ),
        continue_chat=continue_chat,
        deps=OfficialAssistantToolDeps(
            load_user_manual=lambda: "MANUAL_X",
            load_change_logs=lambda: "CHANGE_LOGS_X",
        ),
    )

    assert old_response is old_final_response
    assert new_output.response == new_final_response
    assert captured_new["messages"] == captured_old["messages"]
    assert new_output.side_effects == []


def test_clean_tool_loop_returns_mbti_side_effect():
    initial_response = ChatCompletionSnapshot(
        choices=[
            ChatCompletionChoiceSnapshot(
                message=AssistantMessageSnapshot(
                    content="I will save your MBTI now.",
                    tool_calls=[
                        AssistantToolCall(
                            id="tool-call-1",
                            function=AssistantToolCallFunction(
                                name=OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME,
                                arguments='{"mbti_type":"enfp"}',
                            ),
                        )
                    ],
                ),
                finish_reason="tool_calls",
            )
        ]
    )
    final_response = ChatCompletionSnapshot(
        choices=[
            ChatCompletionChoiceSnapshot(
                message=AssistantMessageSnapshot(content="Saved.", tool_calls=[]),
                finish_reason="stop",
            )
        ]
    )
    captured_messages: dict[str, list[dict]] = {}

    def continue_chat(messages):
        captured_messages["messages"] = openai_dicts_from_messages(messages)
        return final_response

    output = resolve_official_assistant_tool_calls(
        request=OfficialAssistantToolLoopInput(
            response=initial_response,
            openai_messages=[OpenAIChatMessageSnapshot(role="user", content="test")],
            user_id="user-1",
        ),
        continue_chat=continue_chat,
    )

    assert output.response == final_response
    assert len(output.side_effects) == 1
    assert output.side_effects[0].user_id == "user-1"
    assert output.side_effects[0].mbti_type == "ENFP"
    assert any(
        message["role"] == "tool" and message["content"] == "Saved MBTI type: ENFP"
        for message in captured_messages["messages"]
    )
