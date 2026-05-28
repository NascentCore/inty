"""Channel-specific output-format prompt slices for companion turns.

These slices are fixed package prompt text selected by runtime channel signals.
They do not live in MemoryStore because they describe transport affordances, not
the companion persona or relationship memory.
"""

from __future__ import annotations

from app.schemas.implicit_signals import (
    ImplicitSignalBundle,
    OutputFormatPromptSlice,
)


WECHAT_WEIXIN_OUTPUT_FORMAT_PROMPT_SLICE = """## Output format: WeChat / Weixin DM

The visible reply is written into a WeChat/Weixin one-to-one chat thread.

- Output plain natural-language chat text only; do not use Markdown headings, tables, code fences, JSON, XML, or bullet-heavy layouts unless the user explicitly asks for structured content.
- Keep each visible message compact and DM-like: usually one short paragraph, up to two short paragraphs when warmth or clarity needs it.
- Preserve intimacy and immediacy: write as if texting the user directly, not as an app assistant or system.
- Do not mention WeChat, Weixin, iLink, Hermes, transport adapters, prompt slices, tool routes, or delivery mechanics.
- If the model response must use a structured envelope, apply this format only inside user-facing natural-language fields such as `user_facing_reply`; keep the envelope itself valid.
"""


def output_format_prompt_slice_text(
    output_format: OutputFormatPromptSlice,
) -> str:
    """Return fixed prompt text for a channel output-format slice id."""
    match output_format:
        case OutputFormatPromptSlice.WECHAT_WEIXIN:
            return WECHAT_WEIXIN_OUTPUT_FORMAT_PROMPT_SLICE


def output_format_prompt_slice_for_implicit_signals(
    implicit_signal_bundle: ImplicitSignalBundle | None,
) -> str:
    """Resolve the per-turn channel output prompt slice from runtime signals."""
    if implicit_signal_bundle is None:
        return ""
    output_format = implicit_signal_bundle.output_format_prompt_slice
    if output_format is None:
        return ""
    return output_format_prompt_slice_text(output_format)
