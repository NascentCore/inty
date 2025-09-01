"""
Wrapper of OpenAI API, used to wrap the OpenAI API with LangSmith.
"""

"""
Demo for using OpenAI SDK with LangSmith to track the usage of OpenAI API.
"""

from enum import StrEnum
import os
from langchain_core.messages import BaseMessage
from typing_extensions import deprecated
from openai import OpenAI
from langsmith import traceable, wrappers


from app.core.config import global_config_loaded_from_config_yaml


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

    # LangSmith expects "human" and "ai" as role names.
    HUMAN = "human"
    AI = "ai"


class ReasoningEffort(StrEnum):
    """
    Used to control how much reasoning token to produces during chat completions.
    https://platform.openai.com/docs/api-reference/chat/create#chat_create-reasoning_effort
    """

    # https://ai.google.dev/gemini-api/docs/openai#thinking
    # Only meaningful for Gemini models
    NONE = "none"

    # Below are listed in OpenAI SDK.
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# These env vars has no arguments inputable to langchina api
assert os.getenv("LANGCHAIN_API_KEY"), "LANGCHAIN_API_KEY must be set"
assert os.getenv("LANGSMITH_TRACING_V2"), "LANGSMITH_TRACING_V2 must be set"
assert os.getenv("LANGSMITH_PROJECT"), "LANGSMITH_PROJECT must be set"

_vanilla_openai_client = OpenAI(
    base_url=global_config_loaded_from_config_yaml.agent.base_url,
    api_key=global_config_loaded_from_config_yaml.agent.api_key,
    # Extra headers used for tracking on openrouter.ai.
    default_headers={
        # This appears as app name on openrouter.ai's activity page.
        "HTTP-Referer": f"{global_config_loaded_from_config_yaml.app.name_for_openrouter}",  # Optional. Site URL for rankings on openrouter.ai.
        "X-Title": global_config_loaded_from_config_yaml.app.name,  # Optional. Site title for rankings on openrouter.ai.
    },
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
    return _vanilla_openai_client.chat.completions.create(messages=messages, **kwargs)


def get_openai_client(chat_name: str, labels: dict[str, str]):
    """
    Return an OpenAI client with LangSmith tracing.
    The ENV vars are required by langsmith.
    This maps the role of the messages: user->Human and assistant->AI.
    """
    # Create OpenAI client and wrap it with LangSmith
    tracing_extra = {
        "metadata": labels,
    }
    _client = wrappers.wrap_openai(
        _vanilla_openai_client, chat_name=chat_name, tracing_extra=tracing_extra
    )

    return _client


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
    client = get_openai_client()
    response = client.chat.completions.create(
        model="openai/gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello, world!"}],
    )
    print(response)
