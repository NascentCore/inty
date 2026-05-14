#!/usr/bin/env python3
"""
Experiment: under OpenRouter chat.completions with tool_choice=\"required\",
measure how often a no-op tool is chosen vs specialized tools when user
messages are aligned vs unrelated to those tools.

Reads API key from devops/config.yaml.local -> agent.api_key (unless OPENROUTER_API_KEY set).

Usage (from repo root):
  uv pip install -r experimental/tool_choice_required_do_nothing/requirements.txt
  python experimental/tool_choice_required_do_nothing/run_experiment.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _REPO_ROOT / "devops" / "config.yaml.local"

# Must match tool.function.name values below
NOOP_TOOL_NAME = "noop_acknowledge"


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": NOOP_TOOL_NAME,
            "description": (
                "Acknowledge the turn without performing any external action. "
                "Use when the user's message is general chat, gratitude, small talk, "
                "or does not clearly require weather, scheduling, translation, or math tools."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Brief internal note why no other tool applies.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_forecast",
            "description": "Get weather forecast for a city on a specific date or day.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "when": {
                        "type": "string",
                        "description": "e.g. tomorrow, 2026-02-20",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_reminder",
            "description": "Create a calendar reminder or alarm for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "datetime_iso": {"type": "string"},
                },
                "required": ["title", "datetime_iso"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "translate_phrase",
            "description": "Translate a phrase between natural languages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "source_language": {"type": "string"},
                    "target_language": {"type": "string"},
                },
                "required": ["text", "target_language"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_math_expression",
            "description": "Evaluate a mathematical expression or computation.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
]


@dataclass(frozen=True)
class PromptCase:
    case_id: str
    category: str  # "aligned" | "neutral"
    user_message: str
    """If category aligned: which specialized tool we intend to trigger."""
    expected_specialized_tool: str | None


# --- User messages aligned with specific (non-noop) tools ---
ALIGNED_CASES: list[PromptCase] = [
    PromptCase(
        case_id="a_weather",
        category="aligned",
        user_message="What's the weather going to be like in Seattle this Saturday?",
        expected_specialized_tool="get_weather_forecast",
    ),
    PromptCase(
        case_id="a_calendar",
        category="aligned",
        user_message="Please add a calendar reminder: team standup next Monday at 10:00 local time.",
        expected_specialized_tool="create_calendar_reminder",
    ),
    PromptCase(
        case_id="a_translate",
        category="aligned",
        user_message='Translate the phrase "Where is the nearest train station?" from English to Korean.',
        expected_specialized_tool="translate_phrase",
    ),
    PromptCase(
        case_id="a_math",
        category="aligned",
        user_message="Compute (19**2 - 47) / 4 and give the numeric result.",
        expected_specialized_tool="evaluate_math_expression",
    ),
]

# --- Messages NOT tied to the specialized tools (goal: often pick noop under required tools) ---
NEUTRAL_CASES: list[PromptCase] = [
    PromptCase(
        case_id="n_thanks",
        category="neutral",
        user_message="Thanks, that really helped. Have a nice day!",
        expected_specialized_tool=None,
    ),
    PromptCase(
        case_id="n_smalltalk",
        category="neutral",
        user_message="How's your day going? I'm just saying hi.",
        expected_specialized_tool=None,
    ),
    PromptCase(
        case_id="n_general_knowledge",
        category="neutral",
        user_message="Explain in two sentences why vaccines train the immune system.",
        expected_specialized_tool=None,
    ),
    PromptCase(
        case_id="n_creative",
        category="neutral",
        user_message="Write a four-line poem about moonlight on a lake. No tools needed—just text.",
        expected_specialized_tool=None,
    ),
]


SYSTEM_PROMPT = """You are a concise assistant. Tools are available.
When you must call a tool, pick exactly one that best matches the user's intent.
For general conversation, gratitude, chitchat, or pure explanation/creative text that does not need weather, scheduling, translation, or explicit calculation, prefer noop_acknowledge."""


def load_openrouter_from_config(config_path: Path) -> tuple[str, str]:
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError("config yaml must be a mapping")
    load_dotenv()
    env_key = (
        os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    ).strip()
    agent_cfg = raw.get("agent", {})
    if not isinstance(agent_cfg, dict):
        raise ValueError("config missing 'agent' mapping")
    key_from_file = str(agent_cfg.get("api_key", "")).strip()
    base_url = str(agent_cfg.get("base_url", "https://openrouter.ai/api/v1")).strip()
    api_key = env_key or key_from_file
    if not api_key:
        raise ValueError("No API key in env or config agent.api_key")
    return api_key, base_url


def extract_tool_names(response: Any) -> tuple[list[str], str | None]:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return [], None
    c0 = choices[0]
    msg = getattr(c0, "message", None)
    if msg is None:
        return [], getattr(c0, "finish_reason", None)
    raw_calls = getattr(msg, "tool_calls", None) or []
    names: list[str] = []
    for tc in raw_calls:
        fn = getattr(tc, "function", None)
        name = getattr(fn, "name", None)
        if isinstance(name, str) and name:
            names.append(name)
    return names, getattr(c0, "finish_reason", None)


def call_once(
    client: OpenAI,
    *,
    model: str,
    user_message: str,
    temperature: float,
    timeout_seconds: float,
) -> tuple[list[str], str | None, str | None]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="required",
            parallel_tool_calls=False,
            temperature=temperature,
            max_completion_tokens=1024,
            timeout=timeout_seconds,
        )
        names, fr = extract_tool_names(resp)
        return names, fr, None
    except (
        BadRequestError,
        AuthenticationError,
        PermissionDeniedError,
        RateLimitError,
        APIConnectionError,
        APITimeoutError,
        APIError,
    ) as e:
        return [], None, f"{type(e).__name__}: {e}"


def run_model(
    client: OpenAI,
    *,
    model: str,
    cases: list[PromptCase],
    samples_per_case: int,
    temperature: float,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        for rep in range(samples_per_case):
            t0 = time.perf_counter()
            names, finish_reason, err = call_once(
                client,
                model=model,
                user_message=case.user_message,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
            )
            latency_ms = (time.perf_counter() - t0) * 1000.0
            primary = names[0] if names else None
            rows.append(
                {
                    "model": model,
                    "case_id": case.case_id,
                    "category": case.category,
                    "expected_specialized_tool": case.expected_specialized_tool,
                    "user_message": case.user_message,
                    "repetition": rep + 1,
                    "called_tools": names,
                    "primary_tool": primary,
                    "is_noop": primary == NOOP_TOOL_NAME,
                    "finish_reason": finish_reason,
                    "latency_ms": round(latency_ms, 2),
                    "error": err,
                }
            )
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_model_cat: dict[str, dict[str, dict[str, float | int]]] = {}
    for r in rows:
        if r.get("error"):
            continue
        m = str(r["model"])
        cat = str(r["category"])
        by_model_cat.setdefault(m, {}).setdefault(cat, {"n": 0, "noop": 0})
        bucket = by_model_cat[m][cat]
        bucket["n"] = int(bucket["n"]) + 1  # type: ignore[assignment]
        if r.get("is_noop"):
            bucket["noop"] = int(bucket["noop"]) + 1  # type: ignore[assignment]

    rates: dict[str, Any] = {}
    for m, cats in by_model_cat.items():
        rates[m] = {}
        for cat, b in cats.items():
            n, noop = int(b["n"]), int(b["noop"])
            rates[m][cat] = {
                "samples": n,
                "noop_count": noop,
                "noop_rate": round(noop / n, 4) if n else 0.0,
            }

    # aligned: rate of matching expected specialized tool (when provided)
    match_stats: dict[str, dict[str, float]] = {}
    for r in rows:
        if r.get("error"):
            continue
        if r.get("category") != "aligned":
            continue
        exp = r.get("expected_specialized_tool")
        if not exp:
            continue
        m = str(r["model"])
        match_stats.setdefault(m, {"hit": 0, "total": 0})
        match_stats[m]["total"] += 1
        if exp in (r.get("called_tools") or []):
            match_stats[m]["hit"] += 1
    for m in match_stats:
        t = match_stats[m]["total"]
        match_stats[m]["expected_tool_match_rate"] = (
            round(match_stats[m]["hit"] / t, 4) if t else 0.0
        )

    return {"noop_by_model_category": rates, "aligned_expected_tool_match": match_stats}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=_DEFAULT_CONFIG,
        help="YAML with agent.api_key (default: devops/config.yaml.local)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=[
            # OpenRouter: `google/gemini-3.1-preview` is not valid; use Pro Preview slug.
            "google/gemini-3.1-pro-preview",
            "deepseek/deepseek-v4-flash",
        ],
    )
    parser.add_argument("--samples-per-case", type=int, default=8)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    api_key, base_url = load_openrouter_from_config(args.config)
    client = OpenAI(api_key=api_key, base_url=base_url)

    all_cases = ALIGNED_CASES + NEUTRAL_CASES
    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_path = out_dir / f"run_{stamp}.json"

    all_rows: list[dict[str, Any]] = []
    for model in args.models:
        rows = run_model(
            client,
            model=model,
            cases=all_cases,
            samples_per_case=args.samples_per_case,
            temperature=args.temperature,
            timeout_seconds=args.timeout,
        )
        all_rows.extend(rows)

    summary = summarize(all_rows)
    payload = {
        "meta": {
            "created_at_utc": stamp,
            "config_path": str(args.config),
            "models": list(args.models),
            "samples_per_case": args.samples_per_case,
            "temperature": args.temperature,
            "tool_choice": "required",
            "noop_tool": NOOP_TOOL_NAME,
        },
        "summary": summary,
        "rows": all_rows,
    }
    results_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nWrote {results_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
