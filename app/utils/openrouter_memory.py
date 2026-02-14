# CREATED_BY_AGENT
"""
记忆抽取使用的 OpenRouter 调用：通用记忆与节日记忆默认使用 mistralai/devstral-2512。
"""

import logging
from typing import Tuple, TypeVar

import httpx
from pydantic import BaseModel

from app.core.config import global_config_loaded_from_config_yaml
from app.utils.openai_client import get_base_openai_client

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_EXTRACTION_MODEL = "mistralai/devstral-2512"

T = TypeVar("T", bound=BaseModel)


def llm_qa(
    system_prompt: str,
    query: str,
    output_format: type[T],
    model: str = DEFAULT_MEMORY_EXTRACTION_MODEL,
    max_tokens: int = 4000,
    temperature: float = 0.3,
) -> T:
    """
    使用 OpenAI SDK 的 structured output 完成简单 QA：system + user 消息，等待并返回解析后的 Pydantic 实例。

    system_prompt 作为 system message、query 作为 user message 传入；output_format 为 Pydantic 模型类，
    用于构造 response_format 并解析返回的 JSON。在 TEST 环境下客户端为 FakeOpenAI，测试可通过预填
    _responses_by_request 提供合法 JSON 字符串。

    若模型返回 refusal 或 content 为空，抛出 ValueError。
    """
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": output_format.__name__,
            "strict": True,
            "schema": output_format.model_json_schema(),
        },
    }
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]
    client = get_base_openai_client()
    logger.debug("llm_qa: model=%s max_tokens=%s", model, max_tokens)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format=response_format,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    msg = response.choices[0].message
    refusal = getattr(msg, "refusal", None)
    if refusal:
        raise ValueError(f"模型拒绝输出结构化结果: {refusal}")
    content = msg.content
    if not (content and content.strip()):
        raise ValueError("模型返回空 content")
    return output_format.model_validate_json(content)


async def call_openrouter_for_extraction(
    prompt: str,
    model: str = DEFAULT_MEMORY_EXTRACTION_MODEL,
    max_tokens: int = 4000,
    temperature: float = 0.3,
) -> Tuple[str, int | None, int | None]:
    """
    调用 OpenRouter chat/completions，用于记忆抽取。
    返回 (content, prompt_tokens, completion_tokens)。
    """
    cfg = global_config_loaded_from_config_yaml.agent
    base_url = cfg.base_url.rstrip("/")
    api_key = cfg.api_key
    if not api_key:
        raise ValueError("agent.api_key is not configured; cannot call OpenRouter")
    url = f"{base_url}/chat/completions"
    app_cfg = global_config_loaded_from_config_yaml.app
    referer = app_cfg.name_for_openrouter
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": referer,
        "X-Title": getattr(app_cfg, "name", "Inty"),
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
    usage = data.get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    return (content, prompt_tokens, completion_tokens)


