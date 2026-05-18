# CREATED_BY_AGENT
"""Agent 专属提示词配置，支持按 agent_id 或 agent_name 覆盖 main_prompt / mode_prompt。"""

from dataclasses import dataclass
from typing import Dict, Optional

# 与 agent.py、Android AgentConstants 保持一致
INTELLIMATE_AGENT_ID = "879e5e14-fec2-4d63-9704-4f3141bed74f"
INTELLIMATE_AGENT_NAME = "Inty"
INTELLIMATE_AGENT_NAME_LEGACY = "IntelliMate"


@dataclass
class AgentPromptOverride:
    """Agent 专属提示词覆盖。None 表示使用默认逻辑，空字符串表示不注入该提示词。"""

    main_prompt: Optional[str] = None  # None=默认逻辑, ""=不注入
    mode_prompt: Optional[str] = None


AGENT_PROMPT_OVERRIDES: Dict[str, AgentPromptOverride] = {
    INTELLIMATE_AGENT_ID: AgentPromptOverride(main_prompt="", mode_prompt=""),
    INTELLIMATE_AGENT_NAME: AgentPromptOverride(main_prompt="", mode_prompt=""),
    INTELLIMATE_AGENT_NAME_LEGACY: AgentPromptOverride(
        main_prompt="", mode_prompt=""
    ),
}


def get_agent_prompt_override(
    agent_id: str, agent_name: str
) -> Optional[AgentPromptOverride]:
    """按 agent_id 或 agent_name 查找专属配置，优先 agent_id。"""
    return AGENT_PROMPT_OVERRIDES.get(agent_id) or AGENT_PROMPT_OVERRIDES.get(
        agent_name
    )
