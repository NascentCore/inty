from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.agentic_kernel.experience_profile import normalize_experience_profile_id


class PromptContext(BaseModel):
    """
    Runtime prompt context data for one assistant identity.
    """

    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    context_mode: str = Field(
        default="intimate",
        min_length=1,
        description="Experience profile id (canonical); persisted as context.json context_mode.",
    )
    identity: str = ""
    soul: str = ""
    user_md: str = ""
    memory_md: str = ""
    tools_md: str = ""
    heartbeat_md: str = ""

    @field_validator("context_mode")
    @classmethod
    def _validate_context_mode(cls, v: str) -> str:
        return normalize_experience_profile_id(v)


class PromptBuildInput(BaseModel):
    """
    Inputs used by the prompt assembler for the current turn.
    """

    model_config = ConfigDict(extra="forbid")

    user_profile: str = ""
    include_output_format_prompt: bool = True
    inner_tick_turn: bool = False
    inner_tick_mode: str = "maintenance"
