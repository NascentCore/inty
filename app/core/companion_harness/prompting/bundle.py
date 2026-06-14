"""Group of memory docs as bundle for system prompt messages injection."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PromptBundle(BaseModel):
    """
    Prompt bundle for system prompt messages injection.
    Each document is inserted as a system prompt message into the prompt of llm invocation.
    """

    identity: str
    soul: str
    style_md: str = Field(
        default="",
        description="Communication style: STYLE.md body for system injection (tone, pacing, expression boundaries).",
    )
    user_md: str
    memory_md: str = Field(
        ...,
        description="semantic memory: MEMORY.md body for system injection when private memory is on.",
    )
    techno_core_md: str = Field(
        default="",
        description="TechnoCore virtual residency constitution for autonomy boundaries.",
    )
    living_sphere_md: str = Field(
        default="",
        description="Stable virtual home anchor seeded by living_sphere for TechnoCore presence.",
    )
    significance_perception_md: str = Field(
        default="",
        description=(
            "Operator guidance for 1-10 importance scoring; injected when "
            "include_significance_perception_slice is true (package prompts/SIGNIFICANCE_PERCEPTION.md)."
        ),
    )
    channels_md: str = Field(
        default="",
        description="Channel capability contract: CHANNELS.md body for Capability system injection.",
    )
    companionship_md: str = Field(
        default="",
        description=(
            "User-facing companionship framing: COMPANIONSHIP.md body "
            "(relationship_phase, tone, mutual agreements)."
        ),
    )
    output_format_im_dm_md: str = Field(
        default="",
        description="Channel output-format slice for IM DM delivery (Weixin, Telegram, etc.).",
    )
    tools_md: str = ""
    memory_daily_today_md: str = Field(
        default="",
        description="daily gist: memory/daily/<date>.md for system injection (dreaming-written).",
    )
