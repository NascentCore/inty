"""
OpenAI API client helpers and shared client singleton.

Chat LLM (e.g. google/gemini-2.5-flash-lite) is invoked via this client against the
OpenRouter endpoint (agent.base_url, agent.api_key). Do not use Vertex/genai client
for chat; use get_chat_openai_client() for Agent chat, get_base_openai_client() for
default/extraction. When agent.chat_llm_base_url and agent.chat_llm_api_key are set,
chat uses that endpoint (e.g. LiteLLM); otherwise chat uses base_url + api_key.

LangSmith tracing is done at call site (e.g. agent._call_openai_api_with_retry),
not via client wrapping.
"""

# LLM provider 标识，用于 meta_data.llm_provider（openrouter / litellm）
LLM_PROVIDER_OPENROUTER = "openrouter"
LLM_PROVIDER_LITELLM = "litellm"

# TODO: 写一个 Wrapper 来完成常见功能，包括：
# 1. structured output
# 2. system_prompt, prompt, 单一 text 输出及结构和输出
# 之前尝试：https://github.com/NascentCore/inty/pull/2310 没有完成

import os
import threading
from enum import StrEnum
from typing import Any, Optional, Tuple

from langchain_core.messages import BaseMessage
from loguru import logger
from openai import AsyncOpenAI, OpenAI

from app.api.types.llm_config import LLMConfig
from app.utils.models_catalog import CHAT_TEXT_MODELS, OPENROUTER_VISION_CHAT_FALLBACK_ID
from app.core.agentic_kernel.providers.facade import (
    OpenAICompatibleClientOptions,
    get_openai_compatible_async_client,
    get_openai_compatible_sync_client,
)
from app.core.config import Environment, global_config_loaded_from_config_yaml
from app.utils.openrouter_memory import DEFAULT_MEMORY_EXTRACTION_MODEL


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
def _warn_env_var(env_var: str):
    if not os.getenv(env_var):
        logger.warning(f"{env_var} is not set")


_warn_env_var("LANGCHAIN_API_KEY")
_warn_env_var("LANGSMITH_TRACING_V2")
_warn_env_var("LANGSMITH_PROJECT")


# 全局单例基础客户端，用于复用HTTP连接
_base_client: Optional[OpenAI] = None
_client_lock = threading.Lock()

_async_client: Optional[AsyncOpenAI] = None
_async_client_lock = threading.Lock()

_chat_client: Optional[OpenAI] = None
_chat_client_lock = threading.Lock()


