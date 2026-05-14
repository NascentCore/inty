"""Tool trigger benchmark for memory prompt structures.

Compares tool-calling trigger rate under:
1) Flat memory injection
2) Layered memory injection

The benchmark uses OpenRouter with model `google/gemini-2.5-flash` by default,
and reads API key from `devops/config.yaml.dev` (agent.api_key) unless
`OPENROUTER_API_KEY` / `OPENAI_API_KEY` is already provided.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml
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
from dotenv import load_dotenv

MemoryVariant = Literal["flat", "layered"]


@dataclass(frozen=True)
class ToolTriggerCase:
    case_id: str
    query: str
    should_trigger_tool: bool
    expected_tool: str | None


@dataclass(frozen=True)
class BenchmarkObservation:
    variant: MemoryVariant
    case_id: str
    query: str
    iteration: int
    should_trigger_tool: bool
    expected_tool: str | None
    triggered_tool: bool
    called_tools: list[str]
    matched_expected_tool: bool
    finish_reason: str | None
    latency_ms: float
    status: str
    error: str | None


@dataclass(frozen=True)
class VariantSummary:
    variant: MemoryVariant
    total_samples: int
    trigger_rate_overall: float
    trigger_rate_when_needed: float
    trigger_rate_when_not_needed: float
    expected_tool_match_rate_when_needed: float


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather forecast for a city/date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Create a calendar event/reminder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                },
                "required": ["title", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search current or external factual information.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "Create support ticket for account/app problems.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "details": {"type": "string"},
                },
                "required": ["topic", "details"],
            },
        },
    },
]


CASES: list[ToolTriggerCase] = [
    ToolTriggerCase(
        case_id="c01_weather",
        query="Can you check tomorrow morning weather in New York?",
        should_trigger_tool=True,
        expected_tool="get_weather",
    ),
    ToolTriggerCase(
        case_id="c02_calendar",
        query="Schedule a reminder for dentist on Friday at 3pm.",
        should_trigger_tool=True,
        expected_tool="create_calendar_event",
    ),
    ToolTriggerCase(
        case_id="c03_search",
        query="Search latest OpenAI and Google Gemini model updates this week.",
        should_trigger_tool=True,
        expected_tool="web_search",
    ),
    ToolTriggerCase(
        case_id="c04_support",
        query="I cannot login to my account, please file a support ticket for me.",
        should_trigger_tool=True,
        expected_tool="create_support_ticket",
    ),
    ToolTriggerCase(
        case_id="c05_chitchat",
        query="Tell me a short warm goodnight message.",
        should_trigger_tool=False,
        expected_tool=None,
    ),
    ToolTriggerCase(
        case_id="c06_general_knowledge",
        query="Why does deep sleep matter for memory consolidation?",
        should_trigger_tool=False,
        expected_tool=None,
    ),
    ToolTriggerCase(
        case_id="c07_creative",
        query="Write a two-line poem about spring rain.",
        should_trigger_tool=False,
        expected_tool=None,
    ),
    ToolTriggerCase(
        case_id="c08_joke",
        query="Tell me a light joke about penguins.",
        should_trigger_tool=False,
        expected_tool=None,
    ),
]


FLAT_MEMORY = """User memory blob (flat, unstructured):
- Alex, product manager, prefers concise and practical responses.
- Last month Alex had login trouble and asked support questions.
- Alex often plans schedules and checks weather before commuting.
- Alex likes occasional creative chat, poems, jokes, and emotional support.
- Alex asks for updates on AI models and market news.
- Sometimes assistant should proactively verify facts with tools.
- If unsure, searching first can reduce risk.
- Tool notes mixed with profile: weather/get_weather, schedule/create_calendar_event,
  latest info/web_search, account problem/create_support_ticket.
- Keep conversation smooth and do not ask many follow-up questions.
"""


LAYERED_MEMORY = """<memory_blocks>
<core_memory>
- User name: Alex
- Tone preference: concise, direct, practical
</core_memory>

<profile_memory>
- Works as product manager
- Commutes often and plans with calendar reminders
</profile_memory>

