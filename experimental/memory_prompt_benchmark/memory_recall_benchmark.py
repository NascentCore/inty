"""Memory recall benchmark for flat vs layered memory structures.

Compares recall accuracy under:
1) Flat memory injection (legacy-style blob)
2) Layered memory injection (core/profile/episodic/tool-affinity)

The benchmark uses OpenRouter with model `google/gemini-2.5-flash` by default,
and reads API key from `devops/config.yaml.dev` (agent.api_key) unless
`OPENROUTER_API_KEY` / `OPENAI_API_KEY` is already provided.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in some envs
    load_dotenv = None


MemoryVariant = Literal["flat", "layered"]


@dataclass(frozen=True)
class RecallCase:
    case_id: str
    question: str
    expected_code: str
    is_known_memory: bool


@dataclass(frozen=True)
class RecallObservation:
    variant: MemoryVariant
    case_id: str
    iteration: int
    expected_code: str
    predicted_code: str
    is_correct: bool
    is_known_memory: bool
    finish_reason: str | None
    latency_ms: float
    status: str
    error: str | None


@dataclass(frozen=True)
class RecallSummary:
    variant: MemoryVariant
    total_samples: int
    overall_accuracy: float
    known_case_accuracy: float
    unknown_case_accuracy: float
    unknown_hallucination_rate: float


CASES: list[RecallCase] = [
    RecallCase(
        case_id="r01_codename",
        question=(
            "What is the CURRENT preferred codename for the user?\n"
            "Options: A) Captain Alex  B) AlexBoss  C) Alex  Z) UNKNOWN"
        ),
        expected_code="A",
        is_known_memory=True,
    ),
    RecallCase(
        case_id="r02_wakeup_weekday",
        question=(
            "What is the CURRENT weekday wake-up time?\n"
            "Options: A) 07:00  B) 06:30  C) 05:45  Z) UNKNOWN"
        ),
        expected_code="B",
        is_known_memory=True,
    ),
    RecallCase(
        case_id="r03_drink",
        question=(
            "Which drink should be suggested first?\n"
            "Options: A) Americano  B) Oat milk latte  C) Green tea  Z) UNKNOWN"
        ),
        expected_code="B",
        is_known_memory=True,
    ),
    RecallCase(
        case_id="r04_avoid_topic",
        question=(
            "Which topic should be avoided because it increases anxiety?\n"
            "Options: A) Cryptocurrency day trading  B) Hiking trails  C) Sci-fi novels  Z) UNKNOWN"
        ),
        expected_code="A",
        is_known_memory=True,
    ),
    RecallCase(
        case_id="r05_city",
        question=(
            "What is the CURRENT city where user lives?\n"
            "Options: A) Seattle  B) Austin  C) Boston  Z) UNKNOWN"
        ),
        expected_code="A",
        is_known_memory=True,
    ),
    RecallCase(
        case_id="r06_dog_name",
        question=(
            "What is the user's dog name?\n"
            "Options: A) Coco  B) Mochi  C) Poppy  Z) UNKNOWN"
        ),
        expected_code="B",
        is_known_memory=True,
    ),
    RecallCase(
        case_id="r07_passport_missing",
        question=(
            "What is the user's passport number?\n"
            "Options: A) KX839122  B) MZ127761  C) PQ188273  Z) UNKNOWN"
        ),
        expected_code="Z",
        is_known_memory=False,
    ),
    RecallCase(
        case_id="r08_sister_name_missing",
        question=(
            "What is the user's sister name?\n"
            "Options: A) Lila  B) Emma  C) Zoe  Z) UNKNOWN"
        ),
        expected_code="Z",
        is_known_memory=False,
    ),
]


FLAT_MEMORY = """User memory notes (mixed, unstructured):
- User is Alex, product manager, likes concise and practical replies.
- Codename seen in notes: AlexBoss and Captain Alex.
- Weekday wake-up records seen: 07:00 and 06:30.
- Drinks mentioned: americano and oat milk latte.
- Anxiety trigger topics include cryptocurrency day trading and market panic threads.
- Location notes include Austin and Seattle.
- User's dog name: Mochi.
- Keep conversation warm and direct.
- Notes are from multiple periods; latest/canonical value is not explicitly marked.
"""


LAYERED_MEMORY = """<memory_blocks>
<core_memory>
- user_name: Alex
- preferred_codename: Captain Alex
- response_style: concise, practical
</core_memory>

<profile_memory>
- weekday_wakeup_time: 06:30
- preferred_drink: oat milk latte
- current_city: Seattle
- dog_name: Mochi
</profile_memory>

