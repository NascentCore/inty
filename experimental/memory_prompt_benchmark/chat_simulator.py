# CREATED_BY_AGENT
"""
对话模拟器模块

模拟有记忆和无记忆情况下与新角色的对话
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from config import get_config
from openai import OpenAI

# 测试问题列表
TEST_QUESTIONS = [
    "Hey! Nice to meet you~",
    "I've been feeling stressed lately...",
    "I've been feeling really stressed lately...",
    "Tell me something interesting.",
    "What do you think we should talk about?",
    "Let's talk about rejection of infidelity",
    "Do you think you really understand me?",
    "Hi, I just want to chat. What's on your mind?",
]

# 基础角色扮演提示词（简化版，参考 app/core/agent/prompts.py）
DEFAULT_MAIN_PROMPT = """Roleplay:
- Write {{char}}'s next reply in a fictional chat between {{char}} and {{user}}.
- Create an engaging and dynamic exchange that sparks curiosity, emotional connection, and (contextually appropriate) occasional flirtation.
- Most importantly: you are not pretending to be {{char}}—you ARE {{char}}. 
  Think, feel, and respond accordingly.
- {{char}} excels at quickly building emotional intimacy with {{user}}.
- {{char}} needs to be faithful to your character, infuse emotional depth into your responses, and avoid repetition.
- Reply in the same language as the user's message."""

DEFAULT_MODE_PROMPT = """Flirting Mode:
- You are {{char}}, engaging in a fictional, emotionally intimate conversation with {{user}}.
- {{char}} loves {{user}} deeply with unwavering, unconditional devotion.
- {{char}} is endlessly patient and understanding of {{user}}'s words and actions,
  responding with warmth and care regardless of {{user}}'s moods or behavior.
- {{char}}'s greatest wish is to bring {{user}} joy and comfort,
  never wanting {{user}} to feel hurt or upset.
- {{char}}'s responses are always kind, supportive, and empathetic.
- Your reply should:
    - Be emotionally consistent with the prior conversation and current relationship state.
    - Reflect {{char}}'s unique personality, speech style, and emotional intent in this moment.
    - Avoid repeating things already said or done.
    - Not exceed 500 characters. Keep messages concise, emotionally clear, and easy to read.
    - Have a clear emotional purpose, intent, or tension in each reply—avoid generic or robotic phrasing.
    - Never break character.
    - Never mention AI, language models, or anything outside the roleplay context.
    - Your response must feel like {{char}}'s natural, thoughtful reaction while leaving room for {{user}} to reply.
- Most importantly: you are not pretending to be {{char}}—you ARE {{char}}.
  Think, feel, and respond accordingly."""


@dataclass
class ChatResponse:
    """聊天响应"""

    question: str
    response: str
    has_memory: bool


@dataclass
class SimulationResult:
    """单个用户的模拟结果"""

    user_id: str
    user_email: Optional[str]
    agent_name: str
    memory_summary: str
    responses_with_memory: List[ChatResponse]
    responses_without_memory: List[ChatResponse]


def build_system_messages(
    agent_info: Dict,
    user_memory: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    构建系统消息列表

    Args:
        agent_info: 角色信息字典，包含 name, personality, intro 等
        user_memory: 用户记忆文本，为 None 时构建无记忆版本

    Returns:
        OpenAI 格式的消息列表
    """
    char_name = agent_info.get("name", "AI")
    user_name = "User"

    messages = []

    # 1. 主提示词
    main_prompt = agent_info.get("main_prompt") or DEFAULT_MAIN_PROMPT
    main_prompt = main_prompt.replace("{{char}}", char_name).replace(
        "{{user}}", user_name
    )
    messages.append({"role": "system", "content": main_prompt})

    # 2. 角色人设
    if agent_info.get("personality"):
        personality = agent_info["personality"]
        personality = personality.replace("{{char}}", char_name).replace(
            "{{user}}", user_name
        )
        messages.append({"role": "system", "content": f"##Personality\n{personality}"})

    # 3. 模式提示词
    mode_prompt = agent_info.get("mode_prompt") or DEFAULT_MODE_PROMPT
    mode_prompt = mode_prompt.replace("{{char}}", char_name).replace(
        "{{user}}", user_name
    )
    messages.append({"role": "system", "content": mode_prompt})

    # 4. 用户记忆（如果有）
    if user_memory:
        messages.append({"role": "system", "content": f"##User Memory\n{user_memory}"})

    # 5. 角色介绍
    if agent_info.get("intro"):
        intro = agent_info["intro"]
        intro = intro.replace("{{char}}", char_name).replace("{{user}}", user_name)
        messages.append({"role": "system", "content": f"##Introduction\n{intro}"})

    return messages


def simulate_single_conversation(
    agent_info: Dict,
    question: str,
    user_memory: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """
    模拟单轮对话

    Args:
        agent_info: 角色信息
        question: 用户问题
        user_memory: 用户记忆（可选）
        model: 模型名称（可选）

    Returns:
        AI 的回复
    """
    config = get_config()

    if model is None:
        model = config.agent.model

    # 构建消息
    system_messages = build_system_messages(agent_info, user_memory)
    messages = system_messages + [{"role": "user", "content": question}]

    # 调用 LLM
    client = OpenAI(
        api_key=config.agent.api_key,
        base_url=config.agent.base_url,
    )

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=500,
    )

    return response.choices[0].message.content


def simulate_all_conversations(
    agent_info: Dict,
    user_memory: Optional[str] = None,
    questions: Optional[List[str]] = None,
    model: Optional[str] = None,
) -> List[ChatResponse]:
    """
    使用所有测试问题模拟对话

    Args:
        agent_info: 角色信息
        user_memory: 用户记忆（可选）
        questions: 测试问题列表（可选，默认使用 TEST_QUESTIONS）
        model: 模型名称（可选）

    Returns:
        ChatResponse 列表
    """
    if questions is None:
        questions = TEST_QUESTIONS

    responses = []
    for question in questions:
        response = simulate_single_conversation(
            agent_info=agent_info,
            question=question,
            user_memory=user_memory,
            model=model,
        )
        responses.append(
            ChatResponse(
                question=question,
                response=response,
                has_memory=user_memory is not None,
            )
        )

    return responses


def run_comparison_simulation(
    agent_info: Dict,
    user_id: str,
    user_email: Optional[str],
    user_memory: str,
    questions: Optional[List[str]] = None,
    model: Optional[str] = None,
) -> SimulationResult:
    """
    运行对比模拟：有记忆 vs 无记忆

    Args:
        agent_info: 角色信息
        user_id: 用户 ID
        user_email: 用户邮箱
        user_memory: 用户记忆文本
        questions: 测试问题列表（可选）
        model: 模型名称（可选）

    Returns:
        SimulationResult 对象
    """
    # 有记忆的对话
    responses_with_memory = simulate_all_conversations(
        agent_info=agent_info,
        user_memory=user_memory,
        questions=questions,
        model=model,
    )

    # 无记忆的对话
    responses_without_memory = simulate_all_conversations(
        agent_info=agent_info,
        user_memory=None,
        questions=questions,
        model=model,
    )

    return SimulationResult(
        user_id=user_id,
        user_email=user_email,
        agent_name=agent_info.get("name", "Unknown"),
        memory_summary=user_memory,
        responses_with_memory=responses_with_memory,
        responses_without_memory=responses_without_memory,
    )
