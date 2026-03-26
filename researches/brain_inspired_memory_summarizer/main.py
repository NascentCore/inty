from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_PREF_RE = re.compile(r"(?:我|以后我|请)(?:更)?喜欢(?:你)?叫我([A-Za-z\u4e00-\u9fff]{1,16})")
_CITY_RE = re.compile(r"我(?:现在)?住在([A-Za-z\u4e00-\u9fff]{1,24})")
_PET_RE = re.compile(r"我养了一只([A-Za-z\u4e00-\u9fff]{1,24})")
_DAY_RE = re.compile(r"我是周([一二三四五六日天])休息")
_COFFEE_RE = re.compile(r"(?:我|本人)?(不喝咖啡|喝咖啡)")
_BOUNDARY_RE = re.compile(r"(不要叫我宝贝|别叫我宝贝|请不要叫我宝贝)")


def _extract_memory_facts(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    pref = _PREF_RE.search(text)
    if pref:
        out["preferred_name"] = pref.group(1)
    city = _CITY_RE.search(text)
    if city:
        out["city"] = city.group(1)
    pet = _PET_RE.search(text)
    if pet:
        out["pet"] = pet.group(1)
    day = _DAY_RE.search(text)
    if day:
        out["rest_day"] = f"周{day.group(1)}"
    coffee = _COFFEE_RE.search(text)
    if coffee:
        out["coffee_preference"] = coffee.group(1)
    boundary = _BOUNDARY_RE.search(text)
    if boundary:
        out["boundary"] = "不要叫我宝贝"
    return out


def _count_chars(messages: list[dict[str, str]]) -> int:
    return sum(len(m["text"]) for m in messages)


@dataclass(frozen=True)
class QAItem:
    question: str
    key: str
    expected: str


@dataclass(frozen=True)
class ExperimentCase:
    case_id: str
    turns: list[dict[str, str]]
    qa: list[QAItem]


def _load_dataset(path: Path) -> list[ExperimentCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[ExperimentCase] = []
    for item in raw["cases"]:
        qa = [QAItem(**q) for q in item["qa"]]
        out.append(
            ExperimentCase(
                case_id=item["case_id"],
                turns=item["turns"],
                qa=qa,
            )
        )
    return out


class BaselineAgent:
    """
    Baseline: only keeps last N turns in context.
    If fact not present in context, returns unknown.
    """

    def __init__(self, window_turns: int = 6) -> None:
        self.window_turns = window_turns
        self.turns: list[dict[str, str]] = []

    def ingest_turn(self, user_text: str, assistant_text: str) -> None:
        self.turns.append({"role": "user", "text": user_text})
        self.turns.append({"role": "assistant", "text": assistant_text})

    def _context_messages(self) -> list[dict[str, str]]:
        k = self.window_turns * 2
        if len(self.turns) <= k:
            return self.turns
        return self.turns[-k:]

    def answer(self, key: str) -> tuple[str, int]:
        ctx = self._context_messages()
        merged = "\n".join(m["text"] for m in ctx if m["role"] == "user")
        facts = _extract_memory_facts(merged)
        answer = facts.get(key, "不知道")
        return answer, _count_chars(ctx)


class LayeredMemoryAgent:
    """
    Layered prototype:
    - L1 transcript window for recency
    - L4 semantic memory facts for durable retrieval
    """

    def __init__(self, window_turns: int = 2) -> None:
        self.window_turns = window_turns
        self.turns: list[dict[str, str]] = []
        self.semantic_memory: dict[str, str] = {}

    def ingest_turn(self, user_text: str, assistant_text: str) -> None:
        self.turns.append({"role": "user", "text": user_text})
        self.turns.append({"role": "assistant", "text": assistant_text})
        facts = _extract_memory_facts(user_text)
        # Latest stable statement wins in this minimal prototype.
        for k, v in facts.items():
            self.semantic_memory[k] = v

    def _context_messages(self) -> list[dict[str, str]]:
        k = self.window_turns * 2
        if len(self.turns) <= k:
            return self.turns
        return self.turns[-k:]

    def answer(self, key: str) -> tuple[str, int]:
        if key in self.semantic_memory:
            # Inject compact memory block + short recency window.
            ctx = self._context_messages()
            memory_block = f"{key}:{self.semantic_memory[key]}"
            chars = _count_chars(ctx) + len(memory_block)
            return self.semantic_memory[key], chars

        ctx = self._context_messages()
        merged = "\n".join(m["text"] for m in ctx if m["role"] == "user")
        facts = _extract_memory_facts(merged)
        return facts.get(key, "不知道"), _count_chars(ctx)


def _assistant_placeholder(_: str) -> str:
    return "收到，我记住了。"


def run_experiment(dataset_path: Path, baseline_window_turns: int = 6) -> dict[str, Any]:
    cases = _load_dataset(dataset_path)
    all_results: list[dict[str, Any]] = []

    baseline_hits = 0
    layered_hits = 0
    total_questions = 0
    baseline_chars = 0
    layered_chars = 0

    for case in cases:
        baseline = BaselineAgent(window_turns=baseline_window_turns)
        layered = LayeredMemoryAgent(window_turns=2)

        for turn in case.turns:
            user_text = turn["user"]
            assistant_text = _assistant_placeholder(user_text)
            baseline.ingest_turn(user_text=user_text, assistant_text=assistant_text)
            layered.ingest_turn(user_text=user_text, assistant_text=assistant_text)

        qa_rows: list[dict[str, Any]] = []
        for item in case.qa:
            b_ans, b_chars = baseline.answer(item.key)
            l_ans, l_chars = layered.answer(item.key)
            b_ok = b_ans == item.expected
            l_ok = l_ans == item.expected
            baseline_hits += int(b_ok)
            layered_hits += int(l_ok)
            baseline_chars += b_chars
            layered_chars += l_chars
            total_questions += 1
            qa_rows.append(
                {
                    "question": item.question,
                    "key": item.key,
                    "expected": item.expected,
                    "baseline_answer": b_ans,
                    "layered_answer": l_ans,
                    "baseline_correct": b_ok,
                    "layered_correct": l_ok,
                    "baseline_context_chars": b_chars,
                    "layered_context_chars": l_chars,
                }
            )

        all_results.append({"case_id": case.case_id, "qa": qa_rows})

    baseline_accuracy = baseline_hits / total_questions if total_questions else 0.0
    layered_accuracy = layered_hits / total_questions if total_questions else 0.0
    baseline_avg_chars = baseline_chars / total_questions if total_questions else 0.0
    layered_avg_chars = layered_chars / total_questions if total_questions else 0.0

    summary = {
        "questions": total_questions,
        "baseline_accuracy": baseline_accuracy,
        "layered_accuracy": layered_accuracy,
        "accuracy_delta": layered_accuracy - baseline_accuracy,
        "baseline_avg_context_chars": baseline_avg_chars,
        "layered_avg_context_chars": layered_avg_chars,
        "context_reduction_ratio": (
            (baseline_avg_chars - layered_avg_chars) / baseline_avg_chars
            if baseline_avg_chars > 0
            else 0.0
        ),
    }

    return {"summary": summary, "cases": all_results}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run minimal baseline vs layered memory experiment."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).resolve().parent / "dataset.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "results.json",
    )
    parser.add_argument("--baseline-window-turns", type=int, default=6)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run_experiment(
        dataset_path=args.dataset, baseline_window_turns=args.baseline_window_turns
    )
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
