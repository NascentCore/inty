"""LLM 调用摘要写入可选 trace 文件（JSONL，每轮一行；用于调试，非生产遥测）。"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .jsonl_db_store import append_jsonl_with_db
from .prompts import SYSTEM_PROMPT_SEP, system_prompt_security_prefix

_TRACE_LOCK = threading.Lock()
_trace_file_path: Path | None = None
LLM_TRACE_JSONL_VERSION = 1

# In-memory OpenAI message dicts may carry this key; stripped before API calls.
TRANSCRIPT_MSG_UUID_KEY = "_transcript_uuid"


def configure_llm_trace_file(path: Path | None) -> None:
    """由 main 入口设置；None 表示不写入文件。"""
    global _trace_file_path
    _trace_file_path = path.resolve() if path is not None else None


def is_system_prompt_bundle(content: str) -> bool:
    """是否为 build_system_prompt 拼出的主会话 system（按分隔符 + 首段 security）。"""
    if SYSTEM_PROMPT_SEP not in content:
        return False
    head = content.split(SYSTEM_PROMPT_SEP, 1)[0].strip()
    return head == system_prompt_security_prefix().strip()


def _label_system_segment(seg: str, *, ws_label: str, day: str) -> str:
    """单段 → 人类可读路径标签（与 prompts.build_system_prompt 段首一致）。"""
    s = seg.lstrip()
    if s.startswith("你是情感伴侣型助手"):
        return f"{ws_label}/security"
    if s.startswith("## AGENTS（工作空间约定）"):
        return f"{ws_label}/AGENTS.md"
    if s.startswith("## TOOLS（本地工具配置）"):
        return f"{ws_label}/TOOLS.md"
    if s.startswith("## HEARTBEAT（检查清单）"):
        return f"{ws_label}/HEARTBEAT.md"
    if s.startswith("## IDENTITY"):
        return f"{ws_label}/IDENTITY.md"
    if s.startswith("## SOUL"):
        return f"{ws_label}/SOUL.md"
    if s.startswith("当前上下文模式："):
        return f"{ws_label}/context.json"
    if s.startswith("## USER"):
        return f"{ws_label}/USER.md"
    if s.startswith("## MEMORY 日记（今日原始）"):
        return f"{ws_label}/memory/daily/{day}.md"
    if s.startswith("## MEMORY 当日总结"):
        return f"{ws_label}/memory/{day}.md"
    if s.startswith("## MEMORY（长期记忆定稿）"):
        return f"{ws_label}/MEMORY.md"
    if s.startswith("输出通道：") or s.startswith("输出与工具："):
        return f"{ws_label}/output_contract"
    return f"unknown({len(seg)}ch)"


def summarize_system_message_content(content: str, *, ws_label: str, day: str) -> str:
    """将 bundle 形 system 压成「总长 + @⟨段标签⟩」单行。"""
    labels: list[str] = []
    for seg in content.split(SYSTEM_PROMPT_SEP):
        labels.append(_label_system_segment(seg, ws_label=ws_label, day=day))
    inner = ",".join(labels)
    return f"{len(content)}ch @⟨{inner}⟩"


def summarize_messages(
    messages: list[dict[str, Any]],
    ws_label: str,
    trace_day: str,
    *,
    preview_len: int = 56,
) -> str:
    """将 messages 压成单行摘要：角色链、长度、可选内容前缀或 bundle 引用。"""
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
        if role == "system" and is_system_prompt_bundle(c):
            parts.append(
                f"{i}:system {summarize_system_message_content(c, ws_label=ws_label, day=trace_day)}"
            )
            continue
        tid = m.get(TRANSCRIPT_MSG_UUID_KEY)
        if role in ("user", "assistant", "system") and isinstance(tid, str) and tid:
            parts.append(f"{i}:{role} transcript⟨{tid}⟩")
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
            bits.append(
                f"tokens p={pt} c={ct}" + (f" t={tt}" if tt is not None else "")
            )
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


def emit_trace(
    where: str,
    *,
    round_idx: int,
    model: str,
    messages: str,
    response: str,
    trace_id: str | None = None,
) -> None:
    """带锁追加一行 JSONL 到已配置路径，避免与记忆线程交错时行内撕裂。"""
    row: dict[str, Any] = {
        "v": LLM_TRACE_JSONL_VERSION,
        "kind": "llm_trace",
        "where": where,
        "round_idx": round_idx,
        "model": model,
        "req": messages,
        "resp": response,
    }
    if trace_id is not None and trace_id.strip():
        row["trace_id"] = trace_id
    with _TRACE_LOCK:
        path = _trace_file_path
        if path is None:
            return
        append_jsonl_with_db(path, row)
