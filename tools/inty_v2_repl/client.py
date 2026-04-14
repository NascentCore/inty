"""单次 chat.completions 调用（内层，不拼业务 system）。"""

from __future__ import annotations

import atexit
import json
import os
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI

from app.core.agentic_kernel.providers.facade import (
    OpenAICompatibleClientOptions,
    get_openai_compatible_sync_client,
)
from .env_util import env_flag_enabled

_DEFAULT_MODEL = "google/gemini-2.5-flash"

_CLIENT: OpenAI | None = None
# 双路并行（chat 无 tools + tool 全量）：LangSmith 中需区分 run 名称，故分两个 wrap_openai 实例。
_CLIENT_DUAL_LLM_CHAT: OpenAI | None = None
_CLIENT_DUAL_LLM_TOOL: OpenAI | None = None
_OPENROUTER_JSON_MAX_ATTEMPTS = 3
_OPENROUTER_JSON_BACKOFF_SECONDS = (0.25, 0.75)


class OpenRouterInvalidJsonError(RuntimeError):
    """OpenRouter returned a response body that was not valid JSON."""


def _register_module_aliases() -> None:
    """
    Keep one shared module object for both import paths:
    - experimental.inty_v2_text_chat_prototype.client
    - inty_v2_text_chat_prototype.client
    This avoids exception class identity mismatch in mixed import styles.
    """
    module = sys.modules[__name__]
    sys.modules.setdefault("experimental.inty_v2_text_chat_prototype.client", module)
    sys.modules.setdefault("inty_v2_text_chat_prototype.client", module)


_register_module_aliases()


def _flush_langsmith_traces_on_exit() -> None:
    from langsmith import utils as ls_utils

    if ls_utils.tracing_is_enabled() is not True:
        return
    from langsmith.run_trees import get_cached_client

    try:
        get_cached_client().flush()
    except RuntimeError:
        pass


atexit.register(_flush_langsmith_traces_on_exit)


def load_prototype_dotenv() -> None:
    """Load cwd `.env` first, then package `.env` for keys still unset (repo-root cwd)."""
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent / ".env")


def _ensure_dotenv() -> None:
    load_prototype_dotenv()


def _prototype_langsmith_wrap_enabled() -> bool:
    """Only wrap OpenAI when LangSmith tracing is on; avoids 403 spam when tracing is off or key invalid."""
    _ensure_dotenv()
    from langsmith import utils as ls_utils

    return ls_utils.tracing_is_enabled() is True


def get_client() -> OpenAI:
    global _CLIENT
    _ensure_dotenv()
    if _CLIENT is not None:
        return _CLIENT
    key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if not key:
        raise ValueError(
            "Missing API key: set OPENROUTER_API_KEY in the environment "
            "(or a .env file loaded by python-dotenv)."
        )
    base_url = "https://openrouter.ai/api/v1"
    logger.info(
        "IntyV2Proto LLM client: api_key_env=OPENROUTER_API_KEY base_url={}",
        base_url,
    )
    _CLIENT = get_openai_compatible_sync_client(
        OpenAICompatibleClientOptions(
            base_url=base_url,
            api_key=key,
            wrap_langsmith=_prototype_langsmith_wrap_enabled(),
            chat_name="IntyV2Proto_ChatOpenAI",
            completions_name="IntyV2Proto_OpenAI",
            use_fake_openai=False,
        )
    )
    return _CLIENT


def _openrouter_langsmith_options(*, chat_name: str) -> OpenAICompatibleClientOptions:
    """与 `get_client()` 相同 endpoint/key，仅 `chat_name` 用于 LangSmith 区分 run。"""
    _ensure_dotenv()
    key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if not key:
        raise ValueError(
            "Missing API key: set OPENROUTER_API_KEY in the environment "
            "(or a .env file loaded by python-dotenv)."
        )
    return OpenAICompatibleClientOptions(
        base_url="https://openrouter.ai/api/v1",
        api_key=key,
        wrap_langsmith=_prototype_langsmith_wrap_enabled(),
        chat_name=chat_name,
        completions_name="IntyV2Proto_OpenAI",
        use_fake_openai=False,
    )


