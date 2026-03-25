"""终端可读的 LLM 调用摘要（用于 REPL 调试，非生产遥测）。"""

from __future__ import annotations

import threading
from typing import Any

_TRACE_LOCK = threading.Lock()
_TRACE_PREFIX = "[llm-trace]"


def summarize_messages(messages: list[dict[str, Any]], *, preview_len: int = 56) -> str:
    """将 messages 压成单行摘要：角色链、长度、可选内容前缀。"""
    parts: list[str] = []
    for i, m in enumerate(messages):
        role = m.get("role", "?")
        if role == "tool":
            tid = (m.get("tool_call_id") or "")[:10]
            c = m.get("content")
            clen = len(c) if isinstance(c, str) else 0
            parts.append(f"{i}:tool(id…{tid}) {clen}ch")
            continue
        tcs = m.get("tool_calls")
        if role == "assistant" and tcs:
            names: list[str] = []
            for tc in tcs:
                if isinstance(tc, dict):
                    fn = tc.get("function") or {}
                    names.append(str(fn.get("name", "?")))
                else:
                    fn = getattr(tc, "function", None)
                    names.append(getattr(fn, "name", "?") if fn is not None else "?")
            arg_lens = []
            for tc in tcs:
                if isinstance(tc, dict):
                    fn = tc.get("function") or {}
                    a = fn.get("arguments") or ""
                else:
                    fn = getattr(tc, "function", None)
                    a = (fn.arguments if fn is not None else None) or ""
                arg_lens.append(len(a) if isinstance(a, str) else 0)
            detail = ",".join(f"{n}({L}b)" for n, L in zip(names, arg_lens))
            parts.append(f"{i}:assistant→[{detail}]")
            continue
        c = m.get("content")
        if not isinstance(c, str):
            parts.append(f"{i}:{role} <non-str>")
            continue
        prev = c.replace("\n", " ").strip()
        if len(prev) > preview_len:
            prev = prev[: preview_len - 1] + "…"
        parts.append(f"{i}:{role} {len(c)}ch «{prev}»")
    return " | ".join(parts)


def summarize_completion_response(resp: Any) -> str:
    """单次 chat.completions 响应：finish_reason、usage、文本或 tool_calls。"""
    ch0 = resp.choices[0]
    fr = getattr(ch0, "finish_reason", None) or "?"
    msg = ch0.message
    tcs = getattr(msg, "tool_calls", None) or []
    bits: list[str] = [f"finish={fr}"]
    u = getattr(resp, "usage", None)
    if u is not None:
        pt = getattr(u, "prompt_tokens", None)
        ct = getattr(u, "completion_tokens", None)
        tt = getattr(u, "total_tokens", None)
        if pt is not None and ct is not None:
            bits.append(f"tokens p={pt} c={ct}" + (f" t={tt}" if tt is not None else ""))
    if tcs:
        pairs: list[str] = []
        for tc in tcs:
            fn = tc.function
            arglen = len(fn.arguments or "")
            pairs.append(f"{fn.name}({arglen}b)")
        bits.append("tools:[" + ",".join(pairs) + "]")
        return " ".join(bits)
    content = msg.content or ""
    prev = content.replace("\n", " ").strip()
    if len(prev) > 72:
        prev = prev[:71] + "…"
    bits.append(f"text {len(content)}ch «{prev}»")
    return " ".join(bits)


def emit_trace(where: str, *, round_idx: int, model: str, messages: str, response: str) -> None:
    """带锁打印三行 trace，避免与记忆线程交错时行内撕裂。"""
    block = (
        f"{_TRACE_PREFIX} {where} #{round_idx} model={model}\n"
        f"{_TRACE_PREFIX}   req:  {messages}\n"
        f"{_TRACE_PREFIX}   resp: {response}\n"
    )
    with _TRACE_LOCK:
        print(block, end="", flush=True)
