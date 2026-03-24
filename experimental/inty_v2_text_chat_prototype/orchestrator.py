"""Text Turn Orchestrator：唯一将助手回复写入 transcript.jsonl 的入口。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .client import complete
from .file_store import append_jsonl
from .memory_update import memory_update_after_turn
from .models import (
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    ChatMessage,
    load_context_meta,
    load_prompt_bundle,
    load_transcript,
)
from .paths import WorkspacePaths
from .prompts import build_system_prompt


def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_workspace_files(paths: WorkspacePaths) -> None:
    for p in (
        paths.identity,
        paths.soul,
        paths.user_md,
        paths.memory_md,
        paths.transcript,
    ):
        assert p.is_file(), f"missing required file: {p}"


def _truncate_transcript(msgs: list[ChatMessage]) -> list[ChatMessage]:
    if len(msgs) <= TRANSCRIPT_WINDOW_MAX_MESSAGES:
        return msgs
    return msgs[-TRANSCRIPT_WINDOW_MAX_MESSAGES:]


def run_turn(
    workspace: Path,
    user_text: str,
    *,
    debug_print_system: bool = False,
) -> str:
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    _require_workspace_files(paths)

    bundle = load_prompt_bundle(paths)
    context = load_context_meta(paths.context_json)
    transcript = _truncate_transcript(load_transcript(paths.transcript))

    system = build_system_prompt(bundle, context)
    if debug_print_system:
        print(system)
        print("=" * 80)

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for m in transcript:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": user_text})

    assistant_text = complete(messages)

    ts_user = _utc_ts()
    append_jsonl(
        paths.transcript,
        {"role": "user", "content": user_text, "ts": ts_user},
    )
    ts_asst = _utc_ts()
    append_jsonl(
        paths.transcript,
        {"role": "assistant", "content": assistant_text, "ts": ts_asst},
    )

    memory_update_after_turn(paths, user_text=user_text, assistant_text=assistant_text)

    return assistant_text
