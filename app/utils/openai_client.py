"""
OpenAI client, used to wrap the OpenAI API with LangSmith.
"""

import os
import threading
from enum import StrEnum
from typing import Optional, Tuple

from langchain_core.messages import BaseMessage
from langsmith import traceable
from loguru import logger
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel, ValidationError

from app.api.types.llm_config import LLMConfig
from app.external_services.fakes.openai import FakeOpenAI
from app.utils.openrouter_memory import DEFAULT_MEMORY_EXTRACTION_MODEL

import cyclopts

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


def _create_openai_client():
    """创建基础OpenAI客户端实例（不含LangSmith包装）"""
    # 在测试环境使用 FakeOpenAI
    from app.utils.config import Environment

    from app.core.config import global_config_loaded_from_config_yaml as global_config
    if global_config.app.environment == Environment.TEST:
        logger.info("Using FakeOpenAI in test environment")
        return FakeOpenAI()

    return OpenAI(
        base_url=global_config.agent.base_url,
        api_key=global_config.agent.api_key,
        # Extra headers used for tracking on openrouter.ai.
        default_headers={
            # This appears as app name on openrouter.ai's activity page.
            "HTTP-Referer": f"{global_config.app.name_for_openrouter}",  # Optional. Site URL for rankings on openrouter.ai.
            "X-Title": global_config.app.name,  # Optional. Site title for rankings on openrouter.ai.
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


def _create_async_openai_client() -> AsyncOpenAI:
    """创建 AsyncOpenAI 客户端，与 sync 客户端相同配置（base_url、api_key、OpenRouter headers）。"""
    # 测试环境也使用真实 AsyncOpenAI；需 mock 的测试会 patch chat_completion_for_extraction。
    return AsyncOpenAI(
        base_url=global_config_loaded_from_config_yaml.agent.base_url,
        api_key=global_config_loaded_from_config_yaml.agent.api_key,
        default_headers={
            "HTTP-Referer": f"{global_config_loaded_from_config_yaml.app.name_for_openrouter}",
            "X-Title": global_config_loaded_from_config_yaml.app.name,
        },
        timeout=120.0,
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
) -> Tuple[str, int | None, int | None]:
    """
    异步调用 chat completions 用于记忆抽取。
    返回 (content, prompt_tokens, completion_tokens)。
    llm_config 为 None 时使用默认配置（DEFAULT_MEMORY_EXTRACTION_MODEL、max_tokens=4000、temperature=0.3）。
    """
    cfg = llm_config if llm_config is not None else _default_extraction_llm_config()
    client = get_async_openai_client()
    create_kwargs = _llm_config_to_create_kwargs(cfg)
    response = await client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        **create_kwargs,
    )
    content = (response.choices[0].message.content or "") if response.choices else ""
    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else None
    completion_tokens = usage.completion_tokens if usage else None
    return (content, prompt_tokens, completion_tokens)


def wrap_client_with_langsmith(
    client: OpenAI, chat_name: str, labels: dict[str, str]
) -> OpenAI:
    """
    已废弃：直接返回基础客户端，不再使用 wrap_openai

    wrap_openai 会创建多层嵌套的 trace，导致 LangSmith 显示混乱。
    现在改用 langsmith.trace context manager 在 API 调用处手动创建单个 trace。

    Args:
        client: 基础OpenAI客户端
        chat_name: 聊天名称（不再使用）
        labels: 元数据标签（不再使用）

    Returns:
        基础OpenAI客户端（不包装）
    """
    # 直接返回基础客户端，不再使用 wrap_openai
    # trace 在 agent.py 的 _call_openai_api_with_retry 中手动创建
    return client


def _is_pydantic_model_class(obj: object) -> bool:
    """True if obj is a Pydantic BaseModel class (used for structured parse)."""
    return isinstance(obj, type) and issubclass(obj, BaseModel)


@traceable
def openrouter_chat_completion(
    *,
    api_key: str | None = None,
    model: str,
    prompt: str,
    response_format: object = None,
) -> str:
    """
    Call OpenRouter (or any OpenAI-compatible) chat API and return content text.
    Raises ValueError on refusal or empty content.

    When response_format is a Pydantic model class, uses the SDK parse() API so
    the response is validated and message.parsed is populated. When it is a dict
    (e.g. OpenRouter json_schema), uses create() and returns raw message.content.
    """
    from app.core.config import global_config_loaded_from_config_yaml as global_config
    if api_key is None:
        api_key = global_config.agent.api_key
    from app.utils.config import OPENROUTER_BASE_URL
    base_url = OPENROUTER_BASE_URL
    client = OpenAI(api_key=api_key, base_url=base_url)
    create_kwargs: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if response_format is not None:
        print(f"response_format: {response_format}")
        create_kwargs["response_format"] = response_format
        response = client.beta.chat.completions.parse(**create_kwargs)
        print(f"with response_format response: {response}")
    else:
        response = client.chat.completions.create(**create_kwargs)
        print(f"without response_format response: {response}")
    message = response.choices[0].message
    refusal = getattr(message, "refusal", None)
    if refusal:
        raise ValueError(f"OpenRouter 模型拒绝输出结构化结果: {refusal}")
    if response_format is not None and _is_pydantic_model_class(response_format):
        parsed = getattr(message, "parsed", None)
        if parsed is not None:
            if hasattr(parsed, "final_answer"):
                return parsed.final_answer
            return parsed.model_dump_json()
        return message.content or ""
    return message.content or ""


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


def main(prompt: str = "Hello, world!"):
    """
    调用 API 来验证 langsmith 调用正常工作，需要找到对应的 LangSmith API Key
    写入本地 config.yaml 文件，完成后到 LangSmith Web UI 检查 Trace 记录。
    Structured output 需传入 Pydantic 模型类（而非 schema dict），且 prompt 需符合 schema（如要求返回 name/description）。
    """
    class Output(BaseModel):
        name: str
        description: str
    # 必须在调用任何 @traceable 函数之前加载 config，否则 LANGSMITH_TRACING_V2 / LANGCHAIN_API_KEY 未设置，LangSmith 不会上报 trace。
    from app.core.config import global_config_loaded_from_config_yaml  # noqa: F401
    # 传入模型类才能让 SDK 填充 message.parsed；若 prompt 不要求返回 name/description，模型可能返回自然语言，parsed 仍为 None
    default_structured_prompt = (
        "Reply with a single character: give a name and a one-sentence description. "
        "Example: name=Alice, description=She is a friendly engineer."
    )
    effective_prompt = default_structured_prompt if prompt == "Hello, world!" else prompt
    response = openrouter_chat_completion(
        model="google/gemini-2.5-flash-lite",
        prompt=effective_prompt,
        response_format=Output,
    )
    print(f"response: {response}")
    # 确保 trace 在进程退出前已上报（LangSmith 使用后台线程发送）
    try:
        from langsmith import Client
        Client().flush()
    except Exception:
        pass

if __name__ == "__main__":
    cyclopts.run(main)
