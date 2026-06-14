from __future__ import annotations

import inspect

from app.core.companion_harness.companion.models import (
    OUTPUT_FORMAT_IM_DM_MD,
    ContextMeta,
    InnerTickActivity,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
    build_system_messages_for_bootstrap_track,
    build_system_messages_for_chat_track,
    build_system_messages_for_implicit_sign_on_greeting,
    build_system_messages_for_inner_tick_autonomy,
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


def test_contextual_messages_include_infer_time_zone_slice_with_tool_name() -> None:
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )
    messages = build_system_messages_for_chat_track(
        bundle,
        ContextMeta(),
        memory_bootstrap_type="none",
    )
    joined = "\n".join(str(m["content"]) for m in messages if m["role"] == "system")
    assert "用户当地时间与作息" in joined
    assert "update_user_md" in joined
    assert "Asia/Shanghai" in joined


def test_inner_tick_maintenance_omits_infer_time_zone_slice() -> None:
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
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        ai_private_text="private\n",
        tool_side_compact=True,
    )
    joined = "\n".join(str(m["content"]) for m in messages if m["role"] == "system")
    assert "用户当地时间与作息" not in joined


def test_inner_tick_maintenance_is_monolog_only_without_ls_tc_or_memory_store() -> None:
    bundle = PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )
    messages = build_system_messages_for_inner_tick_maintenance(
        store=MemoryStore(
            scope=CompanionScope("sm", "a", "maintenance-prompt"),
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
        output_format_im_dm_md=load_template_seed_text(
            OUTPUT_FORMAT_IM_DM_MD
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
    im_index = first_lines.index("# Output format: IM direct message")
    envelope_index = first_lines.index(
        "## Dual-LLM chat branch: structured reply envelope"
    )

    assert mirrored_tools_index < envelope_index < im_index
    assert contents[im_index].split("\n") == [
        "# Output format: IM direct message",
        "",
        "The visible reply is written into a one-to-one instant-messaging chat thread (WeChat, Telegram, or similar).",
        "",
        "- Output plain natural-language chat text only; do not use Markdown headings, tables, code fences, JSON, XML, or bullet-heavy layouts unless the user explicitly asks for structured content.",
        "- Keep each visible message short and DM-like: usually 1–3 short sentences; avoid essay-style blocks.",
        "- When a thought needs more room, split it across line breaks into several short lines (like sending a few quick texts), not one dense paragraph.",
        "- Preserve intimacy and immediacy: write as if texting the user directly, not as an app assistant or system.",
        "- Do not mention WeChat, Weixin, Telegram, iLink, Hermes, transport adapters, prompt slices, tool routes, or delivery mechanics.",
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
        build_system_messages_for_inner_tick_autonomy,
        build_system_messages_for_inner_tick_proactive_chat,
        build_system_messages_for_inner_tick_scheduled,
        build_system_messages_for_implicit_sign_on_greeting,
    ]

    for builder in builders:
        assert "output_format_prompt_slice" not in inspect.signature(
            builder
        ).parameters


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
            runtime_channel=CompanionRuntimeChannel.WECHAT_WEIXIN,
        )
        == body
    )
    assert (
        output_format_prompt_slice_for_runtime_channel(
            bundle=bundle,
            runtime_channel=CompanionRuntimeChannel.TELEGRAM,
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
    assert not any(c.startswith("内在活动（ai_private）") for c in contents)
    autonomy_lines = autonomy_blocks[0].split("\n")
    assert "**绝对不向用户发送任何消息。** 面向用户的可见正文必须为空字符串；" in autonomy_lines[2]
    assert any("LIFE_CURRENTS.md" in line for line in autonomy_lines)
    autonomy_text = autonomy_blocks[0]
    assert "与 ai_private 分工" in autonomy_text
    assert "禁止写入" in autonomy_text
    assert "成为他的知己" in autonomy_text
    assert "只允许" in autonomy_text and "LIFE_CURRENTS.md" in autonomy_text


def test_build_system_messages_for_inner_tick_autonomy_is_production_builder(
    tmp_path,
) -> None:
    scope = CompanionScope("u-autonomy-builder", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    messages = build_system_messages_for_inner_tick_autonomy(
        _make_bundle(), ContextMeta(), store
    )
    contents = [str(m["content"]) for m in messages]
    autonomy_blocks = [c for c in contents if c.startswith("本轮（AUTONOMY 自主活动）")]
    assert len(autonomy_blocks) == 1
    assert not any(c.startswith("本轮（内在节拍）") for c in contents)
    assert not any(c.startswith("本轮（陪伴主动聊天）") for c in contents)
    assert not any(c.startswith("内在活动（ai_private）") for c in contents)
    assert all("## 工具环收尾：结构化信封" not in c for c in contents)
    assert all("系统仍会向用户投递产物" not in c for c in contents)


def _make_bundle() -> PromptBundle:
    return PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )


def test_proactive_chat_injects_life_currents_when_present(tmp_path) -> None:
    scope = CompanionScope("u-proactive", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    life_currents = (
        "# 我最近在做的事\n\n"
        "## 当前主题（中期）\n"
        "跟得上他在做的独立游戏圈\n\n"
        "## 今天（当日兴致）\n"
        "翻一翻他上次提到的那本《xxx》\n"
    )
    store.write_document("LIFE_CURRENTS.md", life_currents)
    messages = build_system_messages_for_inner_tick_proactive_chat(
        _make_bundle(), ContextMeta(), store
    )
    contents = [str(m["content"]) for m in messages]
    proactive_idx = next(
        i for i, c in enumerate(contents) if c.startswith("本轮（陪伴主动聊天）")
    )
    life_block = contents[proactive_idx + 1]
    life_lines = life_block.split("\n")
    assert life_lines[0] == "## 你最近在做的事（仅供参考）"
    assert "跟得上他在做的独立游戏圈" in life_block
    assert "翻一翻他上次提到的那本《xxx》" in life_block
    assert life_lines[-1].startswith("内在独白（ai_private）已在对话上下文中")


def test_proactive_chat_omits_life_currents_when_missing(tmp_path) -> None:
    scope = CompanionScope("u-proactive-missing", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    messages = build_system_messages_for_inner_tick_proactive_chat(
        _make_bundle(), ContextMeta(), store
    )
    contents = [str(m["content"]) for m in messages]
    assert any(c.startswith("本轮（陪伴主动聊天）") for c in contents)
    assert all("## 你最近在做的事" not in c for c in contents)


def test_proactive_chat_omits_life_currents_when_blank(tmp_path) -> None:
    scope = CompanionScope("u-proactive-blank", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("LIFE_CURRENTS.md", "   \n")
    messages = build_system_messages_for_inner_tick_proactive_chat(
        _make_bundle(), ContextMeta(), store
    )
    contents = [str(m["content"]) for m in messages]
    assert all("## 你最近在做的事" not in c for c in contents)