<episodic_memory>
- Had account login issues recently
- Frequently asks for current updates before decisions
</episodic_memory>

<tool_affinity_memory>
- Tool call gate (strict):
  1) Call a tool only when user explicitly asks an external action or real-time lookup.
  2) Do not call tools for pure chat, poetry, jokes, emotional support, or general explanation.
  3) If no external action is requested, answer directly without tools.
- Mapping:
  - forecast place/date => get_weather
  - schedule/reminder/create calendar item => create_calendar_event
  - latest/current external facts => web_search
  - file account/app issue => create_support_ticket
</tool_affinity_memory>
</memory_blocks>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tool trigger rate benchmark")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[2] / "devops" / "config.yaml.dev"),
        help="Path to config.yaml.dev",
    )
    parser.add_argument(
        "--model",
        default="google/gemini-2.5-flash",
        help="Model name on OpenRouter",
    )
    parser.add_argument(
        "--samples-per-case",
        type=int,
        default=5,
        help="Number of repeated runs per query for each memory variant",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature for probabilistic trigger estimation",
    )
    parser.add_argument(
        "--max-completion-tokens",
        type=int,
        default=200,
        help="max_completion_tokens for model output",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=60.0,
        help="Timeout per API call",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Defaults to results/tool_trigger_<timestamp>",
    )
    return parser.parse_args()


def load_openrouter_config(config_path: Path) -> tuple[str, str]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError("config yaml must be a mapping")

    env_key = ""
    load_dotenv()
    openrouter_from_env = (
        os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    )
    if isinstance(openrouter_from_env, str):
        env_key = openrouter_from_env.strip()

    agent_cfg = raw.get("agent", {})
    if not isinstance(agent_cfg, dict):
        raise ValueError("config.yaml.dev missing 'agent' mapping")
    key_from_file = str(agent_cfg.get("api_key", "")).strip()
    base_url = str(agent_cfg.get("base_url", "https://openrouter.ai/api/v1")).strip()
    api_key = env_key or key_from_file
    if not api_key:
        raise ValueError("No API key found in env or config.yaml.dev agent.api_key")
    if not base_url:
        raise ValueError("base_url is empty")
    return api_key, base_url


def build_messages(variant: MemoryVariant, query: str) -> list[dict[str, str]]:
    memory = FLAT_MEMORY if variant == "flat" else LAYERED_MEMORY
    system_prompt = (
        "You are an assistant with access to tools.\n"
        "Decision rule:\n"
        "- Call exactly one tool when user asks for external real-time info or explicit action.\n"
        "- Do NOT call tools for pure chitchat, creative writing, or general knowledge explainers.\n"
        "- If calling tool, prefer the most specific tool and return tool call directly.\n"
        "- If no tool needed, answer directly.\n\n"
        "Memory context:\n"
        f"{memory}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]


def call_with_retries(
    *,
    client: OpenAI,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_completion_tokens: int,
    timeout_seconds: float,
    max_retries: int = 3,
) -> Any:
    wait_seconds = 1.0
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                parallel_tool_calls=False,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                timeout=timeout_seconds,
            )
        except (RateLimitError, APIConnectionError, APITimeoutError, APIError):
            if attempt == max_retries - 1:
                raise
            time.sleep(wait_seconds)
            wait_seconds *= 2


def extract_tool_call_info(response: Any) -> tuple[list[str], str | None]:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return [], None
    choice0 = choices[0]
    message = getattr(choice0, "message", None)
    if message is None:
        return [], getattr(choice0, "finish_reason", None)
    raw_calls = getattr(message, "tool_calls", None) or []
    names: list[str] = []
    for tc in raw_calls:
        fn = getattr(tc, "function", None)
        name = getattr(fn, "name", None)
        if isinstance(name, str) and name:
            names.append(name)
    return names, getattr(choice0, "finish_reason", None)


