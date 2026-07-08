from __future__ import annotations

import inspect

from app.core.companion_harness.companion.models import (
    OUTPUT_FORMAT_IM_DM_MD,
    ContextMeta,
    InnerTickActivity,
)
from app.core.companion_harness.experience_profile.experience_directives import (
    ExperienceDirectiveTone,
    ExperienceDirectives,
    ExperienceSessionIntent,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.prompting.tracks import (
    build_settled_user_turn_dual_chat_leg_system_messages,
)
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
    build_system_messages_for_inner_tick_autonomy,
    build_system_messages_for_inner_tick_monolog,
    build_system_messages_for_tool_track,
)
from app.core.companion_harness.prompt_builder import PromptBuilder
from app.core.companion_harness.companion.prompt_stack import (
    append_runtime_output_format_system_message,
    output_format_prompt_slice_for_runtime_channel,
)
from app.core.companion_harness.memory.memory_store_scope import (
    load_template_seed_text,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)


def test_doctrine_system_prefix_excludes_subconscious_prompt() -> None:
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )
    messages = build_system_messages(bundle, ContextMeta())
    doctrine_lines = [
        str(messages[index]["content"]).split("\n")[0] for index in range(3)
    ]

    assert doctrine_lines == [
        "# Axiom - 你存在的根本法则",
        "# Inty - AI agents as human companions",
        "# Safety - 安全预防",
    ]
    assert all(
        "SUBCONSCIOUS" not in str(message["content"]) for message in messages
    )


def test_contextual_messages_include_infer_time_zone_slice_with_tool_name() -> (
    None
):
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )
    messages = build_settled_user_turn_dual_chat_leg_system_messages(
        bundle,
        ContextMeta(),
    )
    joined = "\n".join(
        str(m["content"]) for m in messages if m["role"] == "system"
    )
    assert "用户当地时间与作息" in joined
    assert "update_user_md" in joined
    assert "Asia/Shanghai" in joined


def test_contextual_messages_include_experience_directives_when_tone_set() -> (
    None
):
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )
    messages = build_settled_user_turn_dual_chat_leg_system_messages(
        bundle,
        ContextMeta(
            context_mode="intimate",
            experience_directives=ExperienceDirectives(
                intent=ExperienceSessionIntent.DEEP_CONVERSATION,
                tone=ExperienceDirectiveTone.WARM,
            ),
        ),
    )
    joined = "\n".join(
        str(m["content"]) for m in messages if m["role"] == "system"
    )
    assert "EXPERIENCE DIRECTIVES" in joined
    assert "deep_conversation" in joined
    assert "warm" in joined


def test_contextual_messages_include_experience_directives_when_intent_only() -> (
    None
):
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )
    messages = build_settled_user_turn_dual_chat_leg_system_messages(
        bundle,
        ContextMeta(
            context_mode="emotional_companion",
            experience_directives=ExperienceDirectives(
                intent=ExperienceSessionIntent.CASUAL_CHAT,
            ),
        ),
    )
    joined = "\n".join(
        str(m["content"]) for m in messages if m["role"] == "system"
    )
    assert "EXPERIENCE DIRECTIVES" in joined
    assert "casual_chat" in joined
    assert "语气细调" not in joined


def test_contextual_messages_omit_experience_directives_when_unset() -> None:
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )
    messages = build_settled_user_turn_dual_chat_leg_system_messages(
        bundle,
        ContextMeta(),
    )
    joined = "\n".join(
        str(m["content"]) for m in messages if m["role"] == "system"
    )
    assert "EXPERIENCE DIRECTIVES" not in joined


def test_inner_tick_monolog_omits_infer_time_zone_slice() -> None:
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )
    messages = build_system_messages(
        bundle,
        ContextMeta(),
        enable_tools=True,
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.MONOLOG,
        ai_private_text="private\n",
        tool_side_compact=True,
    )
    joined = "\n".join(
        str(m["content"]) for m in messages if m["role"] == "system"
    )
    assert "用户当地时间与作息" not in joined


def test_inner_tick_monolog_is_monolog_only_without_ls_tc_or_memory_store() -> (
    None
):
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )
    messages = build_system_messages_for_inner_tick_monolog(
        store=MemoryStore(
            scope=CompanionScope("sm", "a", "monolog-prompt"),
            repository=None,
        ),
        bundle=bundle,
        context=ContextMeta(),
    )
    contents = [str(m["content"]) for m in messages if m["role"] == "system"]
    inner_blocks = [c for c in contents if c.startswith("本轮（内在节拍）")]
    assert len(inner_blocks) == 1
    block = inner_blocks[0]
    assert "ai_private_append" in block
    assert "memory_store_write_document" not in block
    assert "living_sphere_record_update" not in block
    assert "面向用户的正文**必须为空字符串**" in block
    assert any(c.startswith("内在活动（ai_private）") for c in contents)


