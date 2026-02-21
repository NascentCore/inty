import functools
from typing import Any, Optional

from loguru import logger

from app.core.config import Environment, global_config_loaded_from_config_yaml
from app.utils.langsmith_metadata import normalize_langsmith_metadata

try:
    from langsmith import wrappers as langsmith_wrappers
except ImportError:
    langsmith_wrappers = None


def _normalize_contents_to_dicts(contents: Any) -> Any:
    """
    将 contents 中可 model_dump 的项转为 dict，以便 LangSmith _process_gemini_inputs 能构建 messages。
    H1 验证：当 contents 为 types.Content (Pydantic) 时，wrapper 不规范化，导致 trace 中无完整 prompt。
    """
    if contents is None:
        return contents
    if isinstance(contents, str):
        return contents
    if isinstance(contents, list):
        out = []
        for c in contents:
            if hasattr(c, "model_dump"):
                out.append(c.model_dump())
            elif isinstance(c, dict):
                out.append(c)
            else:
                out.append(c)
        return out
    return contents


def _patch_models_to_normalize_contents(client: Any) -> None:
    """在 LangSmith 包装之后，对 generate_content / generate_content_stream 做 contents 规范化。"""
    if not hasattr(client, "models"):
        return

    def make_sync_wrapped(orig: Any) -> Any:
        @functools.wraps(orig)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            if "contents" in kwargs:
                kwargs = {**kwargs, "contents": _normalize_contents_to_dicts(kwargs["contents"])}
            return orig(*args, **kwargs)

        _wrapped._contents_normalized = True  # type: ignore[attr-defined]
        return _wrapped

    for method_name in ("generate_content", "generate_content_stream"):
        original = getattr(client.models, method_name, None)
        if original is None or getattr(original, "_contents_normalized", False):
            continue
        setattr(client.models, method_name, make_sync_wrapped(original))

    def make_async_wrapped(orig: Any) -> Any:
        @functools.wraps(orig)
        async def _awrapped(*args: Any, **kwargs: Any) -> Any:
            if "contents" in kwargs:
                kwargs = {**kwargs, "contents": _normalize_contents_to_dicts(kwargs["contents"])}
            return await orig(*args, **kwargs)

        _awrapped._contents_normalized = True  # type: ignore[attr-defined]
        return _awrapped

    if hasattr(client, "aio") and hasattr(client.aio, "models"):
        for method_name in ("generate_content", "generate_content_stream"):
            original = getattr(client.aio.models, method_name, None)
            if original is None or getattr(original, "_contents_normalized", False):
                continue
            setattr(client.aio.models, method_name, make_async_wrapped(original))


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

    if langsmith_wrappers is None:
        logger.warning(
            "LangSmith wrappers are unavailable, skip Google GenAI tracing wrapper"
        )
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
        wrapped = None
        if tracing_extra and chat_name:
            wrapped = wrap_gemini(
                client,
                tracing_extra=tracing_extra,
                chat_name=chat_name,
            )
        elif tracing_extra:
            wrapped = wrap_gemini(client, tracing_extra=tracing_extra)
        elif chat_name:
            wrapped = wrap_gemini(client, chat_name=chat_name)
        else:
            wrapped = wrap_gemini(client)
        _patch_models_to_normalize_contents(wrapped)
        return wrapped
    except TypeError:
        # 兼容旧版本 wrap_gemini 签名：仅接收 client 参数。
        try:
            wrapped = wrap_gemini(client)
            _patch_models_to_normalize_contents(wrapped)
            return wrapped
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
