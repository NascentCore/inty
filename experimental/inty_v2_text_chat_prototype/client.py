"""单次 chat.completions 调用（内层，不拼业务 system）。"""

from __future__ import annotations

import atexit
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langsmith.wrappers import wrap_openai
from loguru import logger
from openai import OpenAI

_DEFAULT_MODEL = "deepseek/deepseek-v3.2"

_CLIENT: OpenAI | None = None

# experimental/inty_v2_text_chat_prototype/client.py → parents[2] = inty repo root
_REPO_ROOT_FOR_DOTENV = Path(__file__).resolve().parent.parent.parent

# LangSmith `tracing_is_enabled()` only treats the literal lowercase string "true" as on.
_LANGSMITH_TRACING_TRUTHY = frozenset({"1", "yes", "on", "true"})


def _coerce_langsmith_tracing_env() -> None:
    for key in (
        "LANGSMITH_TRACING_V2",
        "LANGSMITH_TRACING",
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_TRACING",
    ):
        raw = os.environ.get(key)
        if raw is None or not str(raw).strip():
            continue
        if str(raw).strip().lower() in _LANGSMITH_TRACING_TRUTHY:
            os.environ[key] = "true"


def _flush_langsmith_traces_on_exit() -> None:
    from langsmith import utils as ls_utils

    if ls_utils.tracing_is_enabled() is not True:
        return
    from langsmith.run_trees import get_cached_client

    get_cached_client().flush()


atexit.register(_flush_langsmith_traces_on_exit)


def load_prototype_dotenv() -> None:
    """Load `inty/.env` first, then cwd `.env` (e.g. OPENROUTER_API_KEY); cwd may differ from repo root."""
    load_dotenv(_REPO_ROOT_FOR_DOTENV / ".env")
    load_dotenv()
    _coerce_langsmith_tracing_env()


def _ensure_dotenv() -> None:
    load_prototype_dotenv()


def get_client() -> OpenAI:
    global _CLIENT
    _ensure_dotenv()
    if _CLIENT is not None:
        return _CLIENT
    key = (os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise ValueError(
            "Missing API key: set OPENROUTER_API_KEY or OPENAI_API_KEY in the environment "
            "(or a .env file loaded by python-dotenv)."
        )
    if os.getenv("OPENROUTER_API_KEY"):
        base = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=key,
        )
    else:
        base = OpenAI(api_key=key)
    _CLIENT = wrap_openai(
        base,
        chat_name="IntyV2Proto_ChatOpenAI",
        completions_name="IntyV2Proto_OpenAI",
    )
    return _CLIENT


def default_model() -> str:
    _ensure_dotenv()
    return os.getenv("INTY_V2_PROTO_MODEL", _DEFAULT_MODEL)


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
    resp = client.chat.completions.create(model=m, messages=messages)
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
        from .llm_trace import emit_trace, summarize_completion_response, summarize_messages

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
