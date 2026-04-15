from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

from langchain_core.messages import SystemMessage

from app.core.agent import prompts
from app.core.agentic_kernel.companion.workspace import get_imate_axiom_system_text

RenderPromptFn = Callable[[str, str, Optional[str]], str]
PromptOverrideLookupFn = Callable[[str, str], Any]
BuildUserTimeContextPromptFn = Callable[[dict[str, Any]], Optional[str]]


@dataclass(frozen=True)
class PromptAssemblerDeps:
    render_prompt: RenderPromptFn
    lookup_prompt_override: PromptOverrideLookupFn
    is_user_time_context_enabled: Callable[[], bool]
    is_christmas_prompt_enabled: Callable[[], bool]
    build_user_time_context_prompt: BuildUserTimeContextPromptFn


@dataclass(frozen=True)
class PromptAssemblerConfig:
    official_agent_id: str
    force_default_prompts: bool
    christmas_seasonal_behavior_prompt: str
    christmas_temporal_context_prompt: str
    official_rename_system_message: str
    official_tool_usage_system_message: str
    intro_system_message_prefix: str = (
        "##Introduction The following Introduction is a text for {{user}}, "
        "used only to provide background: \n"
    )


def _extract_user_name_from_profile(user_profile: str) -> Optional[str]:
    if not user_profile:
        return None
    try:
        name_match = re.search(r"Name:\s*([^\n]+)", user_profile)
        if name_match:
            return name_match.group(1).strip()
        chinese_name_match = re.search(r"[名字|姓名]\s*[:=：]\s*([^\n]+)", user_profile)
        if chinese_name_match:
            return chinese_name_match.group(1).strip()
    except (AttributeError, TypeError):
        return None
    return None


def _is_official_assistant(*, context: Any, config: PromptAssemblerConfig) -> bool:
    return context.agent_id == config.official_agent_id


def _axiom_system_messages_prefix() -> list[SystemMessage]:
    axiom = get_imate_axiom_system_text()
    if not axiom:
        return []
    return [SystemMessage(content=axiom)]


def _get_effective_main_prompt(
    *, context: Any, deps: PromptAssemblerDeps, config: PromptAssemblerConfig
) -> str:
    override = deps.lookup_prompt_override(context.agent_id, context.name)
    if override is not None and override.main_prompt is not None:
        return override.main_prompt
    if config.force_default_prompts:
        return prompts.PURITY_ROLEPLAY_PROMPT.main_prompt
    if context.main_prompt:
        try:
            return prompts.get_main_prompt_by_id(context.main_prompt)
        except ValueError:
            return context.main_prompt
    return prompts.ROMANTIC_ROLEPLAY_PROMPT.main_prompt


def _get_effective_mode_prompt(
    *, context: Any, deps: PromptAssemblerDeps, config: PromptAssemblerConfig
) -> str:
    override = deps.lookup_prompt_override(context.agent_id, context.name)
    if override is not None and override.mode_prompt is not None:
        return override.mode_prompt
    if config.force_default_prompts:
        return prompts.PURITY_ROLEPLAY_PROMPT.mode_prompt
    if context.mode_prompt:
        try:
            return prompts.get_mode_prompt_by_id(context.mode_prompt)
        except ValueError:
            return context.mode_prompt
    return prompts.ROMANTIC_ROLEPLAY_PROMPT.mode_prompt


def _get_effective_output_format_prompt(context: Any) -> str:
    if context.output_format_prompt:
        return context.output_format_prompt
    if context.mode_prompt:
        try:
            return prompts.get_mode_output_format_prompt_by_id(context.mode_prompt)
        except ValueError:
            return ""
    return prompts.ROMANTIC_ROLEPLAY_PROMPT.output_format_prompt


def _build_character_context(
    *,
    context: Any,
    user_name: Optional[str],
    deps: PromptAssemblerDeps,
    config: PromptAssemblerConfig,
) -> list[SystemMessage]:
    context_messages: list[SystemMessage] = []
    if context.personality:
        rendered = deps.render_prompt(context.personality, context.name, user_name)
        context_messages.append(SystemMessage(content=rendered))
    if context.scenario:
        rendered = deps.render_prompt(context.scenario, context.name, user_name)
        context_messages.append(SystemMessage(content=rendered))
    if context.message_example:
        rendered = deps.render_prompt(context.message_example, context.name, user_name)
        context_messages.append(SystemMessage(content=rendered))
    if deps.is_christmas_prompt_enabled():
        rendered = deps.render_prompt(
            config.christmas_seasonal_behavior_prompt,
            context.name,
            user_name,
        )
        context_messages.append(SystemMessage(content=rendered))
    return context_messages


