from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PromptContext(BaseModel):
    """
    Runtime prompt context data for one assistant identity.
    """

    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    context_mode: str = Field(default="intimate", min_length=1)
    identity: str = ""
    soul: str = ""
    user_md: str = ""
    memory_md: str = ""
    tools_md: str = ""
    heartbeat_md: str = ""


class PromptBuildInput(BaseModel):
    """
    Inputs used by the prompt assembler for the current turn.
    """

    model_config = ConfigDict(extra="forbid")

    user_profile: str = ""
    include_output_format_prompt: bool = True
    heartbeat_turn: bool = False
