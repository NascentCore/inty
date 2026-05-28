from __future__ import annotations

import inspect

from app.core.companion_harness.companion.models import (
    OUTPUT_FORMAT_WECHAT_WEIXIN_MD,
    ContextMeta,
    InnerTickActivity,
)
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
    build_system_messages_for_bootstrap_track,
    build_system_messages_for_chat_track,
    build_system_messages_for_implicit_sign_on_greeting,
    build_system_messages_for_inner_tick_maintenance,
    build_system_messages_for_inner_tick_proactive_chat,
    build_system_messages_for_inner_tick_scheduled,
    build_system_messages_for_tool_track,
)
from app.core.companion_harness.companion.prompt_stack import (
    append_runtime_output_format_system_message,
    output_format_prompt_slice_for_runtime_channel,
)
from app.core.companion_harness.memory.memory_store_scope import (
    load_template_seed_text,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
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
    assert all("SUBCONSCIOUS" not in str(message["content"]) for message in messages)


def test_wechat_weixin_output_format_slice_is_appended_by_runtime_decorator() -> None:
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
        output_format_wechat_weixin_md=load_template_seed_text(
            OUTPUT_FORMAT_WECHAT_WEIXIN_MD
        ),
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
            channel=CompanionRuntimeChannel.WECHAT_WEIXIN,
            implicit_signal_bundle=None,
        ),
    )
    contents = [str(message["content"]) for message in messages]
    first_lines = [content.split("\n")[0] for content in contents]
    mirrored_tools_index = first_lines.index(
        "## 快思考路径（系统 1）与并行工具路径（系统 2）须一致"
    )
    wechat_index = first_lines.index("# Output format: WeChat / Weixin DM")
    envelope_index = first_lines.index(
        "## Dual-LLM chat branch: structured reply envelope"
    )

    assert mirrored_tools_index < envelope_index < wechat_index
    assert contents[wechat_index].split("\n") == [
        "# Output format: WeChat / Weixin DM",
        "",
        "The visible reply is written into a WeChat/Weixin one-to-one chat thread.",
        "",
        "- Output plain natural-language chat text only; do not use Markdown headings, tables, code fences, JSON, XML, or bullet-heavy layouts unless the user explicitly asks for structured content.",
        "- Keep each visible message compact and DM-like: usually one short paragraph, up to two short paragraphs when warmth or clarity needs it.",
        "- Preserve intimacy and immediacy: write as if texting the user directly, not as an app assistant or system.",
        "- Do not mention WeChat, Weixin, iLink, Hermes, transport adapters, prompt slices, tool routes, or delivery mechanics.",
        "- If the model response must use a structured envelope, apply this format only inside user-facing natural-language fields such as `user_facing_reply`; keep the envelope itself valid.",
    ]
    assert CompanionRuntimeChannel.WECHAT_WEIXIN.value == "wechat_weixin"


def test_output_format_slice_is_runtime_decorator_not_system_builder_argument() -> None:
    builders = [
        build_system_messages,
        build_system_messages_for_bootstrap_track,
        build_system_messages_for_chat_track,
        build_system_messages_for_tool_track,
        build_system_messages_for_inner_tick_maintenance,
        build_system_messages_for_inner_tick_proactive_chat,
        build_system_messages_for_inner_tick_scheduled,
        build_system_messages_for_implicit_sign_on_greeting,
    ]

    for builder in builders:
        assert "output_format_prompt_slice" not in inspect.signature(
            builder
        ).parameters


def test_output_format_slice_resolves_from_runtime_channel() -> None:
    body = load_template_seed_text(OUTPUT_FORMAT_WECHAT_WEIXIN_MD)
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
        output_format_wechat_weixin_md=body,
    )

    assert (
        output_format_prompt_slice_for_runtime_channel(
            bundle=bundle,
            runtime_channel=CompanionRuntimeChannel.WECHAT_WEIXIN,
        )
        == body
    )
    assert (
        output_format_prompt_slice_for_runtime_channel(
            bundle=bundle,
            runtime_channel=CompanionRuntimeChannel.APP,
        )
        == ""
    )


def test_autonomy_inner_tick_emits_autonomy_section_and_no_proactive_clause() -> None:
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
    autonomy_blocks = [c for c in contents if c.startswith("本轮（AUTONOMY 自主活动）")]
    assert len(autonomy_blocks) == 1
    proactive_blocks = [c for c in contents if c.startswith("本轮（陪伴主动聊天）")]
    assert proactive_blocks == []
    maintenance_blocks = [c for c in contents if c.startswith("本轮（内在节拍）")]
    assert maintenance_blocks == []
    autonomy_lines = autonomy_blocks[0].split("\n")
    assert "**绝对不向用户发送任何消息。** 面向用户的可见正文必须为空字符串；" in autonomy_lines[2]
    assert any("LIFE_CURRENTS.md" in line for line in autonomy_lines)