def _create_openai_client():
    """创建基础OpenAI客户端实例（不含LangSmith包装）"""
    use_fake_openai = (
        global_config_loaded_from_config_yaml.app.environment == Environment.TEST
    )
    return get_openai_compatible_sync_client(
        OpenAICompatibleClientOptions(
            base_url=global_config_loaded_from_config_yaml.agent.base_url,
            api_key=global_config_loaded_from_config_yaml.agent.api_key,
            wrap_langsmith=False,
            default_headers={
                # This appears as app name on openrouter.ai's activity page.
                "HTTP-Referer": f"{global_config_loaded_from_config_yaml.app.name_for_openrouter}",  # Optional. Site URL for rankings on openrouter.ai.
                "X-Title": global_config_loaded_from_config_yaml.app.name,  # Optional. Site title for rankings on openrouter.ai.
            },
            use_fake_openai=use_fake_openai,
        )
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


def _create_chat_openai_client() -> OpenAI:
    """创建 Agent 聊天专用 OpenAI 客户端。若配置了 chat_llm_base_url 与 chat_llm_api_key 则使用二者，否则使用 base_url + api_key。"""
    cfg = global_config_loaded_from_config_yaml.agent
    base_url = cfg.chat_llm_base_url or cfg.base_url
    api_key = cfg.chat_llm_api_key or cfg.api_key
    use_fake_openai = (
        global_config_loaded_from_config_yaml.app.environment == Environment.TEST
    )
    return get_openai_compatible_sync_client(
        OpenAICompatibleClientOptions(
            base_url=base_url,
            api_key=api_key,
            wrap_langsmith=False,
            default_headers={
                "HTTP-Referer": f"{global_config_loaded_from_config_yaml.app.name_for_openrouter}",
                "X-Title": global_config_loaded_from_config_yaml.app.name,
            },
            use_fake_openai=use_fake_openai,
        )
    )


def get_chat_openai_client() -> OpenAI:
    """
    获取 Agent 聊天专用 OpenAI 客户端单例。
    当配置了 agent.chat_llm_base_url 与 agent.chat_llm_api_key 时使用该端点（如 LiteLLM），否则与 get_base_openai_client() 相同。
    """
    global _chat_client
    if _chat_client is None:
        with _chat_client_lock:
            if _chat_client is None:
                logger.debug("创建 Agent 聊天专用 OpenAI 客户端")
                _chat_client = _create_chat_openai_client()
    return _chat_client


def get_chat_llm_provider() -> str:
    """返回当前 chat 使用的 LLM 网关标识（来自配置 agent.chat_llm_provider），用于写入 meta_data.llm_provider。"""
    return global_config_loaded_from_config_yaml.agent.chat_llm_provider


def _create_async_openai_client() -> AsyncOpenAI:
    """创建 AsyncOpenAI 客户端，与 sync 客户端相同配置（base_url、api_key、OpenRouter headers）。"""
    # 与历史行为保持一致：异步抽取路径即使在 TEST 也不走 FakeOpenAI。
    return get_openai_compatible_async_client(
        OpenAICompatibleClientOptions(
            base_url=global_config_loaded_from_config_yaml.agent.base_url,
            api_key=global_config_loaded_from_config_yaml.agent.api_key,
            wrap_langsmith=False,
            default_headers={
                "HTTP-Referer": f"{global_config_loaded_from_config_yaml.app.name_for_openrouter}",
                "X-Title": global_config_loaded_from_config_yaml.app.name,
            },
            timeout=120.0,
            use_fake_openai=False,
        )
    )


def get_async_openai_client() -> AsyncOpenAI:
    """
    获取全局单例的 AsyncOpenAI 客户端。
    用于记忆抽取等异步调用，与 get_base_openai_client() 配置一致。
    """
    global _async_client
    if _async_client is None:
        with _async_client_lock:
            if _async_client is None:
                logger.debug("创建全局 AsyncOpenAI 客户端")
                _async_client = _create_async_openai_client()
    return _async_client


def _default_extraction_llm_config() -> LLMConfig:
    """默认记忆抽取用 LLM 配置，与原先 chat_completion_for_extraction 行为一致。"""
    return LLMConfig(
        model=DEFAULT_MEMORY_EXTRACTION_MODEL,
        max_tokens=4000,
        temperature=0.3,
    )


def _llm_config_to_create_kwargs(llm_config: LLMConfig) -> dict:
    """从 LLMConfig 构建 client.chat.completions.create 的参数字典，仅包含非 None 字段。"""
    model = (llm_config.model or "").strip() or DEFAULT_MEMORY_EXTRACTION_MODEL
    kwargs: dict = {
        "model": model,
        "max_tokens": llm_config.max_tokens,
        "temperature": llm_config.temperature,
    }
    if llm_config.top_p is not None:
        kwargs["top_p"] = llm_config.top_p
    if llm_config.presence_penalty is not None:
        kwargs["presence_penalty"] = llm_config.presence_penalty
    if llm_config.frequency_penalty is not None:
        kwargs["frequency_penalty"] = llm_config.frequency_penalty
    return kwargs


async def chat_completion_for_extraction(
    prompt: str,
    llm_config: Optional[LLMConfig] = None,
    response_format: Optional[dict] = None,
) -> Tuple[str, int | None, int | None]:
    """
    异步调用 chat completions 用于记忆抽取。
    返回 (content, prompt_tokens, completion_tokens)。
    llm_config 为 None 时使用默认配置（DEFAULT_MEMORY_EXTRACTION_MODEL、max_tokens=4000、temperature=0.3）。
    response_format 非空时传入 create（OpenRouter/OpenAI 结构化输出），content 为 JSON 字符串，由调用方解析。
    """
    cfg = llm_config if llm_config is not None else _default_extraction_llm_config()
    client = get_async_openai_client()
    create_kwargs = _llm_config_to_create_kwargs(cfg)
    if response_format is not None:
        create_kwargs["response_format"] = response_format

    response = await client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        **create_kwargs,
    )
    content = (response.choices[0].message.content or "") if response.choices else ""
    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else None
    completion_tokens = usage.completion_tokens if usage else None
    return (content, prompt_tokens, completion_tokens)


def openai_chat_messages_include_image_parts(messages: list[dict[str, Any]]) -> bool:
    """True if any message uses OpenAI multimodal content with an image part."""
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "image_url":
                return True
            if part.get("type") == "input_image":
                return True
    return False


def resolve_chat_model_for_openai_messages(
    resolved_model_id: str,
    openai_messages: list[dict[str, Any]],
) -> str:
    """
    Use a vision-capable OpenRouter model when the payload includes images but the
    configured chat model is text-only (catalog CHAT_TEXT_MODELS).
    """
    if not openai_chat_messages_include_image_parts(openai_messages):
        return resolved_model_id
    if resolved_model_id == OPENROUTER_VISION_CHAT_FALLBACK_ID:
        return resolved_model_id
    text_only_ids = {m.id_on_provider for m in CHAT_TEXT_MODELS}
    if resolved_model_id not in text_only_ids:
        return resolved_model_id
    logger.info(
        "Chat includes image parts; switching model from {} to {} for vision support",
        resolved_model_id,
        OPENROUTER_VISION_CHAT_FALLBACK_ID,
    )
    return OPENROUTER_VISION_CHAT_FALLBACK_ID


def langchain_message_to_openai_message(
    message: BaseMessage, user_name: str, agent_name: str
) -> dict[str, Any]:
    name = None
    if message.type == Role.HUMAN.value:
        role = Role.USER.value
        name = user_name
    elif message.type == Role.AI.value:
        role = Role.ASSISTANT.value
        name = agent_name
    else:
        role = message.type
    content = message.content
    if isinstance(content, list):
        normalized_content = []
        for part in content:
            if hasattr(part, "model_dump"):
                normalized_content.append(part.model_dump(exclude_none=True))
            else:
                normalized_content.append(part)
        content = normalized_content
    elif hasattr(content, "model_dump"):
        content = content.model_dump(exclude_none=True)
    res = {
        "role": role,
        "content": content,
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
    client = get_base_openai_client()
    response = client.chat.completions.create(
        model="openai/gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello, world!"}],
    )
    print(response)