<episodic_memory>
- user moved from Austin to Seattle
- anxiety increased during cryptocurrency day-trading discussions
</episodic_memory>

<tool_affinity_memory>
- Use the latest/canonical value when old and new values conflict.
- If information is absent in memory, output UNKNOWN.
</tool_affinity_memory>
</memory_blocks>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Memory recall benchmark")
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
        default=4,
        help="Number of repeated runs per case and memory variant",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.4,
        help="Sampling temperature",
    )
    parser.add_argument(
        "--max-completion-tokens",
        type=int,
        default=120,
        help="Max completion tokens",
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
        help="Output directory; defaults to results/memory_recall_<timestamp>",
    )
    return parser.parse_args()


def load_openrouter_config(config_path: Path) -> tuple[str, str]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError("config yaml must be a mapping")

    if load_dotenv is not None:
        load_dotenv()
    env_key = (
        os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    ).strip()

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


def build_messages(variant: MemoryVariant, case: RecallCase) -> list[dict[str, str]]:
    memory = FLAT_MEMORY if variant == "flat" else LAYERED_MEMORY
    system = (
        "You are doing strict memory recall QA.\n"
        "Rules:\n"
        "1) Use ONLY the provided memory context.\n"
        "2) Choose exactly one option code from: A, B, C, Z.\n"
        "3) Output only one uppercase letter, nothing else.\n"
        "4) If information is absent, choose Z.\n\n"
        "Memory context:\n"
        f"{memory}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": case.question},
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
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                timeout=timeout_seconds,
            )
        except (RateLimitError, APIConnectionError, APITimeoutError, APIError):
            if attempt == max_retries - 1:
                raise
            time.sleep(wait_seconds)
            wait_seconds *= 2


def parse_option_code(content: str | None) -> str:
    if not content:
        return ""
    text = content.strip().upper()
    match = re.search(r"\b([ABCZ])\b", text)
    if match:
        return match.group(1)
    if text in {"A", "B", "C", "Z"}:
        return text
    return ""


def get_case_by_id(case_id: str) -> RecallCase:
    for case in CASES:
        if case.case_id == case_id:
            return case
    raise ValueError(f"Unknown case id: {case_id}")