def get_client_dual_llm_chat() -> OpenAI:
    """
    不挂载 tools 的「聊天路」completion（双路 chat 支路、async 前台快回等）；
    LangSmith run 名：IntyV2Proto_DualLlm_Chat。
    """
    global _CLIENT_DUAL_LLM_CHAT
    if _CLIENT_DUAL_LLM_CHAT is None:
        _CLIENT_DUAL_LLM_CHAT = get_openai_compatible_sync_client(
            _openrouter_langsmith_options(chat_name="IntyV2Proto_DualLlm_Chat")
        )
    return _CLIENT_DUAL_LLM_CHAT


def get_client_dual_llm_tool() -> OpenAI:
    """
    挂载 tools 的 LLM 调用（双路 tool 支路、async 后台 tool loop、同步单路带 tools、
    bootstrap 等）；LangSmith run 名：IntyV2Proto_DualLlm_Tool。
    """
    global _CLIENT_DUAL_LLM_TOOL
    if _CLIENT_DUAL_LLM_TOOL is None:
        _CLIENT_DUAL_LLM_TOOL = get_openai_compatible_sync_client(
            _openrouter_langsmith_options(chat_name="IntyV2Proto_DualLlm_Tool")
        )
    return _CLIENT_DUAL_LLM_TOOL


def default_model() -> str:
    _ensure_dotenv()
    return os.getenv("INTY_V2_PROTO_MODEL", _DEFAULT_MODEL)


def chat_model() -> str:
    """主聊天通道模型（低延迟优先）；缺省回退到 INTY_V2_PROTO_MODEL。"""
    _ensure_dotenv()
    return os.getenv("INTY_V2_PROTO_CHAT_MODEL") or default_model()


def tool_model() -> str:
    """工具通道模型（工具调用能力优先）；缺省回退到 INTY_V2_PROTO_MODEL。"""
    _ensure_dotenv()
    return os.getenv("INTY_V2_PROTO_TOOL_MODEL") or default_model()


def tool_path_chat_completion_kwargs(model: str) -> dict[str, Any]:
    """
    OpenRouter ``chat.completions.create`` 的额外参数：仅用于**挂载 tools** 的调用（工具选型、参数构造）。

    - DeepSeek：``extra_body.reasoning.effort=high``，``exclude=True`` 避免推理内容进入对用户可见的 assistant 文本。
    - Gemini：``reasoning_effort=high``（与 ``experimental/thinking_token_handling`` 一致）。

    关闭：``INTY_V2_PROTO_TOOL_THINKING=0`` / ``false`` / ``no`` / ``off`` / ``none``。
    其它模型暂不注入，避免不支持的参数导致 400。
    """
    _ensure_dotenv()
    raw = os.environ.get("INTY_V2_PROTO_TOOL_THINKING")
    if raw is not None and str(raw).strip().lower() in (
        "0",
        "false",
        "no",
        "off",
        "none",
    ):
        return {}

    from app.utils.models_catalog import is_deepseek_on_openrouter, is_gemini_model

    if is_deepseek_on_openrouter(model):
        return {"extra_body": {"reasoning": {"effort": "high", "exclude": True}}}
    if is_gemini_model(model):
        return {"reasoning_effort": "high"}
    return {}


def create_chat_completion(
    client: Any,
    *,
    model: str,
    messages_payload: list[dict[str, Any]],
    tools: list[Any],
    tool_choice: str | None = None,
) -> Any:
    create_kw: dict[str, Any] = {
        "model": model,
        "messages": deepcopy(messages_payload),
    }
    if tools:
        create_kw.update(tool_path_chat_completion_kwargs(model))
        create_kw["tools"] = tools
        create_kw["parallel_tool_calls"] = True
        if tool_choice is not None:
            create_kw["tool_choice"] = tool_choice
    for attempt in range(1, _OPENROUTER_JSON_MAX_ATTEMPTS + 1):
        try:
            return client.chat.completions.create(**create_kw)
        except json.JSONDecodeError as exc:
            retryable = attempt < _OPENROUTER_JSON_MAX_ATTEMPTS
            logger.warning(
                "llm.chat_completions invalid_json_response model={} attempt={}/{} retryable={} err={}",
                model,
                attempt,
                _OPENROUTER_JSON_MAX_ATTEMPTS,
                retryable,
                exc,
            )
            if retryable:
                delay = _OPENROUTER_JSON_BACKOFF_SECONDS[min(attempt - 1, 1)]
                time.sleep(delay)
                continue
            raise OpenRouterInvalidJsonError(
                "OpenRouter returned a non-JSON response body "
                f"for model={model} after {_OPENROUTER_JSON_MAX_ATTEMPTS} attempts."
            ) from exc


