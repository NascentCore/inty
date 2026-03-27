from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

try:
    from .extractor import (
        SlotCandidate,
        extract_candidates,
        extract_memory_facts,
        is_invalid_preferred_name_against_boundary,
        is_more_reliable_name_candidate,
    )
except ImportError:  # script mode (python path/to/main.py)
    from extractor import (  # type: ignore
        SlotCandidate,
        extract_candidates,
        extract_memory_facts,
        is_invalid_preferred_name_against_boundary,
        is_more_reliable_name_candidate,
    )

_UNKNOWN = "不知道"


@dataclass(frozen=True)
class QAItem:
    question: str
    key: str
    expected: str


@dataclass(frozen=True)
class Episode:
    episode_id: str
    user_turns: list[str]
    qa: list[QAItem]


@dataclass(frozen=True)
class EvaluationMetrics:
    accuracy: float
    avg_context_chars: float
    avg_context_lines: float
    memory_item_count: int


def _extract_memory_facts(text: str) -> dict[str, str]:
    return extract_memory_facts(text)


def _context_chars(lines: list[str]) -> int:
    return sum(len(line) for line in lines)


def build_dataset() -> list[Episode]:
    """A deterministic benchmark where early facts are overwritten and later buried."""
    return [
        Episode(
            episode_id="ep-001",
            user_turns=[
                "以后请叫我阿辰。",
                "今天会议很多，先记个待办。",
                "我现在住在杭州。",
                "最近工作挺忙，回消息可能慢一点。",
                "我养了一只边牧。",
                "今天的午饭一般般。",
                "我是周三休息。",
                "晚上可能去散步。",
                "我不喝咖啡。",
                "请不要叫我宝贝。",
                "我搬家了，我现在住在上海。",
                "顺便说下，今天我只是想闲聊。",
                "刚刚在看电影，剧情还不错。",
                "这会儿有点困，准备休息了。",
            ],
            qa=[
                QAItem(question="你该怎么称呼我？", key="preferred_name", expected="阿辰"),
                QAItem(question="我现在住在哪？", key="city", expected="上海"),
                QAItem(question="我养了什么宠物？", key="pet", expected="边牧"),
                QAItem(question="我哪天休息？", key="rest_day", expected="周三"),
                QAItem(question="我喝不喝咖啡？", key="coffee_preference", expected="不喝咖啡"),
                QAItem(question="称呼边界是什么？", key="boundary", expected="不要叫我宝贝"),
            ],
        )
    ]


class NaiveWindowAgent:
    """
    Baseline agent: only sees a fixed number of recent user lines.
    """

    def __init__(self, window_size: int) -> None:
        self.window_size = window_size
        self.user_turns: list[str] = []

    def ingest_user_turn(self, text: str) -> None:
        self.user_turns.append(text)

    def _visible_context(self) -> list[str]:
        if len(self.user_turns) <= self.window_size:
            return self.user_turns
        return self.user_turns[-self.window_size :]

    def answer(self, key: str) -> tuple[str, int, int]:
        ctx = self._visible_context()
        extracted = _extract_memory_facts("\n".join(ctx))
        return extracted.get(key, _UNKNOWN), _context_chars(ctx), len(ctx)

    @property
    def memory_item_count(self) -> int:
        return 0


