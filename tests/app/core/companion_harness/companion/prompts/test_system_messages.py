from __future__ import annotations

from app.core.companion_harness.companion.models import (
    OUTPUT_FORMAT_WECHAT_WEIXIN_MD,
    ContextMeta,
)
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
)
from app.core.companion_harness.memory.memory_store_scope import (
    load_template_seed_text,
)
from app.schemas.implicit_signals import OutputFormatPromptSlice


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


def test_wechat_weixin_output_format_slice_is_in_output_layer() -> None:
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
        output_format_prompt_slice=bundle.output_format_wechat_weixin_md,
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

    assert mirrored_tools_index < wechat_index < envelope_index
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
    assert OutputFormatPromptSlice.WECHAT_WEIXIN.value == "wechat_weixin"
