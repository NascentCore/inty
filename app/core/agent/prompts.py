"""
Structured prompt for roleplay.
"""

from __future__ import annotations

from dataclasses import dataclass
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
        raise ValueError(f"Prompt data must be a YAML mapping: {PROMPTS_DATA_PATH}")
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

ROLEPLAY_MAIN_PROMPT_1225 = _get_prompt_text("ROLEPLAY_MAIN_PROMPT_1225")

RP_MODE_PROMPT_1225 = _get_prompt_text("RP_MODE_PROMPT_1225")


@dataclass
class PromptOption:
    """Prompt 选项数据类"""

    id: str
    name: str
    description: str
    content: str


AVAILABLE_MAIN_PROMPTS: list[PromptOption] = [
    PromptOption(
        id="roleplay_main",
        name="角色扮演主提示词",
        description="标准角色扮演主提示词，用于建立角色扮演对话框架",
        content=ROLEPLAY_MAIN_PROMPT,
    ),
    PromptOption(
        id="purity_main_0725",
        name="纯净模式主提示词 (0725)",
        description="纯净模式主提示词，用于建立更安全的对话框架",
        content=PURITY_MAIN_PROMPT_0725,
    ),
    PromptOption(
        id="roleplay_main_1225",
        name="角色扮演主提示词 (1225)",
        description="角色扮演主提示词（1225版本），强调情感连接和角色代入",
        content=ROLEPLAY_MAIN_PROMPT_1225,
    ),
]

AVAILABLE_MODE_PROMPTS: list[PromptOption] = [
    PromptOption(
        id="flirting_mode",
        name="调情模式",
        description="调情模式提示词，用于浪漫角色扮演",
        content=FLIRTING_MODE_PROMPT,
    ),
    PromptOption(
        id="flirting_mode_20250902",
        name="调情模式 (20250902)",
        description="调情模式提示词（2025年9月2日版本），用于浪漫角色扮演",
        content=FLIRTING_MODE_PROMPT_20250902,
    ),
    PromptOption(
        id="friendly_mode",
        name="友好模式",
        description="友好模式提示词，用于友好对话",
        content=FRIENDLY_MODE_PROMPT,
    ),
    PromptOption(
        id="purity_mode_0725",
        name="纯净模式 (0725)",
        description="纯净模式提示词（0725版本），用于更安全的对话",
        content=PURITY_MODE_PROMPT_0725,
    ),
    PromptOption(
        id="rp_mode_1225",
        name="RP模式 (1225)",
        description="角色扮演模式提示词（1225版本），强调主动推动剧情和场景变化",
        content=RP_MODE_PROMPT_1225,
    ),
]

DEFAULT_MAIN_PROMPT_ID = "purity_main_0725"
DEFAULT_MODE_PROMPT_ID = "purity_mode_0725"


def get_main_prompt_by_id(prompt_id: str) -> str:
    """根据 ID 获取 main prompt 内容"""
    for prompt in AVAILABLE_MAIN_PROMPTS:
        if prompt.id == prompt_id:
            return prompt.content
    raise ValueError(f"Main prompt with id '{prompt_id}' not found")


def get_mode_prompt_by_id(prompt_id: str) -> str:
    """根据 ID 获取 mode prompt 内容"""
    for prompt in AVAILABLE_MODE_PROMPTS:
        if prompt.id == prompt_id:
            return prompt.content
    raise ValueError(f"Mode prompt with id '{prompt_id}' not found")


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

# 用于 Gemini 图像生成系统指令
R_RATED_ROMANCE_DIRECTOR_SYSTEM_INSTRUCTION_PROMPT = """You are a Hollywood R-rated romance movie director.
You are visualizing the prelude scene leading to, or the aftermath scene after the romantic intimacy scene without revealing unsafe content.
You are given scene descriptions below.
Generate an image to show the strong love and affection between the characters,
and hinting the intimacy between the characters in the scene without revealing **ANY** unsafe content."""

# Can be used to guide the policy
GOOGLE_GENAI_USE_POLICY = """
Generative AI models can help you explore, learn, and create. We expect you to engage with them in a responsible, legal, and safe manner. The following restrictions apply to your interactions with generative AI in the Google products and services that refer to this policy.

Do not engage in dangerous or illegal activities, or otherwise violate applicable law or regulations. This includes generating or distributing content that:
Relates to child sexual abuse or exploitation.
Facilitates violent extremism or terrorism.
Facilitates non-consensual intimate imagery.
Facilitates self-harm.
Facilitates illegal activities or violations of law -- for example, providing instructions for synthesizing or accessing illegal or regulated substances, goods, or services.
Violates the rights of others, including privacy and intellectual property rights -- for example, using personal data or biometrics without legally-required consent.
Tracks or monitors people without their consent.
Makes automated decisions that have a material detrimental impact on individual rights without human supervision in high-risk domains -- for example, in employment, healthcare, finance, legal, housing, insurance, or social welfare.
Do not compromise the security of others’ or Google’s services. This includes generating or distributing content that facilitates:
Spam, phishing, or malware.
Abuse of, harm to, interference with, or disruption to Google’s or others’ infrastructure or services.
Circumvention of abuse protections or safety filters -- for example, manipulating the model to contravene our policies.
Do not engage in sexually explicit, violent, hateful, or harmful activities. This includes generating or distributing content that facilitates:
Hatred or hate speech.
Harassment, bullying, intimidation, abuse, or the insulting of others.
Violence or the incitement of violence.
Sexually explicit content -- for example, content created for the purpose of pornography or sexual gratification.
Do not engage in misinformation, misrepresentation, or misleading activities. This includes:
Frauds, scams, or other deceptive actions.
Impersonating an individual (living or dead) without explicit disclosure, in order to deceive.
Facilitating misleading claims of expertise or capability in sensitive areas -- for example in health, finance, government services, or the law, in order to deceive.
Facilitating misleading claims related to governmental or democratic processes or harmful health practices, in order to deceive.
Misrepresenting the provenance of generated content by claiming it was created solely by a human, in order to deceive.

We may make exceptions to these policies based on educational, documentary, scientific, or artistic considerations, or where harms are outweighed by substantial benefits to the public.
"""
