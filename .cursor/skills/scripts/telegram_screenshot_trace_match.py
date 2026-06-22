#!/usr/bin/env python3
"""Match a Telegram chat screenshot to LangSmith companion traces and log grep hints.

Generated entirely by Cursor agent — helper for telegram-screenshot-trace-match skill.

Reads screenshot hints (local timestamps, distinctive message snippets), scans
LangSmith ``agentic_companion_user_turn`` root runs in a UTC window across
Inty backend projects, and ranks matches by keyword hits + telegram channel metadata.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any
from zoneinfo import ZoneInfo

import cyclopts
import yaml
from langsmith import Client

_USER_TURN_NAME = "agentic_companion_user_turn"
_TELEGRAM_CHANNEL = "telegram"
_INTY_PROJECT_PREFIX = "inty-backend"
_LANGSMITH_PUBLIC_TRACE_URL = "https://smith.langchain.com/public/{trace_id}/r"


@dataclass(frozen=True)
class SearchWindow:
    """UTC half-open interval [start, end) for LangSmith list_runs."""

    start_utc: datetime
    end_utc: datetime


@dataclass(frozen=True)
class TraceMatch:
    """One ranked LangSmith trace candidate."""

    project_name: str
    trace_id: str
    root_run_id: str
    start_time_utc: datetime
    agent_id: str
    user_id: str
    runtime_channel: str
    keyword_hits: tuple[str, ...]
    user_snippet: str
    reply_snippet: str
    score: int


def _local_username_slug() -> str:
    user = (os.getenv("USER") or os.getenv("USERNAME") or "").strip()
    if not user:
        try:
            user = getpass.getuser()
        except Exception:
            user = ""
    if not user:
        user = "unknown"
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in user)
    parts = [p for p in safe.split("-") if p]
    return "-".join(parts) if parts else "unknown"


def _langchain_api_key(yaml_data: dict[str, Any] | None) -> str | None:
    if isinstance(yaml_data, dict):
        agent = yaml_data.get("agent")
        if isinstance(agent, dict):
            raw = agent.get("langchain_api_key")
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
    for env_name in ("LANGCHAIN_API_KEY", "LANGSMITH_API_KEY"):
        value = (os.environ.get(env_name) or "").strip()
        if value:
            return value
    return None


def _load_yaml_config(config_path: Path) -> dict[str, Any] | None:
    if not config_path.is_file():
        return None
    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else None


def _parse_local_clock(
    *,
    clock_text: str,
    calendar_date: date,
    tz: ZoneInfo,
) -> datetime:
    """Parse HH:MM or YYYY-MM-DD HH:MM[:SS] in ``tz``."""
    text = clock_text.strip()
    assert text != ""
    if re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", text):
        parts = text.split(":")
        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) > 2 else 0
        return datetime(
            calendar_date.year,
            calendar_date.month,
            calendar_date.day,
            hour,
            minute,
            second,
            tzinfo=tz,
        )
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def _build_search_window(
    *,
    screenshot_clock: str,
    calendar_date: date,
    tz_name: str,
    padding_minutes: int,
) -> SearchWindow:
    tz = ZoneInfo(tz_name)
    local_center = _parse_local_clock(
        clock_text=screenshot_clock,
        calendar_date=calendar_date,
        tz=tz,
    )
    pad = timedelta(minutes=padding_minutes)
    start_local = local_center - pad
    end_local = local_center + pad
    return SearchWindow(
        start_utc=start_local.astimezone(timezone.utc),
        end_utc=end_local.astimezone(timezone.utc),
    )


def _candidate_projects(
    client: Client,
    *,
    environment_hint: str,
    explicit_projects: tuple[str, ...],
) -> list[str]:
    if explicit_projects:
        return list(explicit_projects)
    all_projects = [project.name for project in client.list_projects(limit=100)]
    inty_projects = [
        name
        for name in all_projects
        if name.startswith(_INTY_PROJECT_PREFIX)
    ]
    match environment_hint:
        case "dev":
            preferred = [name for name in inty_projects if name.endswith("-dev")]
            return preferred or inty_projects
        case "local":
            preferred = [
                name for name in inty_projects if "-local-" in name or name.endswith("-local")
            ]
            return preferred or inty_projects
        case "prod":
            preferred = [name for name in inty_projects if name.endswith("-prod")]
            return preferred or inty_projects
        case _:
            return inty_projects


def _parse_turn_name(name: str) -> tuple[str, str]:
    user_id = ""
    agent_id = ""
    for token in name.split():
        if token.startswith("user="):
            user_id = token.removeprefix("user=")
        if token.startswith("agent="):
            agent_id = token.removeprefix("agent=")
    return user_id, agent_id


def _run_metadata_channel(run_obj: Any) -> str:
    extra = getattr(run_obj, "extra", None) or {}
    metadata = extra.get("metadata") if isinstance(extra, dict) else {}
    if not isinstance(metadata, dict):
        return ""
    for key in ("inty_runtime_channel", "runtime_channel"):
        raw = metadata.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip().lower()
    return ""


def _extract_last_user_snippet(messages: list[Any]) -> str:
    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        if "SYSTEM PROACTIVE CHAT" in content:
            continue
        if "] " in content:
            return content.split("] ", 1)[-1][:120]
        return content[:120]
    return ""


def _extract_reply_snippet(outputs: dict[str, Any] | None) -> str:
    if not isinstance(outputs, dict):
        return ""
    choices = outputs.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if not isinstance(content, str):
        return ""
    text = content.strip()
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            reply = payload.get("user_facing_reply")
            if isinstance(reply, str) and reply.strip():
                return reply.strip()[:160]
    return text[:160]


def _keyword_hits(blob: str, keywords: tuple[str, ...]) -> tuple[str, ...]:
    hits: list[str] = []
    for keyword in keywords:
        if keyword and keyword in blob:
            hits.append(keyword)
    return tuple(hits)


def _score_match(
    *,
    keyword_hits: tuple[str, ...],
    runtime_channel: str,
    require_telegram: bool,
) -> int:
    score = len(keyword_hits) * 10
    if runtime_channel == _TELEGRAM_CHANNEL:
        score += 5
    elif require_telegram:
        score -= 20
    return score


def _list_user_turn_roots(
    client: Client,
    *,
    project_name: str,
    window: SearchWindow,
    max_roots: int,
) -> list[Any]:
    runs = list(
        client.list_runs(
            project_name=project_name,
            start_time=window.start_utc,
            limit=min(max_roots, 100),
            is_root=True,
        )
    )
    filtered: list[Any] = []
    for run in runs:
        start_time = getattr(run, "start_time", None)
        if start_time is None:
            continue
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if start_time >= window.end_utc:
            continue
        name = str(getattr(run, "name", "") or "")
        if _USER_TURN_NAME not in name:
            continue
        filtered.append(run)
    return filtered


def _inspect_root_run(
    client: Client,
    *,
    project_name: str,
    root_run: Any,
    keywords: tuple[str, ...],
    require_telegram: bool,
    read_delay_seconds: float,
) -> TraceMatch | None:
    trace_id = str(getattr(root_run, "trace_id", "") or "")
    root_run_id = str(getattr(root_run, "id", "") or "")
    if not trace_id or not root_run_id:
        return None

    time.sleep(read_delay_seconds)
    try:
        full = client.read_run(root_run_id, load_child_runs=True)
    except Exception:
        return None

    user_id, agent_id = _parse_turn_name(str(getattr(full, "name", "") or ""))
    runtime_channel = _run_metadata_channel(full)
    if require_telegram and runtime_channel not in ("", _TELEGRAM_CHANNEL):
        return None

    messages = (full.inputs or {}).get("messages", [])
    user_snippet = ""
    if isinstance(messages, list):
        user_snippet = _extract_last_user_snippet(messages)

    blob_parts = [json.dumps(full.inputs or {}, ensure_ascii=False, default=str)]
    reply_snippet = ""
    for child in full.child_runs or []:
        child_name = str(getattr(child, "name", "") or "")
        if child_name not in (
            "agentic_companion_chat",
            "tool_background_initial",
            "tool_background_routing_fallback",
        ):
            continue
        time.sleep(read_delay_seconds)
        try:
            child_full = client.read_run(str(child.id))
        except Exception:
            continue
        child_messages = (child_full.inputs or {}).get("messages", [])
        if not user_snippet and isinstance(child_messages, list):
            user_snippet = _extract_last_user_snippet(child_messages)
        blob_parts.append(
            json.dumps(child_full.outputs or {}, ensure_ascii=False, default=str)
        )
        if not reply_snippet:
            reply_snippet = _extract_reply_snippet(child_full.outputs)

    blob = "\n".join(blob_parts)
    hits = _keyword_hits(blob, keywords)
    if keywords and not hits:
        return None

    start_time = getattr(full, "start_time", None)
    if start_time is None:
        return None
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    score = _score_match(
        keyword_hits=hits,
        runtime_channel=runtime_channel,
        require_telegram=require_telegram,
    )
    return TraceMatch(
        project_name=project_name,
        trace_id=trace_id,
        root_run_id=root_run_id,
        start_time_utc=start_time,
        agent_id=agent_id,
        user_id=user_id,
        runtime_channel=runtime_channel or "?",
        keyword_hits=hits,
        user_snippet=user_snippet,
        reply_snippet=reply_snippet,
        score=score,
    )


def _format_local_time(when_utc: datetime, tz_name: str) -> str:
    tz = ZoneInfo(tz_name)
    return when_utc.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S %Z")


def _print_matches(
    matches: list[TraceMatch],
    *,
    tz_name: str,
    log_file: str,
) -> None:
    if not matches:
        print("no matches")
        return
    for index, match in enumerate(matches, start=1):
        print(f"--- match #{index} score={match.score} ---")
        print(f"project={match.project_name}")
        print(f"trace_id={match.trace_id}")
        print(f"root_run_id={match.root_run_id}")
        print(f"utc={match.start_time_utc.isoformat()}")
        print(f"local={_format_local_time(match.start_time_utc, tz_name)}")
        print(f"user_id={match.user_id}")
        print(f"agent_id={match.agent_id}")
        print(f"runtime_channel={match.runtime_channel}")
        print(f"keyword_hits={','.join(match.keyword_hits) or '-'}")
        print(f"user_snippet={match.user_snippet}")
        print(f"reply_snippet={match.reply_snippet}")
        print(f"langsmith_url={_LANGSMITH_PUBLIC_TRACE_URL.format(trace_id=match.trace_id)}")
        print("log_grep:")
        print(f"  rg -n '{match.trace_id}|{match.agent_id}|run_turn|telegram-demo' {log_file}")
        print(
            "  download trace: "
            f"python .cursor/skills/scripts/download_run.py "
            f"--trace-id {match.trace_id} --project-name {match.project_name}"
        )


app = cyclopts.App(
    help=(
        "Match Telegram screenshot hints to LangSmith companion user_turn traces.\n\n"
        "Run from repo root. Requires agent.langchain_api_key in --config."
    ),
)


@app.default
def main(
    screenshot_clock: Annotated[
        str,
        cyclopts.Parameter(
            help=(
                "Clock time visible on screenshot: HH:MM[:SS] or full ISO local datetime. "
                "Required."
            ),
        ),
    ],
    *,
    calendar_date: Annotated[
        str,
        cyclopts.Parameter(
            "--date",
            help="Calendar date for HH:MM clock (YYYY-MM-DD). Default: today in --timezone.",
        ),
    ] = "",
    timezone_name: Annotated[
        str,
        cyclopts.Parameter(
            "--timezone",
            help="IANA timezone for screenshot clock (default Asia/Shanghai).",
        ),
    ] = "Asia/Shanghai",
    padding_minutes: Annotated[
        int,
        cyclopts.Parameter(
            "--padding-minutes",
            help="Minutes before/after screenshot clock for LangSmith search window.",
        ),
    ] = 15,
    keyword: Annotated[
        list[str],
        cyclopts.Parameter(
            "--keyword",
            help=(
                "Distinctive snippet from screenshot (user or bot line). Repeatable. "
                "Omit to list all user_turn roots in the window."
            ),
        ),
    ] = (),
    environment_hint: Annotated[
        str,
        cyclopts.Parameter(
            "--environment-hint",
            help="Narrow LangSmith projects: dev | local | prod | any.",
        ),
    ] = "dev",
    project_name: Annotated[
        list[str],
        cyclopts.Parameter(
            "--project-name",
            help="Explicit LangSmith project(s). Repeatable; overrides --environment-hint.",
        ),
    ] = (),
    config: Annotated[
        Path,
        cyclopts.Parameter(
            "--config",
            help="Inty YAML with agent.langchain_api_key.",
        ),
    ] = Path("devops/config.yaml.local"),
    require_telegram: Annotated[
        bool,
        cyclopts.Parameter(
            "--require-telegram",
            help="Drop matches whose inty_runtime_channel is not telegram.",
        ),
    ] = True,
    max_roots: Annotated[
        int,
        cyclopts.Parameter(
            "--max-roots",
            help="Max root runs fetched per project (LangSmith API cap 100).",
        ),
    ] = 100,
    max_matches: Annotated[
        int,
        cyclopts.Parameter(
            "--max-matches",
            help="Stop after this many ranked matches.",
        ),
    ] = 10,
    read_delay_seconds: Annotated[
        float,
        cyclopts.Parameter(
            "--read-delay-seconds",
            help="Sleep between read_run calls to reduce LangSmith 429 rate limits.",
        ),
    ] = 0.35,
    log_file: Annotated[
        str,
        cyclopts.Parameter(
            "--log-file",
            help="Ops log path for printed rg hints (local default .inty/inty.log).",
        ),
    ] = ".inty/inty.log",
    json_output: Annotated[
        bool,
        cyclopts.Parameter(
            "--json",
            help="Emit machine-readable JSON instead of human text.",
        ),
    ] = False,
) -> int:
    assert screenshot_clock.strip() != ""
    yaml_data = _load_yaml_config(config)
    api_key = _langchain_api_key(yaml_data)
    if not api_key:
        print(
            f"error: missing langchain_api_key in {config} and env",
            file=sys.stderr,
        )
        return 1
    os.environ["LANGCHAIN_API_KEY"] = api_key

    tz = ZoneInfo(timezone_name)
    day = (
        date.fromisoformat(calendar_date)
        if calendar_date.strip()
        else datetime.now(tz).date()
    )
    window = _build_search_window(
        screenshot_clock=screenshot_clock,
        calendar_date=day,
        tz_name=timezone_name,
        padding_minutes=padding_minutes,
    )
    keywords = tuple(keyword)
    explicit_projects = tuple(project_name)

    client = Client()
    projects = _candidate_projects(
        client,
        environment_hint=environment_hint.strip().lower(),
        explicit_projects=explicit_projects,
    )
    if not projects:
        print("error: no LangSmith projects to search", file=sys.stderr)
        return 1

    matches: list[TraceMatch] = []
    for project in projects:
        roots = _list_user_turn_roots(
            client,
            project_name=project,
            window=window,
            max_roots=max_roots,
        )
        for root in roots:
            match = _inspect_root_run(
                client,
                project_name=project,
                root_run=root,
                keywords=keywords,
                require_telegram=require_telegram,
                read_delay_seconds=read_delay_seconds,
            )
            if match is None:
                continue
            matches.append(match)
            if len(matches) >= max_matches:
                break
        if len(matches) >= max_matches:
            break

    matches.sort(key=lambda item: (-item.score, item.start_time_utc))

    if json_output:
        payload = {
            "window_start_utc": window.start_utc.isoformat(),
            "window_end_utc": window.end_utc.isoformat(),
            "projects_searched": projects,
            "match_count": len(matches),
            "matches": [
                {
                    "project_name": item.project_name,
                    "trace_id": item.trace_id,
                    "root_run_id": item.root_run_id,
                    "start_time_utc": item.start_time_utc.isoformat(),
                    "start_time_local": _format_local_time(
                        item.start_time_utc, timezone_name
                    ),
                    "user_id": item.user_id,
                    "agent_id": item.agent_id,
                    "runtime_channel": item.runtime_channel,
                    "keyword_hits": list(item.keyword_hits),
                    "user_snippet": item.user_snippet,
                    "reply_snippet": item.reply_snippet,
                    "score": item.score,
                    "langsmith_url": _LANGSMITH_PUBLIC_TRACE_URL.format(
                        trace_id=item.trace_id
                    ),
                }
                for item in matches
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(
        f"window_utc=[{window.start_utc.isoformat()}, {window.end_utc.isoformat()}) "
        f"projects={projects} keywords={list(keywords) or '(none)'}"
    )
    _print_matches(matches, tz_name=timezone_name, log_file=log_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(app())