def build_system_messages(
    *,
    context: Any,
    request: Any,
    deps: PromptAssemblerDeps,
    config: PromptAssemblerConfig,
) -> list[SystemMessage]:
    user_name = _extract_user_name_from_profile(request.user_profile)
    system_messages: list[SystemMessage] = []
    system_messages.extend(_axiom_system_messages_prefix())

    main_prompt = _get_effective_main_prompt(context=context, deps=deps, config=config)
    if main_prompt:
        rendered_main_prompt = deps.render_prompt(main_prompt, context.name, user_name)
        system_messages.append(SystemMessage(content=rendered_main_prompt))

    system_messages.extend(
        _build_character_context(
            context=context,
            user_name=user_name,
            deps=deps,
            config=config,
        )
    )

    override = deps.lookup_prompt_override(context.agent_id, context.name)
    chat_settings = request.chat_settings
    if override is not None and override.mode_prompt is not None:
        mode_prompt = override.mode_prompt
        output_format_prompt = ""
    elif (
        chat_settings
        and chat_settings.chat_mode
        and chat_settings.chat_mode in prompts.USER_FACING_CHAT_MODE_IDS
    ):
        mode_prompt = prompts.get_mode_prompt_by_id(chat_settings.chat_mode)
        output_format_prompt = prompts.get_mode_output_format_prompt_by_id(
            chat_settings.chat_mode
        )
    elif chat_settings and chat_settings.premium_mode:
        mode_prompt = prompts.ROMANTIC_ROLEPLAY_PROMPT.mode_prompt
        output_format_prompt = prompts.ROMANTIC_ROLEPLAY_PROMPT.output_format_prompt
    else:
        mode_prompt = _get_effective_mode_prompt(
            context=context,
            deps=deps,
            config=config,
        )
        output_format_prompt = _get_effective_output_format_prompt(context)

    if mode_prompt:
        rendered_mode_prompt = deps.render_prompt(mode_prompt, context.name, user_name)
        system_messages.append(SystemMessage(content=rendered_mode_prompt))
    if request.include_output_format_prompt and output_format_prompt:
        rendered_output_prompt = deps.render_prompt(
            output_format_prompt,
            context.name,
            user_name,
        )
        system_messages.append(SystemMessage(content=rendered_output_prompt))

    if chat_settings and chat_settings.style_prompt:
        system_messages.append(SystemMessage(content=chat_settings.style_prompt))

    if request.user_profile:
        system_messages.append(SystemMessage(content=request.user_profile))

    if request.user_time_context and deps.is_user_time_context_enabled():
        prompt = deps.build_user_time_context_prompt(
            request.user_time_context.to_runtime_dict()
        )
        if prompt:
            system_messages.append(SystemMessage(content=prompt))

    if deps.is_christmas_prompt_enabled():
        rendered_temporal_prompt = deps.render_prompt(
            config.christmas_temporal_context_prompt,
            context.name,
            user_name,
        )
        system_messages.append(SystemMessage(content=rendered_temporal_prompt))

    if context.intro:
        system_messages.append(
            SystemMessage(
                content=config.intro_system_message_prefix + context.intro,
            )
        )

    if _is_official_assistant(context=context, config=config):
        system_messages.append(
            SystemMessage(content=config.official_rename_system_message)
        )
        system_messages.append(
            SystemMessage(content=config.official_tool_usage_system_message)
        )

    return system_messages


def build_system_messages_for_official_assistant(
    *,
    context: Any,
    request: Any,
    deps: PromptAssemblerDeps,
    config: PromptAssemblerConfig,
) -> list[SystemMessage]:
    user_name = _extract_user_name_from_profile(request.user_profile)
    system_messages: list[SystemMessage] = []
    system_messages.extend(_axiom_system_messages_prefix())

    system_messages.extend(
        _build_character_context(
            context=context,
            user_name=user_name,
            deps=deps,
            config=config,
        )
    )
    if request.chat_settings and request.chat_settings.style_prompt:
        system_messages.append(
            SystemMessage(content=request.chat_settings.style_prompt)
        )
    if request.user_profile:
        system_messages.append(SystemMessage(content=request.user_profile))

    if request.user_time_context and deps.is_user_time_context_enabled():
        prompt = deps.build_user_time_context_prompt(
            request.user_time_context.to_runtime_dict()
        )
        if prompt:
            system_messages.append(SystemMessage(content=prompt))

    if deps.is_christmas_prompt_enabled():
        rendered_temporal_prompt = deps.render_prompt(
            config.christmas_temporal_context_prompt,
            context.name,
            user_name,
        )
        system_messages.append(SystemMessage(content=rendered_temporal_prompt))

    system_messages.append(
        SystemMessage(
            content=config.intro_system_message_prefix + context.intro,
        )
    )
    system_messages.append(SystemMessage(content=config.official_rename_system_message))
    system_messages.append(
        SystemMessage(content=config.official_tool_usage_system_message)
    )
    return system_messages


def build_system_messages_for_chat(
    *,
    context: Any,
    request: Any,
    deps: PromptAssemblerDeps,
    config: PromptAssemblerConfig,
) -> list[SystemMessage]:
    if _is_official_assistant(context=context, config=config):
        return build_system_messages_for_official_assistant(
            context=context,
            request=request,
            deps=deps,
            config=config,
        )
    return build_system_messages(
        context=context,
        request=request,
        deps=deps,
        config=config,
    )
