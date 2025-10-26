"""
Wrapper of OpenAI API, used to wrap the OpenAI API with LangSmith.
"""

"""
Demo for using OpenAI SDK with LangSmith to track the usage of OpenAI API.
"""

import os
import threading
from enum import StrEnum
from typing import Optional

from langchain_core.messages import BaseMessage
from langsmith import traceable, wrappers
from loguru import logger
from openai import OpenAI
from typing_extensions import deprecated

from app.core.config import global_config_loaded_from_config_yaml


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
# LangSmith 希望“人类”和“人工智能”作为角色名称。
    HUMAN = "human"
    AI = "ai"


class ReasoningEffort(StrEnum):
    """
    Used to control how much reasoning token to produces during chat completions.
    https://platform.openai.com/docs/api-reference/chat/create#chat_create-reasoning_effort
    """
# https://ai.google.dev/gemini-api/docs/openai#thinking
# 仅对双子座模型有意义
    NONE = "none"
# 下面列出了 OpenAI SDK 中的内容。
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
# 这些环境变量无法输入到 langchina 的参数 api
def _warn_env_var(env_var: str):
    if not os.getenv(env_var):
        logger.warning(f"{env_var} is not set")


_warn_env_var("LANGCHAIN_API_KEY")
_warn_env_var("LANGSMITH_TRACING_V2")
_warn_env_var("LANGSMITH_PROJECT")
# 全局单例基础客户端，用于复用HTTP连接
_base_client: Optional[OpenAI] = None
_client_lock = threading.Lock()


def _create_openai_client():
    """创建基础OpenAI客户端实例（不含LangSmith包装）"""
    return OpenAI(
        base_url=global_config_loaded_from_config_yaml.agent.base_url,
        api_key=global_config_loaded_from_config_yaml.agent.api_key,
# 用于跟踪openrouter。ai 的额外标头。
        default_headers={
# 这是openrouter。ai 的活动页面上显示为应用程序名称。
            "HTTP-Referer": f"{global_config_loaded_from_config_yaml.app.name_for_openrouter}",  # Optional. Site URL for rankings on openrouter.ai.
            "X-Title": global_config_loaded_from_config_yaml.app.name,  # Optional. Site title for rankings on openrouter.ai.
        },
    )


def get_base_openai_client() -> OpenAI:
    """
    获取全局单例的基础OpenAI客户端（不含LangSmith包装）

    使用双重检查锁定模式确保线程安全的单例创建。
    复用HTTP连接池以提升性能。
    """
    global _base_client
    if _base_client is None:
        with _client_lock:
            if _base_client is None:
                logger.debug("创建全局基础OpenAI客户端")
                _base_client = _create_openai_client()
    return _base_client


def wrap_client_with_langsmith(
    client: OpenAI, chat_name: str, labels: dict[str, str]
) -> OpenAI:
    """
    为已有客户端添加LangSmith包装

    Args:
        client: 基础OpenAI客户端
        chat_name: 聊天名称，用于LangSmith追踪
        labels: 元数据标签

    Returns:
        包装后的OpenAI客户端，带有LangSmith追踪功能
    """
    tracing_extra = {
        "metadata": labels,
    }
    return wrappers.wrap_openai(
        client, chat_name=chat_name, tracing_extra=tracing_extra
    )


@deprecated(
    "Demo function do not use, this is only for demo @traceable "
    "This also mapps user->Human and assistant->AI"
    "We want to have it logging the raw messages, but langsmith insists on"
    "mapping user->Human and assistant->AI"
)
@traceable
def chat_completions(messages: list[dict[str, str]], **kwargs):
    """
    Return an OpenAI client without LangSmith tracing.
    """
    return _create_openai_client().chat.completions.create(messages=messages, **kwargs)


def create_openai_client(chat_name: str, labels: dict[str, str]):
    """
    Return an OpenAI client with LangSmith tracing.
    The ENV vars are required by langsmith.
    This maps the role of the messages: user->Human and assistant->AI.

    Note: 该函数保留用于向后兼容，但推荐在Agent类中使用缓存的客户端。
    对于需要在Agent外部使用的场景，该函数仍然有效。
    """
    base_client = get_base_openai_client()
    return wrap_client_with_langsmith(base_client, chat_name, labels)


def langchain_message_to_openai_message(
    message: BaseMessage, user_name: str, agent_name: str
) -> dict[str, str]:
    name = None
    if message.type == Role.HUMAN.value:
        role = Role.USER.value
        name = user_name
    elif message.type == Role.AI.value:
        role = Role.ASSISTANT.value
        name = agent_name
    else:
        role = message.type
    res = {
        "role": role,
        "content": message.content,
    }
    if name:
        res["name"] = name
    return res


if __name__ == "__main__":
    """
    Test the openai client.
    """
    from dotenv import load_dotenv

    load_dotenv()
    client = create_openai_client()
    response = client.chat.completions.create(
        model="openai/gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello, world!"}],
    )
    print(response)