def run_benchmark(
    *,
    client: OpenAI,
    model: str,
    samples_per_case: int,
    temperature: float,
    max_completion_tokens: int,
    timeout_seconds: float,
) -> list[BenchmarkObservation]:
    variants: list[MemoryVariant] = ["flat", "layered"]
    observations: list[BenchmarkObservation] = []

    for variant in variants:
        for case in CASES:
            for iteration in range(1, samples_per_case + 1):
                t0 = time.perf_counter()
                try:
                    response = call_with_retries(
                        client=client,
                        model=model,
                        messages=build_messages(variant, case.query),
                        temperature=temperature,
                        max_completion_tokens=max_completion_tokens,
                        timeout_seconds=timeout_seconds,
                    )
                    called_tools, finish_reason = extract_tool_call_info(response)
                    triggered = len(called_tools) > 0
                    matched_expected = (
                        case.expected_tool in called_tools
                        if case.expected_tool is not None
                        else not triggered
                    )
                    observations.append(
                        BenchmarkObservation(
                            variant=variant,
                            case_id=case.case_id,
                            query=case.query,
                            iteration=iteration,
                            should_trigger_tool=case.should_trigger_tool,
                            expected_tool=case.expected_tool,
                            triggered_tool=triggered,
                            called_tools=called_tools,
                            matched_expected_tool=matched_expected,
                            finish_reason=finish_reason,
                            latency_ms=(time.perf_counter() - t0) * 1000.0,
                            status="ok",
                            error=None,
                        )
                    )
                except (
                    BadRequestError,
                    AuthenticationError,
                    PermissionDeniedError,
                    RateLimitError,
                    APIConnectionError,
                    APITimeoutError,
                    APIError,
                ) as e:
                    observations.append(
                        BenchmarkObservation(
                            variant=variant,
                            case_id=case.case_id,
                            query=case.query,
                            iteration=iteration,
                            should_trigger_tool=case.should_trigger_tool,
                            expected_tool=case.expected_tool,
                            triggered_tool=False,
                            called_tools=[],
                            matched_expected_tool=False,
                            finish_reason=None,
                            latency_ms=(time.perf_counter() - t0) * 1000.0,
                            status="error",
                            error=f"{type(e).__name__}: {e}",
                        )
                    )
    return observations


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def summarize_variant(
    observations: list[BenchmarkObservation],
    variant: MemoryVariant,
) -> VariantSummary:
    rows = [r for r in observations if r.variant == variant and r.status == "ok"]
    need_rows = [r for r in rows if r.should_trigger_tool]
    no_need_rows = [r for r in rows if not r.should_trigger_tool]

    return VariantSummary(
        variant=variant,
        total_samples=len(rows),
        trigger_rate_overall=_safe_rate(
            sum(1 for r in rows if r.triggered_tool),
            len(rows),
        ),
        trigger_rate_when_needed=_safe_rate(
            sum(1 for r in need_rows if r.triggered_tool),
            len(need_rows),
        ),
        trigger_rate_when_not_needed=_safe_rate(
            sum(1 for r in no_need_rows if r.triggered_tool),
            len(no_need_rows),
        ),
        expected_tool_match_rate_when_needed=_safe_rate(
            sum(1 for r in need_rows if r.matched_expected_tool),
            len(need_rows),
        ),
    )


