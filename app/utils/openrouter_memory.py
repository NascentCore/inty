# CREATED_BY_AGENT
"""
记忆抽取使用的 OpenRouter 调用：通用记忆与节日记忆默认使用 mistralai/devstral-2512。
"""

from typing import Tuple

import httpx

from app.core.config import global_config_loaded_from_config_yaml

DEFAULT_MEMORY_EXTRACTION_MODEL = "mistralai/devstral-2512"


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
        raise ValueError("agent.api_key 未配置，无法调用 OpenRouter")
    url = f"{base_url}/chat/completions"
    app_cfg = global_config_loaded_from_config_yaml.app
    referer = app_cfg.name_for_openrouter()
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
    content = (
        data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
    )
    usage = data.get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    return (content, prompt_tokens, completion_tokens)