def test_im_output_format_slice_is_appended_by_runtime_decorator() -> None:
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
        output_format_im_dm_md=load_template_seed_text(OUTPUT_FORMAT_IM_DM_MD),
    )
    messages = build_system_messages(
        bundle,
        ContextMeta(),
        enable_tools=True,
        async_foreground_chat_stack=True,
        include_significance_perception_slice=True,
    )
    messages = append_runtime_output_format_system_message(
        system_messages=messages,
        bundle=bundle,
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.WECHAT_WEIXIN,
            implicit_signal_bundle=None,
        ),
    )
    contents = [str(message["content"]) for message in messages]
    first_lines = [content.split("\n")[0] for content in contents]
    mirrored_tools_index = first_lines.index(
        "## 快思考路径（系统 1）与并行工具路径（系统 2）须一致"
    )
    im_index = first_lines.index("# Output format: IM direct message")
    envelope_index = first_lines.index(
        "## Dual-LLM chat branch: structured reply envelope"
    )

    assert mirrored_tools_index < envelope_index < im_index
    assert contents[im_index].split("\n") == load_template_seed_text(
        OUTPUT_FORMAT_IM_DM_MD
    ).strip().split("\n")
    assert ChannelKind.WECHAT_WEIXIN.value == "wechat_weixin"


def test_output_format_slice_is_runtime_decorator_not_system_builder_argument() -> (
    None
):
    builders = [
        build_system_messages,
        build_settled_user_turn_dual_chat_leg_system_messages,
        build_system_messages_for_tool_track,
        build_system_messages_for_inner_tick_monolog,
        build_system_messages_for_inner_tick_autonomy,
        PromptBuilder.greeting_system_dicts,
        PromptBuilder.proactive_system_dicts,
        PromptBuilder.scheduled_system_dicts,
    ]

    for builder in builders:
        assert (
            "output_format_prompt_slice"
            not in inspect.signature(builder).parameters
        )


def test_output_format_slice_resolves_from_runtime_channel() -> None:
    body = load_template_seed_text(OUTPUT_FORMAT_IM_DM_MD)
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
        output_format_im_dm_md=body,
    )

    assert (
        output_format_prompt_slice_for_runtime_channel(
            bundle=bundle,
            runtime_channel=ChannelKind.WECHAT_WEIXIN,
        )
        == body
    )
    assert (
        output_format_prompt_slice_for_runtime_channel(
            bundle=bundle,
            runtime_channel=ChannelKind.TELEGRAM,
        )
        == body
    )
    assert (
        output_format_prompt_slice_for_runtime_channel(
            bundle=bundle,
            runtime_channel=ChannelKind.APP_WS,
        )
        == ""
    )


def test_autonomy_inner_tick_emits_autonomy_section_and_no_proactive_clause() -> (
    None
):
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )
    messages = build_system_messages(
        bundle,
        ContextMeta(),
        enable_tools=True,
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.AUTONOMY,
        tool_side_compact=True,
    )
    contents = [str(m["content"]) for m in messages]
    autonomy_blocks = [
        c for c in contents if c.startswith("本轮（AUTONOMY 自主活动）")
    ]
    assert len(autonomy_blocks) == 1
    proactive_blocks = [
        c for c in contents if c.startswith("本轮（陪伴主动聊天）")
    ]
    assert proactive_blocks == []
    monolog_blocks = [
        c for c in contents if c.startswith("本轮（内在节拍）")
    ]
    assert monolog_blocks == []
    assert not any(c.startswith("内在活动（ai_private）") for c in contents)
    autonomy_lines = autonomy_blocks[0].split("\n")
    assert (
        "**绝对不向用户发送任何消息。** 面向用户的可见正文必须为空字符串；"
        in autonomy_lines[2]
    )
    assert any("LIFE_CURRENTS.md" in line for line in autonomy_lines)
    autonomy_text = autonomy_blocks[0]
    assert "与 ai_private 分工" in autonomy_text
    assert "禁止写入" in autonomy_text
    assert "成为他的知己" in autonomy_text
    assert "只允许" in autonomy_text and "LIFE_CURRENTS.md" in autonomy_text


def _make_bundle() -> PromptBundle:
    return PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )


def test_build_system_messages_for_inner_tick_autonomy_is_production_builder(
    tmp_path,
) -> None:
    scope = CompanionScope("u-autonomy-builder", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    messages = build_system_messages_for_inner_tick_autonomy(
        _make_bundle(), ContextMeta(), store
    )
    contents = [str(m["content"]) for m in messages]
    autonomy_blocks = [
        c for c in contents if c.startswith("本轮（AUTONOMY 自主活动）")
    ]
    assert len(autonomy_blocks) == 1
    assert not any(c.startswith("本轮（内在节拍）") for c in contents)
    assert not any(c.startswith("本轮（陪伴主动聊天）") for c in contents)
    assert not any(c.startswith("内在活动（ai_private）") for c in contents)
    assert all("## 工具环收尾：结构化信封" not in c for c in contents)
    assert all("系统仍会向用户投递产物" not in c for c in contents)