def generate_markdown_report(
    *,
    model: str,
    samples_per_case: int,
    summaries: list[VariantSummary],
    observations: list[BenchmarkObservation],
) -> str:
    summary_map = {s.variant: s for s in summaries}
    flat = summary_map["flat"]
    layered = summary_map["layered"]

    lines: list[str] = []
    lines.append("# Tool Trigger Benchmark: Flat vs Layered Memory")
    lines.append("")
    lines.append(f"- Model: `{model}`")
    lines.append(f"- Samples per case: `{samples_per_case}`")
    lines.append(f"- Total cases: `{len(CASES)}`")
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(
        f"- Trigger rate (when tool needed): flat `{flat.trigger_rate_when_needed:.2%}` "
        f"-> layered `{layered.trigger_rate_when_needed:.2%}`"
    )
    lines.append(
        f"- False trigger rate (when tool not needed): flat `{flat.trigger_rate_when_not_needed:.2%}` "
        f"-> layered `{layered.trigger_rate_when_not_needed:.2%}`"
    )
    lines.append(
        f"- Expected tool match (needed cases): flat `{flat.expected_tool_match_rate_when_needed:.2%}` "
        f"-> layered `{layered.expected_tool_match_rate_when_needed:.2%}`"
    )
    lines.append("")
    lines.append("## Variant Summary")
    lines.append("")
    lines.append(
        "| Variant | Samples | Overall Trigger | Trigger When Needed | Trigger When Not Needed | Expected Tool Match (Needed) |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|")
    for s in summaries:
        lines.append(
            f"| {s.variant} | {s.total_samples} | {s.trigger_rate_overall:.2%} | "
            f"{s.trigger_rate_when_needed:.2%} | {s.trigger_rate_when_not_needed:.2%} | "
            f"{s.expected_tool_match_rate_when_needed:.2%} |"
        )
    lines.append("")
    lines.append("## Per-case Trigger Rate")
    lines.append("")
    lines.append("| Case | Should Trigger | Flat | Layered |")
    lines.append("|---|---|---:|---:|")
    for case in CASES:
        flat_rows = [
            r
            for r in observations
            if r.status == "ok" and r.variant == "flat" and r.case_id == case.case_id
        ]
        layered_rows = [
            r
            for r in observations
            if r.status == "ok" and r.variant == "layered" and r.case_id == case.case_id
        ]
        flat_rate = _safe_rate(
            sum(1 for r in flat_rows if r.triggered_tool), len(flat_rows)
        )
        layered_rate = _safe_rate(
            sum(1 for r in layered_rows if r.triggered_tool), len(layered_rows)
        )
        lines.append(
            f"| {case.case_id} | {case.should_trigger_tool} | {flat_rate:.2%} | {layered_rate:.2%} |"
        )

    error_count = sum(1 for r in observations if r.status != "ok")
    lines.append("")
    lines.append(f"- API errors: `{error_count}`")
    return "\n".join(lines)


def resolve_output_dir(output_dir_arg: str | None) -> Path:
    base = Path(__file__).resolve().parent / "results"
    if output_dir_arg:
        out = Path(output_dir_arg)
        if not out.is_absolute():
            out = Path.cwd() / out
        return out
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return base / f"tool_trigger_{stamp}"


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    output_dir = resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    api_key, base_url = load_openrouter_config(config_path)
    client = OpenAI(api_key=api_key, base_url=base_url)

    observations = run_benchmark(
        client=client,
        model=args.model,
        samples_per_case=args.samples_per_case,
        temperature=args.temperature,
        max_completion_tokens=args.max_completion_tokens,
        timeout_seconds=args.timeout_seconds,
    )
    summaries = [
        summarize_variant(observations, "flat"),
        summarize_variant(observations, "layered"),
    ]

    raw_data = {
        "config": {
            "model": args.model,
            "samples_per_case": args.samples_per_case,
            "temperature": args.temperature,
            "max_completion_tokens": args.max_completion_tokens,
            "timeout_seconds": args.timeout_seconds,
            "config_path": str(config_path),
        },
        "summaries": [asdict(s) for s in summaries],
        "observations": [asdict(o) for o in observations],
    }
    raw_json_path = output_dir / "raw_data.json"
    raw_json_path.write_text(
        json.dumps(raw_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report_path = output_dir / "report.md"
    report_path.write_text(
        generate_markdown_report(
            model=args.model,
            samples_per_case=args.samples_per_case,
            summaries=summaries,
            observations=observations,
        ),
        encoding="utf-8",
    )

    print(f"Benchmark completed: {output_dir}")
    print(f"- Report: {report_path}")
    print(f"- Raw data: {raw_json_path}")
    for s in summaries:
        print(
            f"[{s.variant}] needed_trigger={s.trigger_rate_when_needed:.2%}, "
            f"not_needed_trigger={s.trigger_rate_when_not_needed:.2%}, "
            f"expected_tool_match={s.expected_tool_match_rate_when_needed:.2%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