def dual_llm_enabled() -> bool:
    """是否启用双路并行 LLM（聊天路 + 工具路）。"""
    _ensure_dotenv()
    return env_flag_enabled("INTY_V2_PROTO_DUAL_LLM")


def async_tool_background_enabled() -> bool:
    """
    “chat 先回 + tool 后台异步补发”模式。

    默认开启：前台一次无 tools 的 chat.completions，立即返回并落 transcript(source=chat)；
    工具路在同轮快照上后台跑，若有 tool_calls 则结束后再追加 transcript(source=tool_bg) 并投递 REPL 事件。

    显式关闭：INTY_V2_PROTO_ASYNC_TOOL_BG=0|false|no|off（恢复同步 tool loop，与双路 INTY_V2_PROTO_DUAL_LLM 可组合）。
    """
    _ensure_dotenv()
    raw = os.environ.get("INTY_V2_PROTO_ASYNC_TOOL_BG")
    if raw is None or not str(raw).strip():
        return True
    s = str(raw).strip().lower()
    if s in ("0", "false", "no", "off"):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    raise ValueError(
        f"Invalid INTY_V2_PROTO_ASYNC_TOOL_BG={raw!r}; use 1/true or 0/false, or unset for default (on)"
    )


def memory_model() -> str:
    _ensure_dotenv()
    return os.getenv("INTY_V2_PROTO_MEMORY_MODEL") or default_model()


def day_summary_model() -> str:
    """当日总结性记忆（memory/YYYY-MM-DD.md）；可与长期 MEMORY 策展使用不同模型。"""
    _ensure_dotenv()
    return os.getenv("INTY_V2_PROTO_DAY_SUMMARY_MODEL") or memory_model()


def soul_model() -> str:
    """SOUL.md 策展（边界与价值观落盘）；默认与记忆策展同模型。"""
    _ensure_dotenv()
    return os.getenv("INTY_V2_PROTO_SOUL_MODEL") or memory_model()


def user_model() -> str:
    """USER.md 策展（用户对助手可见的长期画像）；默认与记忆策展同模型。"""
    _ensure_dotenv()
    return os.getenv("INTY_V2_PROTO_USER_MODEL") or memory_model()


def complete(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    llm_trace: bool = False,
    trace_where: str = "complete",
    ws_label: str,
    trace_day: str,
) -> str:
    m = model or default_model()
    client = get_client()
    msg_chars = 0
    for mm in messages:
        c = mm.get("content")
        if isinstance(c, str):
            msg_chars += len(c)
    logger.debug(
        "llm.chat_completions req where={} model={} ws={} day={} messages_n={} content_chars={}",
        trace_where,
        m,
        ws_label,
        trace_day,
        len(messages),
        msg_chars,
    )
    t0 = time.perf_counter()
    resp = create_chat_completion(
        client,
        model=m,
        messages_payload=messages,
        tools=[],
    )
    ch0 = resp.choices[0]
    fr = getattr(ch0, "finish_reason", None) or "?"
    u = getattr(resp, "usage", None)
    tok_dbg = ""
    if u is not None:
        pt = getattr(u, "prompt_tokens", None)
        ct = getattr(u, "completion_tokens", None)
        if pt is not None and ct is not None:
            tok_dbg = f" usage_p={pt} c={ct}"
    logger.debug(
        "llm.chat_completions resp where={} finish_reason={}{}",
        trace_where,
        fr,
        tok_dbg,
    )
    logger.info(
        "llm.chat_completions where={} model={} ws={} ms={:.0f}",
        trace_where,
        m,
        ws_label,
        (time.perf_counter() - t0) * 1000.0,
    )
    if llm_trace:
        from .llm_trace import (
            emit_trace,
            summarize_completion_response,
            summarize_messages,
        )

        emit_trace(
            trace_where,
            round_idx=1,
            model=m,
            messages=summarize_messages(
                messages,
                ws_label=ws_label,
                trace_day=trace_day,
            ),
            response=summarize_completion_response(resp),
        )
    content = resp.choices[0].message.content
    return content if content is not None else ""