class LayeredMemoryAgent:
    """
    Minimal layered-memory agent:
    - L1: short recent window (same as baseline)
    - L4: salience-gated durable key-value memory
    """

    def __init__(
        self,
        window_size: int,
        candidate_extractor: Callable[[str, int], list[SlotCandidate]] = extract_candidates,
    ) -> None:
        self.window_size = window_size
        self.user_turns: list[str] = []
        self.semantic_memory: dict[str, str] = {}
        self._best_candidates: dict[str, SlotCandidate] = {}
        self._turn_counter = 0
        self._candidate_extractor = candidate_extractor

    def ingest_user_turn(self, text: str) -> None:
        self._turn_counter += 1
        self.user_turns.append(text)
        candidates = self._candidate_extractor(text, self._turn_counter)

        # Salience gate (still lightweight): apply confidence floor to avoid weak noise.
        for c in candidates:
            if c.confidence < 0.75:
                continue
            old = self._best_candidates.get(c.key)
            if old is None:
                self._best_candidates[c.key] = c
                self.semantic_memory[c.key] = c.value
                continue
            if c.key == "preferred_name":
                if is_more_reliable_name_candidate(c, old):
                    self._best_candidates[c.key] = c
                    self.semantic_memory[c.key] = c.value
            elif c.turn_idx >= old.turn_idx:
                self._best_candidates[c.key] = c
                self.semantic_memory[c.key] = c.value
        self._apply_cross_slot_conflict_resolution()

    def _apply_cross_slot_conflict_resolution(self) -> None:
        preferred_name = self.semantic_memory.get("preferred_name")
        boundary = self.semantic_memory.get("boundary")
        if preferred_name and is_invalid_preferred_name_against_boundary(
            preferred_name, boundary
        ):
            self.semantic_memory.pop("preferred_name", None)

    def _visible_context(self) -> list[str]:
        if len(self.user_turns) <= self.window_size:
            return self.user_turns
        return self.user_turns[-self.window_size :]

    def answer(self, key: str) -> tuple[str, int, int]:
        ctx = self._visible_context()
        if key in self.semantic_memory:
            memory_line = f"{key}:{self.semantic_memory[key]}"
            chars = _context_chars(ctx) + len(memory_line)
            lines = len(ctx) + 1
            return self.semantic_memory[key], chars, lines

        extracted = _extract_memory_facts("\n".join(ctx))
        return extracted.get(key, _UNKNOWN), _context_chars(ctx), len(ctx)

    @property
    def memory_item_count(self) -> int:
        return len(self.semantic_memory)


def evaluate_agent(agent: NaiveWindowAgent | LayeredMemoryAgent, episodes: list[Episode]) -> EvaluationMetrics:
    total_questions = 0
    correct = 0
    total_context_chars = 0
    total_context_lines = 0
    max_memory_items = 0

    for ep in episodes:
        for turn in ep.user_turns:
            agent.ingest_user_turn(turn)

        for qa in ep.qa:
            answer, chars, lines = agent.answer(qa.key)
            total_questions += 1
            total_context_chars += chars
            total_context_lines += lines
            if answer == qa.expected:
                correct += 1

        max_memory_items = max(max_memory_items, agent.memory_item_count)

    if total_questions == 0:
        return EvaluationMetrics(
            accuracy=0.0,
            avg_context_chars=0.0,
            avg_context_lines=0.0,
            memory_item_count=max_memory_items,
        )

    return EvaluationMetrics(
        accuracy=correct / total_questions,
        avg_context_chars=total_context_chars / total_questions,
        avg_context_lines=total_context_lines / total_questions,
        memory_item_count=max_memory_items,
    )


def run_experiment() -> dict[str, float]:
    episodes = build_dataset()
    baseline_small = evaluate_agent(NaiveWindowAgent(window_size=2), episodes)
    baseline_large = evaluate_agent(NaiveWindowAgent(window_size=99), episodes)
    layered = evaluate_agent(LayeredMemoryAgent(window_size=2), episodes)

    return {
        "baseline_small_accuracy": baseline_small.accuracy,
        "baseline_large_accuracy": baseline_large.accuracy,
        "layered_accuracy": layered.accuracy,
        "baseline_small_avg_context_chars": baseline_small.avg_context_chars,
        "baseline_large_avg_context_chars": baseline_large.avg_context_chars,
        "layered_avg_context_chars": layered.avg_context_chars,
        "accuracy_gain_vs_small": layered.accuracy - baseline_small.accuracy,
        "context_reduction_vs_large": (
            (baseline_large.avg_context_chars - layered.avg_context_chars)
            / baseline_large.avg_context_chars
            if baseline_large.avg_context_chars > 0
            else 0.0
        ),
        "layered_memory_item_count": float(layered.memory_item_count),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run brain-inspired memory summarizer experiment."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="run deterministic experiment benchmark")
    run_cmd.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "experiment_results.json",
        help="output json file path",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.command != "run":
        raise ValueError(f"unsupported command: {args.command}")
    result = run_experiment()
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
