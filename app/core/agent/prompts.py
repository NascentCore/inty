"""
Structured prompt for roleplay.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

PROMPTS_DATA_PATH = Path(__file__).with_name("prompts_data.yaml")


@lru_cache(maxsize=1)
def _load_prompts_data() -> dict[str, str]:
    """
    Lazily load the prompts YAML once per process.
    """
    with PROMPTS_DATA_PATH.open(encoding="utf-8") as fp:
        data = yaml.safe_load(fp)
    if not isinstance(data, dict):
        raise ValueError(
            f"Prompt data must be a YAML mapping: {PROMPTS_DATA_PATH}"
        )
    return data


def _get_prompt_text(key: str) -> str:
    try:
        value = _load_prompts_data()[key]
    except KeyError as exc:
        raise KeyError(f"Prompt '{key}' not found in {PROMPTS_DATA_PATH}") from exc
    if not isinstance(value, str):
        raise TypeError(f"Prompt '{key}' must be a string, got {type(value)!r}")
    return value

###############################################################################
# Main prompt is for setting up the whole framework of chat experience.
###############################################################################

# In our case, it's roleplay, which is defined here.
ROLEPLAY_MAIN_PROMPT = _get_prompt_text("ROLEPLAY_MAIN_PROMPT")

###############################################################################
# Mode prompt is for further steering the assumed {{char}}'s conversational
# style and tone.
# You can think of it subcatogory of the experience defined by the main prompt.
# In our case, main prompt is roleplay, then mode is flirting, they together
# define the experience of romantic roleplay.
###############################################################################

# Flirting mode is for romantic roleplay.
FLIRTING_MODE_PROMPT = _get_prompt_text("FLIRTING_MODE_PROMPT")

FLIRTING_MODE_PROMPT_20250902 = _get_prompt_text("FLIRTING_MODE_PROMPT_20250902")

FRIENDLY_MODE_PROMPT = _get_prompt_text("FRIENDLY_MODE_PROMPT")

PURITY_MAIN_PROMPT_0725 = _get_prompt_text("PURITY_MAIN_PROMPT_0725")

PURITY_MODE_PROMPT_0725 = _get_prompt_text("PURITY_MODE_PROMPT_0725")


class StructuredPrompt(BaseModel):
    """
    Prompt, in a moderately accurate way, refers to the *tokens* given to the LLM.
    The LLM completes the prompt, and the response is the suffix after the prompt.

    Prompt, as being sent to the LLM APIs, are structured.
    No one knows how the internal processing applied to the input request.

    The completion tokens produced by LLM is then turned into structured response.
    The overall process can be described as follows:

    <JSON-formated prompt> -> <LLM API request> -> <internal processing> -> <LLM> -> <suffix> -> <LLM API response>

    Step back a bit, the above process is usally modeled as chat.
    And the LLM can assume the role of one or multiple characters and/or narattor.
    All dependes on how to manifulate the prompt.

    With the above conceptual framework, we can then define various prompts for specific purposes.
    """

    main_prompt: str = Field(
        description="For setting up the whole framework of chat experience. The most fundamental prompt."
    )
    mode_prompt: str = Field(
        description="For further steering the assumed {{char}}'s conversational style and tone."
    )

    def assemble(self) -> list[dict]:
        """
        Assemble the structured prompt into a list of messages.
        """
        return [
            {"role": "system", "content": self.main_prompt},
            {"role": "system", "content": self.mode_prompt},
        ]


PROACTIVE_CHAT_SYSTEM_PROMPT = _get_prompt_text("PROACTIVE_CHAT_SYSTEM_PROMPT")

ROMANTIC_ROLEPLAY_PROMPT = StructuredPrompt(
    main_prompt=ROLEPLAY_MAIN_PROMPT,
    mode_prompt=FLIRTING_MODE_PROMPT_20250902,
)

FRIENDLY_ROLEPLAY_PROMPT = StructuredPrompt(
    main_prompt=ROLEPLAY_MAIN_PROMPT,
    mode_prompt=FRIENDLY_MODE_PROMPT,
)

PURITY_ROLEPLAY_PROMPT = StructuredPrompt(
    main_prompt=PURITY_MAIN_PROMPT_0725,
    mode_prompt=PURITY_MODE_PROMPT_0725,
)

###############################################################################
# Image generation prompt
###############################################################################

IMAGE_GENERATION_PROMPT_TEMPLATE = _get_prompt_text("IMAGE_GENERATION_PROMPT_TEMPLATE")
