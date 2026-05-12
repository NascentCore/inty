"""
Review-only clean agent prompt system.

Design goals:
1) Keep behavior parity with the current Agent prompt assembly/tool-loop behavior.
2) Keep agent loop code free of direct DB access.
3) Use structured types + explicit dependency passing at function boundaries.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Literal, Optional, Sequence, TypeAlias

from langchain_core.messages import SystemMessage
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.api.types.llm_config import LLMConfig
from app.core.agent import prompt_template
from app.core.agent.agent import (
    CHRISTMAS_SEASONAL_BEHAVIOR_PROMPT,
    CHRISTMAS_TEMPORAL_CONTEXT_PROMPT,
    INTELLIMATE_AGENT_ID,
    INTELLIMATE_CHANGE_LOGS_SYSTEM_MESSAGE_PREFIX,
    INTELLIMATE_OFFICIAL_RENAME_SYSTEM_MESSAGE,
    INTELLIMATE_USER_MANUAL_SYSTEM_MESSAGE_PREFIX,
    INTELLIMATE_USER_MANUAL_TOOL_USAGE_SYSTEM_MESSAGE,
    OFFICIAL_ASSISTANT_MAX_TOOL_CALL_ROUNDS,
    OFFICIAL_ASSISTANT_READ_CHANGE_LOGS_TOOL_NAME,
    OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME,
    OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME,
    _load_intellimate_change_logs,
    _load_intellimate_user_manual,
)
from app.core.agent.agent_prompt_configs import get_agent_prompt_override
from app.core.agentic_kernel.prompting.assembler import (
    PromptAssemblerConfig,
    PromptAssemblerDeps,
    build_system_messages as build_system_messages_with_assembler,
    build_system_messages_for_chat as build_system_messages_for_chat_with_assembler,
    build_system_messages_for_official_assistant as build_system_messages_for_official_assistant_with_assembler,
)
from app.core.config import (
    global_config_loaded_from_config_yaml as global_config,
)
from app.schemas.user import UserMetadata


def _render_prompt(*, tmpl: str, char: str, user: Optional[str]) -> str:
    return prompt_template.render_prompt_jinja2_template(
        tmpl=tmpl, char=char, user=user
    )


def _is_christmas_prompt_enabled() -> bool:
    return bool(global_config.agent.enable_christmas_prompt)


class AgentRuntimeSettings(BaseModel):
    """
    Structured runtime settings.

    `legacy_llm_config` keeps backward-compatible read path for old `model_config` key.
    """

    llm_config: Optional[LLMConfig] = None
    legacy_llm_config: Optional[LLMConfig] = Field(default=None, alias="model_config")

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    def resolve_llm_config(self) -> Optional[LLMConfig]:
        if self.llm_config is not None:
            return self.llm_config
        return self.legacy_llm_config


class AgentPromptContext(BaseModel):
    agent_id: str
    name: str
    settings: Optional[AgentRuntimeSettings] = None
    main_prompt: str = ""
    mode_prompt: str = ""
    output_format_prompt: str = ""
    personality: str = ""
    scenario: str = ""
    message_example: str = ""
    creator_notes: str = ""
    tags: list[str] = Field(default_factory=list)
    character_version: str = "1.0"
    extensions: dict[str, Any] = Field(default_factory=dict)
    intro: str = ""

    def resolved_llm_config(self) -> Optional[LLMConfig]:
        if self.settings is None:
            return None
        return self.settings.resolve_llm_config()

    @classmethod
    def from_legacy_agent_data(
        cls, *, agent_id: str, agent_data: dict[str, Any]
    ) -> "AgentPromptContext":
        settings_raw = agent_data.get("settings")
        settings = None
        if settings_raw is not None:
            if not isinstance(settings_raw, dict):
                raise ValueError(
                    f"agent_data.settings must be an object, got {type(settings_raw).__name__}"
                )
            settings = AgentRuntimeSettings.model_validate(settings_raw)
        return cls(
            agent_id=agent_id,
            name=agent_data.get("name", f"Agent_{agent_id[:8]}"),
            settings=settings,
            main_prompt=agent_data.get("main_prompt", "") or "",
            mode_prompt=agent_data.get("mode_prompt", "") or "",
            output_format_prompt=agent_data.get("output_format_prompt", "") or "",
            personality=agent_data.get("personality", "") or "",
            scenario=agent_data.get("scenario", "") or "",
            message_example=agent_data.get("message_example", "") or "",
            creator_notes=agent_data.get("creator_notes", "") or "",
            tags=list(agent_data.get("tags", []) or []),
            character_version=agent_data.get("character_version", "1.0") or "1.0",
            extensions=dict(agent_data.get("extensions", {}) or {}),
            intro=agent_data.get("intro", "") or "",
        )


class ChatSettingsSnapshot(BaseModel):
    style_prompt: Optional[str] = None
    premium_mode: bool = False
    chat_mode: Optional[str] = None


class UserTimeContextSnapshot(BaseModel):
    local_time: Optional[str] = None
    timezone: Optional[str] = None
    utc_offset_minutes: Optional[int] = None

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class PromptBuildInput(BaseModel):
    user_profile: str = ""
    chat_settings: Optional[ChatSettingsSnapshot] = None
    user_time_context: Optional[UserTimeContextSnapshot] = None
    include_output_format_prompt: bool = True


RenderPromptFn: TypeAlias = Callable[[str, str, Optional[str]], str]
PromptOverrideLookupFn: TypeAlias = Callable[[str, str], Any]


@dataclass(frozen=True)
class PromptAssemblyDeps:
    render_prompt: RenderPromptFn = lambda tmpl, char, user: _render_prompt(
        tmpl=tmpl, char=char, user=user
    )
    lookup_prompt_override: PromptOverrideLookupFn = get_agent_prompt_override
    is_christmas_prompt_enabled: Callable[[], bool] = _is_christmas_prompt_enabled


DEFAULT_PROMPT_ASSEMBLY_DEPS = PromptAssemblyDeps()


def _build_prompt_assembler_config() -> PromptAssemblerConfig:
    return PromptAssemblerConfig(
        official_agent_id=INTELLIMATE_AGENT_ID,
        force_default_prompts=bool(global_config.agent.force_default_prompts),
        christmas_seasonal_behavior_prompt=CHRISTMAS_SEASONAL_BEHAVIOR_PROMPT,
        christmas_temporal_context_prompt=CHRISTMAS_TEMPORAL_CONTEXT_PROMPT,
        official_rename_system_message=INTELLIMATE_OFFICIAL_RENAME_SYSTEM_MESSAGE,
        official_tool_usage_system_message=INTELLIMATE_USER_MANUAL_TOOL_USAGE_SYSTEM_MESSAGE,
    )


def _to_assembler_deps(deps: PromptAssemblyDeps) -> PromptAssemblerDeps:
    return PromptAssemblerDeps(
        render_prompt=deps.render_prompt,
        lookup_prompt_override=deps.lookup_prompt_override,
        is_christmas_prompt_enabled=deps.is_christmas_prompt_enabled,
    )


def build_system_messages(
    *,
    context: AgentPromptContext,
    request: PromptBuildInput,
    deps: PromptAssemblyDeps = DEFAULT_PROMPT_ASSEMBLY_DEPS,
) -> list[SystemMessage]:
    return build_system_messages_with_assembler(
        context=context,
        request=request,
        deps=_to_assembler_deps(deps),
        config=_build_prompt_assembler_config(),
    )


def build_system_messages_for_official_assistant(
    *,
    context: AgentPromptContext,
    request: PromptBuildInput,
    deps: PromptAssemblyDeps = DEFAULT_PROMPT_ASSEMBLY_DEPS,
) -> list[SystemMessage]:
    return build_system_messages_for_official_assistant_with_assembler(
        context=context,
        request=request,
        deps=_to_assembler_deps(deps),
        config=_build_prompt_assembler_config(),
    )


def build_system_messages_for_chat(
    *,
    context: AgentPromptContext,
    request: PromptBuildInput,
    deps: PromptAssemblyDeps = DEFAULT_PROMPT_ASSEMBLY_DEPS,
) -> list[SystemMessage]:
    return build_system_messages_for_chat_with_assembler(
        context=context,
        request=request,
        deps=_to_assembler_deps(deps),
        config=_build_prompt_assembler_config(),
    )


class AssistantToolCallFunction(BaseModel):
    name: str
    arguments: str = ""


class AssistantToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: AssistantToolCallFunction


class AssistantMessageSnapshot(BaseModel):
    content: Optional[str] = None
    tool_calls: list[AssistantToolCall] = Field(default_factory=list)


class ChatCompletionChoiceSnapshot(BaseModel):
    message: AssistantMessageSnapshot
    finish_reason: Optional[str] = None


class ChatCompletionSnapshot(BaseModel):
    choices: list[ChatCompletionChoiceSnapshot]


class OpenAIChatMessageSnapshot(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: list[AssistantToolCall] = Field(default_factory=list)

    def to_openai_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            payload["content"] = self.content
        if self.tool_call_id is not None:
            payload["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            payload["tool_calls"] = [tc.model_dump() for tc in self.tool_calls]
        return payload


def openai_dicts_from_messages(
    messages: Sequence[OpenAIChatMessageSnapshot],
) -> list[dict[str, Any]]:
    return [message.to_openai_dict() for message in messages]


class SaveUserMbtiSideEffect(BaseModel):
    kind: Literal["save_user_mbti_type"] = "save_user_mbti_type"
    user_id: str
    mbti_type: str


OfficialAssistantSideEffect: TypeAlias = SaveUserMbtiSideEffect


class OfficialAssistantToolExecutionResult(BaseModel):
    tool_result: str
    injected_system_message: Optional[str] = None
    side_effects: list[OfficialAssistantSideEffect] = Field(default_factory=list)


class OfficialAssistantToolLoopInput(BaseModel):
    response: ChatCompletionSnapshot
    openai_messages: list[OpenAIChatMessageSnapshot]
    user_id: str


class OfficialAssistantToolLoopOutput(BaseModel):
    response: ChatCompletionSnapshot
    openai_messages: list[OpenAIChatMessageSnapshot]
    side_effects: list[OfficialAssistantSideEffect]


ContinuationFn: TypeAlias = Callable[
    [Sequence[OpenAIChatMessageSnapshot]], ChatCompletionSnapshot
]


@dataclass(frozen=True)
class OfficialAssistantToolDeps:
    load_user_manual: Callable[[], str] = _load_intellimate_user_manual
    load_change_logs: Callable[[], str] = _load_intellimate_change_logs


DEFAULT_OFFICIAL_ASSISTANT_TOOL_DEPS = OfficialAssistantToolDeps()


def _parse_mbti_type_from_tool_arguments(raw_arguments: str) -> str:
    try:
        parsed_arguments = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError as e:
        raise ValueError(
            f"{OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME} received invalid JSON arguments"
        ) from e
    mbti_type_raw = parsed_arguments.get("mbti_type")
    if not isinstance(mbti_type_raw, str):
        raise ValueError(
            f"{OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME} requires string field mbti_type"
        )
    try:
        metadata = UserMetadata(mbti_type=mbti_type_raw)
    except ValidationError as e:
        raise ValueError(f"Invalid MBTI type: {mbti_type_raw}") from e
    if not metadata.mbti_type:
        raise ValueError(
            f"{OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME} requires non-empty mbti_type"
        )
    return metadata.mbti_type


def execute_official_assistant_tool_call(
    *,
    tool_name: str,
    raw_arguments: str,
    user_id: str,
    deps: OfficialAssistantToolDeps = DEFAULT_OFFICIAL_ASSISTANT_TOOL_DEPS,
) -> OfficialAssistantToolExecutionResult:
    if tool_name == OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME:
        mbti_type = _parse_mbti_type_from_tool_arguments(raw_arguments)
        return OfficialAssistantToolExecutionResult(
            tool_result=f"Saved MBTI type: {mbti_type}",
            side_effects=[SaveUserMbtiSideEffect(user_id=user_id, mbti_type=mbti_type)],
        )
    if tool_name == OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME:
        manual_content = deps.load_user_manual()
        return OfficialAssistantToolExecutionResult(
            tool_result="Loaded IntelliMate user manual into system context.",
            injected_system_message=INTELLIMATE_USER_MANUAL_SYSTEM_MESSAGE_PREFIX
            + manual_content,
        )
    if tool_name == OFFICIAL_ASSISTANT_READ_CHANGE_LOGS_TOOL_NAME:
        change_logs = deps.load_change_logs()
        return OfficialAssistantToolExecutionResult(
            tool_result="Loaded IntelliMate change logs into system context.",
            injected_system_message=INTELLIMATE_CHANGE_LOGS_SYSTEM_MESSAGE_PREFIX
            + change_logs,
        )
    return OfficialAssistantToolExecutionResult(
        tool_result=f"Unsupported tool: {tool_name}"
    )


def _build_assistant_tool_call_message(
    assistant_message: AssistantMessageSnapshot,
) -> OpenAIChatMessageSnapshot:
    return OpenAIChatMessageSnapshot(
        role="assistant",
        content=assistant_message.content or "",
        tool_calls=assistant_message.tool_calls,
    )


def _insert_system_message_into_messages(
    *,
    openai_messages: list[OpenAIChatMessageSnapshot],
    system_message_content: str,
) -> None:
    insertion_index = 0
    while (
        insertion_index < len(openai_messages)
        and openai_messages[insertion_index].role == "system"
    ):
        insertion_index += 1
    openai_messages.insert(
        insertion_index,
        OpenAIChatMessageSnapshot(role="system", content=system_message_content),
    )


def resolve_official_assistant_tool_calls(
    *,
    request: OfficialAssistantToolLoopInput,
    continue_chat: ContinuationFn,
    deps: OfficialAssistantToolDeps = DEFAULT_OFFICIAL_ASSISTANT_TOOL_DEPS,
) -> OfficialAssistantToolLoopOutput:
    messages_with_tool_results = [*request.openai_messages]
    current_response = request.response
    side_effects: list[OfficialAssistantSideEffect] = []

    for _ in range(OFFICIAL_ASSISTANT_MAX_TOOL_CALL_ROUNDS):
        current_message = current_response.choices[0].message
        tool_calls = current_message.tool_calls
        if not tool_calls:
            return OfficialAssistantToolLoopOutput(
                response=current_response,
                openai_messages=messages_with_tool_results,
                side_effects=side_effects,
            )

        messages_with_tool_results.append(
            _build_assistant_tool_call_message(current_message)
        )
        for tool_call in tool_calls:
            execution_result = execute_official_assistant_tool_call(
                tool_name=tool_call.function.name,
                raw_arguments=tool_call.function.arguments or "",
                user_id=request.user_id,
                deps=deps,
            )
            side_effects.extend(execution_result.side_effects)
            messages_with_tool_results.append(
                OpenAIChatMessageSnapshot(
                    role="tool",
                    tool_call_id=tool_call.id,
                    content=execution_result.tool_result,
                )
            )
            if execution_result.injected_system_message:
                _insert_system_message_into_messages(
                    openai_messages=messages_with_tool_results,
                    system_message_content=execution_result.injected_system_message,
                )
        current_response = continue_chat(messages_with_tool_results)

    raise ValueError(
        f"Official assistant tool call rounds exceeded limit={OFFICIAL_ASSISTANT_MAX_TOOL_CALL_ROUNDS}"
    )


def chat_completion_snapshot_from_openai_response(
    response: Any,
) -> ChatCompletionSnapshot:
    raw_choices = getattr(response, "choices", None) or []
    choices: list[ChatCompletionChoiceSnapshot] = []
    for raw_choice in raw_choices:
        raw_message = getattr(raw_choice, "message", None)
        if raw_message is None:
            continue
        raw_tool_calls = getattr(raw_message, "tool_calls", None) or []
        tool_calls = [
            AssistantToolCall(
                id=getattr(raw_tool_call, "id"),
                type=getattr(raw_tool_call, "type", "function"),
                function=AssistantToolCallFunction(
                    name=getattr(raw_tool_call.function, "name"),
                    arguments=getattr(raw_tool_call.function, "arguments", "") or "",
                ),
            )
            for raw_tool_call in raw_tool_calls
        ]
        choices.append(
            ChatCompletionChoiceSnapshot(
                message=AssistantMessageSnapshot(
                    content=getattr(raw_message, "content", None), tool_calls=tool_calls
                ),
                finish_reason=getattr(raw_choice, "finish_reason", None),
            )
        )
    if not choices:
        raise ValueError("LLM returned no choices")
    return ChatCompletionSnapshot(choices=choices)
