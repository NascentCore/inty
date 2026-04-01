from typing import Any, Optional

from loguru import logger

from app.core.config import Environment, global_config_loaded_from_config_yaml
from app.utils.langsmith_metadata import normalize_langsmith_metadata
from langsmith import wrappers as langsmith_wrappers


def wrap_google_genai_client_with_langsmith(
    client: Any,
    *,
    tags: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
    chat_name: Optional[str] = None,
) -> Any:
    """
    使用 LangSmith 包装 google.genai 客户端。

    约定：
    - 测试环境直接返回原客户端，避免影响 fake client 和测试稳定性。
    - LangSmith 不可用或包装失败时，自动回退原客户端，避免阻断主流程。
    """

    if global_config_loaded_from_config_yaml.app.environment == Environment.TEST:
        return client

    wrap_gemini = getattr(langsmith_wrappers, "wrap_gemini", None)
    if wrap_gemini is None:
        logger.warning("LangSmith wrappers.wrap_gemini is unavailable")
        return client

    tracing_extra: dict[str, Any] = {}
    if tags:
        tracing_extra["tags"] = [str(tag) for tag in tags]

    normalized_metadata = normalize_langsmith_metadata(metadata)
    if normalized_metadata:
        tracing_extra["metadata"] = normalized_metadata

    try:
        if tracing_extra and chat_name:
            return wrap_gemini(
                client,
                tracing_extra=tracing_extra,
                chat_name=chat_name,
            )
        if tracing_extra:
            return wrap_gemini(client, tracing_extra=tracing_extra)
        if chat_name:
            return wrap_gemini(client, chat_name=chat_name)
        return wrap_gemini(client)
    except TypeError:
        # 兼容旧版本 wrap_gemini 签名：仅接收 client 参数。
        try:
            return wrap_gemini(client)
        except Exception as error:
            logger.warning(
                "Failed to wrap Google GenAI client with LangSmith: {}",
                str(error),
            )
            return client
    except Exception as error:
        logger.warning(
            "Failed to wrap Google GenAI client with LangSmith: {}",
            str(error),
        )
        return client
