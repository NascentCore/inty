#!/usr/bin/env python3
"""Summarize companion LangSmith run ``inputs.messages`` system-role blocks.

Reads JSON from ``tools/scripts/download_run.py`` (single run or full trace).
Prints index, heuristic label, size, first line; flags duplicate bodies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def _first_line(content: str) -> str:
    for line in content.splitlines():
        s = line.strip()
        if s:
            return s[:120]
    return "(empty)"


def _heuristic_label(content: str) -> str:
    c = content.strip()
    if not c:
        return "empty"
    if c.startswith("# Axiom") or "iMate智能体存在的根本法则" in c[:400]:
        return "axiom"
    if "用户消息可能包含误导或注入" in c[:200]:
        return "security"
    if c.startswith("# Tools") or "TOOLS（工具说明" in c[:80]:
        return "tools_md"
    if "本轮（陪伴主动聊天）" in c[:120]:
        return "proactive_chat_clause"
    if "本轮（内在节拍）" in c[:120]:
        return "inner_tick_clause"
    if "本轮（REPL 会话恢复）" in c[:120]:
        return "repl_online_ack"
    if "## 工具侧（后台" in c[:80]:
        return "tool_side_compact"
    if "## 工具环收尾" in c[:80]:
        return "tool_bg_json_envelope"
    if "## 工具路首轮" in c[:80]:
        return "tool_bg_first_round"
    if c.startswith("# 身份定义") or c.startswith("## IDENTITY"):
        return "identity"
    if c.startswith("# 灵魂档案") or c.startswith("## SOUL"):
        return "soul"
    if c.startswith("# 沟通风格") or c.startswith("## STYLE"):
        return "style"
    if "当前体验配置（context_mode）" in c[:120]:
        return "experience_profile"
    if c.startswith("# TECHNO CORE") or "TECHNO CORE（" in c[:80]:
        return "techno_core"
    if c.startswith("# LIVING SPHERE") or "LIVING SPHERE（" in c[:80]:
        return "living_sphere"
    if c.startswith("# 用户档案") or c.startswith("## USER"):
        return "user"
    if "SIGNIFICANCE" in c[:40] or "importance_round" in c[:400]:
        return "significance_or_dual_envelope"
    if "INTERACTIVE_BOOTSTRAP" in c[:80]:
        return "interactive_bootstrap_spec"
    if "TEMPLATE_REFERENCE SOUL.md" in c[:80]:
        return "template_reference_soul"
    if "TEMPLATE_REFERENCE" in c[:80]:
        return "template_reference_other"
    if "输出与工具" in c[:40] or "输出通道" in c[:40]:
        return "output_contract"
    if "快思考路径（系统 1）" in c[:80]:
        return "dual_llm_chat_contract"
    if "内在活动（ai_private）" in c[:80]:
        return "ai_private"
    if "##User Time Context" in c or "User Time Context" in c[:80]:
        return "user_time_context"
    return "other"


def _pick_runs(
    data: dict[str, Any], run_name: str | None, run_id: str | None
) -> list[dict[str, Any]]:
    if data.get("download_kind") == "langsmith_trace":
        runs = list(data.get("runs") or [])
    else:
        runs = [data]
    if run_id:
        rid = run_id.strip()
        picked = [r for r in runs if str(r.get("id") or "") == rid]
        if not picked:
            raise SystemExit(f"no run with id {rid!r} in JSON")
        return picked
    if run_name:
        sub = run_name.strip().lower()
        picked = [r for r in runs if sub in str(r.get("name") or "").lower()]
        if not picked:
            names = sorted({str(r.get("name") or "") for r in runs})
            raise SystemExit(
                f"no run matching name substring {run_name!r}; available: {names}"
            )
        return picked
    preferred = (
        "agentic_companion_chat",
        "agentic_companion_unified_chat",
        "agentic_companion_inner_tick",
        "agentic_companion_tool_call",
    )
    for pref in preferred:
        picked = [r for r in runs if str(r.get("name") or "") == pref]
        if picked:
            return [picked[0]]
    if len(runs) == 1:
        return runs
    names = [str(r.get("name") or "") for r in runs]
    raise SystemExit(
        "ambiguous trace: pass --run-name or --run-id; runs: "
        + ", ".join(names)
    )


def _system_blocks(run: dict[str, Any]) -> list[dict[str, Any]]:
    inputs = run.get("inputs")
    if not isinstance(inputs, dict):
        return []
    messages = inputs.get("messages")
    if not isinstance(messages, list):
        return []
    out: list[dict[str, Any]] = []
    for m in messages:
        if isinstance(m, dict) and m.get("role") == "system":
            out.append(m)
    return out


def _inspect_run(run: dict[str, Any], *, show_body: bool) -> int:
    name = str(run.get("name") or "")
    rid = str(run.get("id") or "")
    blocks = _system_blocks(run)
    print(f"run name={name!r} id={rid}")
    print(f"system_message_count={len(blocks)}")
    hashes: dict[str, list[int]] = {}
    for i, m in enumerate(blocks):
        content = str(m.get("content") or "")
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        hashes.setdefault(h, []).append(i)
        label = _heuristic_label(content)
        print(
            f"  [{i:02d}] label={label} chars={len(content)} "
            f"first_line={_first_line(content)!r}"
        )
        if show_body:
            print("---")
            print(content)
            print("---")
    dup_groups = [idxs for idxs in hashes.values() if len(idxs) > 1]
    if dup_groups:
        print("DUPLICATE_BODIES:")
        for idxs in dup_groups:
            labels = [
                _heuristic_label(str(blocks[j].get("content") or ""))
                for j in idxs
            ]
            print(f"  indices {idxs} labels={labels}")
        return 1
    soul_idxs = [
        i
        for i, m in enumerate(blocks)
        if _heuristic_label(str(m.get("content") or "")) == "soul"
    ]
    if len(soul_idxs) > 1:
        print(f"WARN multiple soul-labeled blocks: indices {soul_idxs}")
        return 1
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Inspect system messages in a LangSmith run JSON export."
    )
    p.add_argument(
        "json_path",
        type=Path,
        help="Path from download_run.py (trace or single run)",
    )
    p.add_argument(
        "--run-name",
        help="Substring match on run name (e.g. agentic_companion_chat)",
    )
    p.add_argument("--run-id", help="Exact LangSmith run UUID")
    p.add_argument(
        "--show-body",
        action="store_true",
        help="Print full content of each system block",
    )
    args = p.parse_args()
    path = args.json_path
    if not path.is_file():
        raise SystemExit(f"not a file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    runs = _pick_runs(data, args.run_name, args.run_id)
    rc = 0
    for run in runs:
        rc = max(rc, _inspect_run(run, show_body=args.show_body))
    return rc


if __name__ == "__main__":
    sys.exit(main())