def run_benchmark(
    *,
    client: OpenAI,
    model: str,
    samples_per_case: int,
    temperature: float,
    max_completion_tokens: int,
    timeout_seconds: float,
) -> list[RecallObservation]:
    variants: list[MemoryVariant] = ["flat", "layered"]
    observations: list[RecallObservation] = []

    for variant in variants:
        for case in CASES:
            for iteration in range(1, samples_per_case + 1):
                t0 = time.perf_counter()
                try:
                    response = call_with_retries(
                        client=client,
                        model=model,
                        messages=build_messages(variant, case),
                        temperature=temperature,
                        max_completion_tokens=max_completion_tokens,
                        timeout_seconds=timeout_seconds,
                    )
                    choice = response.choices[0]
                    message = choice.message
                    predicted_code = parse_option_code(getattr(message, "content", None))
                    observations.append(
                        RecallObservation(
                            variant=variant,
                            case_id=case.case_id,
                            iteration=iteration,
                            expected_code=case.expected_code,
                            predicted_code=predicted_code,
                            is_correct=predicted_code == case.expected_code,
                            is_known_memory=case.is_known_memory,
                            finish_reason=getattr(choice, "finish_reason", None),
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
                        RecallObservation(
                            variant=variant,
                            case_id=case.case_id,
                            iteration=iteration,
                            expected_code=case.expected_code,
                            predicted_code="",
                            is_correct=False,
                            is_known_memory=case.is_known_memory,
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
    observations: list[RecallObservation], variant: MemoryVariant
) -> RecallSummary:
    rows = [r for r in observations if r.variant == variant and r.status == "ok"]
    known_rows = [r for r in rows if r.is_known_memory]
    unknown_rows = [r for r in rows if not r.is_known_memory]
    unknown_hallucinations = sum(
        1 for r in unknown_rows if r.predicted_code and r.predicted_code != "Z"
    )
    return RecallSummary(
        variant=variant,
        total_samples=len(rows),
        overall_accuracy=_safe_rate(sum(1 for r in rows if r.is_correct), len(rows)),
        known_case_accuracy=_safe_rate(
            sum(1 for r in known_rows if r.is_correct), len(known_rows)
        ),
        unknown_case_accuracy=_safe_rate(
            sum(1 for r in unknown_rows if r.is_correct), len(unknown_rows)
        ),
        unknown_hallucination_rate=_safe_rate(
            unknown_hallucinations, len(unknown_rows)
        ),
    )


def generate_markdown_report(
    *,
    model: str,
    samples_per_case: int,
    summaries: list[RecallSummary],
    observations: list[RecallObservation],
) -> str:
    summary_map = {s.variant: s for s in summaries}
    flat = summary_map["flat"]
    layered = summary_map["layered"]
    lines: list[str] = []
    lines.append("# Memory Recall Benchmark: Flat vs Layered Memory")
    lines.append("")
    lines.append(f"- Model: `{model}`")
    lines.append(f"- Samples per case: `{samples_per_case}`")
    lines.append(f"- Total cases: `{len(CASES)}`")
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(
        f"- Overall accuracy: flat `{flat.overall_accuracy:.2%}` -> layered `{layered.overall_accuracy:.2%}`"
    )
    lines.append(
        f"- Known-memory accuracy: flat `{flat.known_case_accuracy:.2%}` -> layered `{layered.known_case_accuracy:.2%}`"
    )
    lines.append(
        f"- Unknown-case hallucination: flat `{flat.unknown_hallucination_rate:.2%}` -> layered `{layered.unknown_hallucination_rate:.2%}`"
    )
    lines.append("")
    lines.append("## Variant Summary")
    lines.append("")
    lines.append(
        "| Variant | Samples | Overall Acc | Known Acc | Unknown Acc | Unknown Hallucination |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|")
    for s in summaries:
        lines.append(
            f"| {s.variant} | {s.total_samples} | {s.overall_accuracy:.2%} | "
            f"{s.known_case_accuracy:.2%} | {s.unknown_case_accuracy:.2%} | "
            f"{s.unknown_hallucination_rate:.2%} |"
        )
    lines.append("")
    lines.append("## Per-case Accuracy")
    lines.append("")
    lines.append("## Error Profile")
    lines.append("")
    lines.append("| Variant | Case | Expected | Predicted | Count |")
    lines.append("|---|---|---|---|---:|")
    error_counts: dict[tuple[str, str, str, str], int] = {}
    for row in observations:
        if row.status != "ok":
            continue
        if row.is_correct:
            continue
        key = (
            row.variant,
            row.case_id,
            row.expected_code,
            row.predicted_code or "(empty)",
        )
        error_counts[key] = error_counts.get(key, 0) + 1
    if not error_counts:
        lines.append("| (none) | - | - | - | 0 |")
    else:
        for (variant, case_id, expected, predicted), count in sorted(
            error_counts.items()
        ):
            lines.append(
                f"| {variant} | {case_id} | {expected} | {predicted} | {count} |"
            )
    lines.append("")
    lines.append("| Case | Known Memory | Flat | Layered |")
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
            if r.status == "ok"
            and r.variant == "layered"
            and r.case_id == case.case_id
        ]
        flat_acc = _safe_rate(sum(1 for r in flat_rows if r.is_correct), len(flat_rows))
        layered_acc = _safe_rate(
            sum(1 for r in layered_rows if r.is_correct), len(layered_rows)
        )
        lines.append(
            f"| {case.case_id} | {case.is_known_memory} | {flat_acc:.2%} | {layered_acc:.2%} |"
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
    return base / f"memory_recall_{stamp}"


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

    per_case_accuracy: dict[str, dict[str, float]] = {}
    for case in CASES:
        per_case_accuracy[case.case_id] = {}
        for variant in ("flat", "layered"):
            rows = [
                r
                for r in observations
                if r.status == "ok" and r.variant == variant and r.case_id == case.case_id
            ]
            per_case_accuracy[case.case_id][variant] = _safe_rate(
                sum(1 for r in rows if r.is_correct), len(rows)
            )

    raw_data = {
        "config": {
            "model": args.model,
            "samples_per_case": args.samples_per_case,
            "temperature": args.temperature,
            "max_completion_tokens": args.max_completion_tokens,
            "timeout_seconds": args.timeout_seconds,
            "config_path": str(config_path),
        },
        "cases": [
            {
                "case_id": case.case_id,
                "question": case.question,
                "expected_code": case.expected_code,
                "is_known_memory": case.is_known_memory,
            }
            for case in CASES
        ],
        "summaries": [asdict(s) for s in summaries],
        "per_case_accuracy": per_case_accuracy,
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
            f"[{s.variant}] overall={s.overall_accuracy:.2%}, known={s.known_case_accuracy:.2%}, "
            f"unknown_hallucination={s.unknown_hallucination_rate:.2%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
