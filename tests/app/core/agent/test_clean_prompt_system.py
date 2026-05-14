from types import SimpleNamespace

import pytest

from app.core.agent import agent as legacy_agent_module
from app.core.agent import prompts
from app.core.agent.agent import (
    INTELLIMATE_AGENT_ID,
    INTELLIMATE_AGENT_NAME,
    OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME,
    OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME,
    Agent,
)
from app.core.agent.agent_prompt_configs import AgentPromptOverride
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
    PromptAssemblyDeps,
    PromptBuildInput,
    UserTimeContextSnapshot,
    build_system_messages,
    build_system_messages_for_chat,
    chat_completion_snapshot_from_openai_response,
    execute_official_assistant_tool_call,
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
        return (old_final_response, None)

    monkeypatch.setattr(
        old_agent,
        "_call_openai_api_with_retry",
        fake_old_call_openai_api_with_retry,
    )
    monkeypatch.setattr(
        legacy_agent_module, "_load_intellimate_user_manual", lambda: "MANUAL_X"
    )

    old_response, _, _ = old_agent._resolve_official_assistant_tool_calls(
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


def test_agent_prompt_context_from_legacy_uses_llm_config_and_alias():
    context_with_llm_config = AgentPromptContext.from_legacy_agent_data(
        agent_id="agent-llm-1",
        agent_data={
            "name": "A",
            "settings": {
                "llm_config": {
                    "model": "anthropic/claude-3.5-sonnet",
                    "temperature": 0.4,
                }
            },
        },
    )
    assert context_with_llm_config.resolved_llm_config() is not None
    assert (
        context_with_llm_config.resolved_llm_config().model
        == "anthropic/claude-3.5-sonnet"
    )

    context_with_legacy_alias = AgentPromptContext.from_legacy_agent_data(
        agent_id="agent-llm-2",
        agent_data={
            "name": "B",
            "settings": {"model_config": {"model": "openai/gpt-4o-mini"}},
        },
    )
    assert context_with_legacy_alias.resolved_llm_config() is not None
    assert context_with_legacy_alias.resolved_llm_config().model == "openai/gpt-4o-mini"


def test_agent_prompt_context_from_legacy_rejects_non_object_settings():
    with pytest.raises(ValueError):
        AgentPromptContext.from_legacy_agent_data(
            agent_id="agent-bad-settings",
            agent_data={"name": "Bad", "settings": "not-an-object"},
        )


def test_clean_prompt_builder_honors_override_mode_and_suppresses_output_format():
    render = lambda tmpl, char, user: tmpl.replace("{{char}}", char).replace(
        "{{user}}", user or ""
    )
    deps = PromptAssemblyDeps(
        render_prompt=render,
        lookup_prompt_override=lambda *_: AgentPromptOverride(
            main_prompt=None, mode_prompt="OVERRIDE_MODE_FOR_{{char}}"
        ),
        is_christmas_prompt_enabled=lambda: False,
    )
    context = AgentPromptContext(
        agent_id="agent-override-1",
        name="Luna",
        main_prompt="purity_main_0725",
        mode_prompt="purity_mode_0725",
    )
    request = PromptBuildInput(
        user_profile="Name: Alice",
        chat_settings=ChatSettingsSnapshot(chat_mode=None, premium_mode=False),
        include_output_format_prompt=True,
    )

    messages = build_system_messages(context=context, request=request, deps=deps)
    contents = _contents(messages)

    expected_override_mode = "OVERRIDE_MODE_FOR_Luna"
    expected_suppressed_output = render(
        prompts.get_mode_output_format_prompt_by_id("purity_mode_0725"), "Luna", "Alice"
    )
    assert any(expected_override_mode == content for content in contents)
    assert not any(expected_suppressed_output == content for content in contents)


def test_clean_prompt_builder_uses_chat_mode_branch_and_output_format():
    render = lambda tmpl, char, user: tmpl.replace("{{char}}", char).replace(
        "{{user}}", user or ""
    )
    deps = PromptAssemblyDeps(
        render_prompt=render,
        lookup_prompt_override=lambda *_: None,
        is_christmas_prompt_enabled=lambda: False,
    )
    context = AgentPromptContext(
        agent_id="agent-chat-mode-1",
        name="Nova",
        main_prompt="purity_main_0725",
        mode_prompt="purity_mode_0725",
    )
    request = PromptBuildInput(
        user_profile="Name: Alex",
        chat_settings=ChatSettingsSnapshot(
            chat_mode="rp_mode_1225",
            premium_mode=False,
        ),
        include_output_format_prompt=True,
    )

    messages = build_system_messages(context=context, request=request, deps=deps)
    contents = _contents(messages)
    selected_mode = render(
        prompts.get_mode_prompt_by_id("rp_mode_1225"), "Nova", "Alex"
    )
    selected_output = render(
        prompts.get_mode_output_format_prompt_by_id("rp_mode_1225"), "Nova", "Alex"
    )
    default_mode = render(
        prompts.get_mode_prompt_by_id("purity_mode_0725"), "Nova", "Alex"
    )
    assert any(content == selected_mode for content in contents)
    assert any(content == selected_output for content in contents)
    assert not any(content == default_mode for content in contents)


def test_clean_prompt_builder_uses_premium_mode_branch():
    render = lambda tmpl, char, user: tmpl.replace("{{char}}", char).replace(
        "{{user}}", user or ""
    )
    deps = PromptAssemblyDeps(
        render_prompt=render,
        lookup_prompt_override=lambda *_: None,
        is_christmas_prompt_enabled=lambda: False,
    )
    context = AgentPromptContext(
        agent_id="agent-premium-1",
        name="Mira",
        main_prompt="purity_main_0725",
        mode_prompt="purity_mode_0725",
    )
    request = PromptBuildInput(
        user_profile="Name: Sam",
        chat_settings=ChatSettingsSnapshot(chat_mode=None, premium_mode=True),
        include_output_format_prompt=True,
    )

    messages = build_system_messages(context=context, request=request, deps=deps)
    contents = _contents(messages)
    premium_mode = render(prompts.ROMANTIC_ROLEPLAY_PROMPT.mode_prompt, "Mira", "Sam")
    premium_output = render(
        prompts.ROMANTIC_ROLEPLAY_PROMPT.output_format_prompt, "Mira", "Sam"
    )
    assert any(content == premium_mode for content in contents)
    assert any(content == premium_output for content in contents)


def test_clean_prompt_builder_excludes_time_context_when_disabled():
    deps = PromptAssemblyDeps(
        render_prompt=lambda tmpl, char, user: tmpl,
        lookup_prompt_override=lambda *_: None,
        is_christmas_prompt_enabled=lambda: False,
    )
    context = AgentPromptContext(agent_id="agent-time-1", name="TimeAgent")
    request = PromptBuildInput(
        user_profile="Name: Quinn",
        user_time_context=UserTimeContextSnapshot(
            local_time="2026-02-05T18:30:00",
            timezone="Asia/Shanghai",
            utc_offset_minutes=480,
        ),
    )
    messages = build_system_messages(context=context, request=request, deps=deps)
    assert not any(
        "##User Time Context" in (content or "") for content in _contents(messages)
    )


def test_clean_prompt_builder_includes_christmas_prompts_when_enabled():
    deps = PromptAssemblyDeps(
        render_prompt=lambda tmpl, char, user: tmpl.replace("{{char}}", char).replace(
            "{{user}}", user or ""
        ),
        lookup_prompt_override=lambda *_: None,
        is_christmas_prompt_enabled=lambda: True,
    )
    context = AgentPromptContext(
        agent_id="agent-xmas-1",
        name="Carol",
        personality="Gentle and warm.",
    )
    request = PromptBuildInput(user_profile="Name: Pat")
    messages = build_system_messages(context=context, request=request, deps=deps)
    contents = _contents(messages)
    assert any(
        content.startswith("##Seasonal Behavior (Christmas Week")
        for content in contents
    )
    assert any(
        content.startswith("##Temporal Context – Christmas Week")
        for content in contents
    )


def test_clean_official_builder_always_appends_introduction_message():
    deps = PromptAssemblyDeps(
        render_prompt=lambda tmpl, char, user: tmpl,
        lookup_prompt_override=lambda *_: None,
        is_christmas_prompt_enabled=lambda: False,
    )
    context = AgentPromptContext(
        agent_id=INTELLIMATE_AGENT_ID,
        name=INTELLIMATE_AGENT_NAME,
        intro="",
    )
    messages = build_system_messages_for_chat(
        context=context,
        request=PromptBuildInput(user_profile="Name: OfficialUser"),
        deps=deps,
    )
    assert any(
        content.startswith("##Introduction The following Introduction")
        for content in _contents(messages)
    )


def test_clean_tool_loop_round_limit_exceeded_raises():
    initial_response = ChatCompletionSnapshot(
        choices=[
            ChatCompletionChoiceSnapshot(
                message=AssistantMessageSnapshot(
                    content="Still calling tool.",
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

    def continue_chat(_messages):
        return initial_response

    with pytest.raises(ValueError, match="exceeded limit"):
        resolve_official_assistant_tool_calls(
            request=OfficialAssistantToolLoopInput(
                response=initial_response,
                openai_messages=[
                    OpenAIChatMessageSnapshot(role="user", content="loop")
                ],
                user_id="user-1",
            ),
            continue_chat=continue_chat,
        )


def test_clean_tool_loop_unsupported_tool_returns_tool_message():
    initial_response = ChatCompletionSnapshot(
        choices=[
            ChatCompletionChoiceSnapshot(
                message=AssistantMessageSnapshot(
                    content="Calling unsupported tool.",
                    tool_calls=[
                        AssistantToolCall(
                            id="tool-call-1",
                            function=AssistantToolCallFunction(
                                name="unknown_tool",
                                arguments="{}",
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
                message=AssistantMessageSnapshot(
                    content="Fallback answer.", tool_calls=[]
                ),
                finish_reason="stop",
            )
        ]
    )
    captured: dict[str, list[dict]] = {}

    def continue_chat(messages):
        captured["messages"] = openai_dicts_from_messages(messages)
        return final_response

    output = resolve_official_assistant_tool_calls(
        request=OfficialAssistantToolLoopInput(
            response=initial_response,
            openai_messages=[OpenAIChatMessageSnapshot(role="user", content="Hi")],
            user_id="user-1",
        ),
        continue_chat=continue_chat,
    )

    assert output.response == final_response
    assert output.side_effects == []
    assert any(
        message["role"] == "tool"
        and message["content"] == "Unsupported tool: unknown_tool"
        for message in captured["messages"]
    )


def test_clean_tool_loop_inserts_loaded_manual_after_existing_system_messages():
    initial_response = ChatCompletionSnapshot(
        choices=[
            ChatCompletionChoiceSnapshot(
                message=AssistantMessageSnapshot(
                    content="Need manual first.",
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
    final_response = ChatCompletionSnapshot(
        choices=[
            ChatCompletionChoiceSnapshot(
                message=AssistantMessageSnapshot(content="Done", tool_calls=[]),
                finish_reason="stop",
            )
        ]
    )
    captured: dict[str, list[dict]] = {}

    def continue_chat(messages):
        captured["messages"] = openai_dicts_from_messages(messages)
        return final_response

    resolve_official_assistant_tool_calls(
        request=OfficialAssistantToolLoopInput(
            response=initial_response,
            openai_messages=[
                OpenAIChatMessageSnapshot(role="system", content="BASE_SYSTEM"),
                OpenAIChatMessageSnapshot(role="user", content="How to use app?"),
            ],
            user_id="user-1",
        ),
        continue_chat=continue_chat,
        deps=OfficialAssistantToolDeps(
            load_user_manual=lambda: "MANUAL_ABC",
            load_change_logs=lambda: "CHANGE_ABC",
        ),
    )

    messages = captured["messages"]
    assert messages[0] == {"role": "system", "content": "BASE_SYSTEM"}
    assert messages[1]["role"] == "system"
    assert messages[1]["content"].startswith("##IntelliMate User Manual\nMANUAL_ABC")
    assert messages[2] == {"role": "user", "content": "How to use app?"}


def test_execute_official_assistant_tool_call_rejects_invalid_mbti_payloads():
    with pytest.raises(ValueError, match="invalid JSON arguments"):
        execute_official_assistant_tool_call(
            tool_name=OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME,
            raw_arguments="{",
            user_id="user-1",
        )

    with pytest.raises(ValueError, match="requires string field mbti_type"):
        execute_official_assistant_tool_call(
            tool_name=OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME,
            raw_arguments='{"mbti_type": 123}',
            user_id="user-1",
        )

    with pytest.raises(ValueError, match="Invalid MBTI type"):
        execute_official_assistant_tool_call(
            tool_name=OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME,
            raw_arguments='{"mbti_type":"ABCD"}',
            user_id="user-1",
        )


def test_chat_completion_snapshot_from_openai_response_maps_tool_calls():
    raw_function = SimpleNamespace(
        name=OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME, arguments="{}"
    )
    raw_tool_call = SimpleNamespace(id="tc-1", type="function", function=raw_function)
    raw_message = SimpleNamespace(
        content="I will call a tool.", tool_calls=[raw_tool_call]
    )
    raw_choice = SimpleNamespace(message=raw_message, finish_reason="tool_calls")
    raw_response = SimpleNamespace(choices=[raw_choice])

    snapshot = chat_completion_snapshot_from_openai_response(raw_response)
    assert len(snapshot.choices) == 1
    assert snapshot.choices[0].message.content == "I will call a tool."
    assert len(snapshot.choices[0].message.tool_calls) == 1
    assert snapshot.choices[0].message.tool_calls[0].id == "tc-1"
    assert (
        snapshot.choices[0].message.tool_calls[0].function.name
        == OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME
    )


def test_openai_dicts_from_messages_keeps_tool_fields():
    messages = [
        OpenAIChatMessageSnapshot(
            role="assistant", content="Tool calling...", tool_calls=[]
        ),
        OpenAIChatMessageSnapshot(
            role="tool", tool_call_id="tc-1", content="Tool result"
        ),
    ]
    payload = openai_dicts_from_messages(messages)
    assert payload[0] == {"role": "assistant", "content": "Tool calling..."}
    assert payload[1] == {
        "role": "tool",
        "tool_call_id": "tc-1",
        "content": "Tool result",
    }
