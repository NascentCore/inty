"""Group of memory docs as bundle for system prompt messages injection."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PromptBundle(BaseModel):
    """
    Prompt bundle for system prompt messages injection.
    Each document is inserted as a system prompt message into the prompt of llm invocation.
    Field semantics and paths are owned by ``memory_document_catalog``.
    """

    identity: str
    soul: str
    style_md: str = Field(
        default="",
        description="Communication style body; catalog bundle_field style_md.",
    )
    user_md: str
    memory_md: str = Field(
        ...,
        description="Semantic memory body; catalog bundle_field memory_md.",
    )
    techno_core_md: str = Field(
        default="",
        description="TechnoCore constitution; catalog bundle_field techno_core_md.",
    )
    living_sphere_md: str = Field(
        default="",
        description="LivingSphere snapshot; catalog bundle_field living_sphere_md.",
    )
    significance_perception_md: str = Field(
        default="",
        description="Significance scoring guidance; catalog bundle_field significance_perception_md.",
    )
    channels_md: str = Field(
        default="",
        description="Channel capability contract; catalog bundle_field channels_md.",
    )
    output_format_wechat_weixin_md: str = Field(
        default="",
        description="Non-catalog runtime channel output-format slice (WeChat/Weixin DM).",
    )
    tools_md: str = ""
    memory_daily_today_md: str = Field(
        default="",
        description="Daily gist body; catalog bundle_field memory_daily_today_md.",
    )
