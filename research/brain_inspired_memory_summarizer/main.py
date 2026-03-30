from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

try:
    from .extractor import (
        EpisodicEvent,
        MemoryCategory,
        SlotCandidate,
        extract_by_memory_category,
        extract_candidates,
        extract_episodic_events_llm,
        extract_memory_facts,
        is_invalid_preferred_name_against_boundary,
        is_more_reliable_name_candidate,
        merge_slot_candidates,
        utterance_memory_categories,
    )
except ImportError:  # script mode (python path/to/main.py)
    from extractor import (  # type: ignore
        EpisodicEvent,
        MemoryCategory,
        SlotCandidate,
        extract_by_memory_category,
        extract_candidates,
        extract_episodic_events_llm,
        extract_memory_facts,
        is_invalid_preferred_name_against_boundary,
        is_more_reliable_name_candidate,
        merge_slot_candidates,
        utterance_memory_categories,
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
    Brain-inspired layered-memory agent:
    - Routing: dialogue → memory subsystem via explicit rules (`utterance_memory_categories`),
      not via LLM pretending to be a classifier.
    - Encoding: per-category extraction (semantic vs self-schema vs episodic) with separate
      LLM instructions when mode is LLM; regex fallback per category in auto/regex mode.
    - Episodic buffer + consolidation: repeated evidence from episodic traces can promote
      semantic slots (systems-consolidation style), in addition to direct semantic encoding.
    - Read path: L4 semantic + short window (working-memory analogue).
    """

    _CONFIDENCE_FLOOR = 0.75
    _EPISODIC_SALIENCE_FOR_CONSOLIDATION = 0.65
    _EPISODIC_PROMOTION_HITS = 2

    def __init__(
        self,
        window_size: int,
        candidate_extractor: Callable[[str, int], list[SlotCandidate]] | None = None,
        *,
        extract_mode: str = "auto",
        slot_llm_extract_fn: Callable[[str, int], list[SlotCandidate]] | None = None,
        episodic_llm_call: Callable[[str], str] | None = None,
    ) -> None:
        self.window_size = window_size
        self.user_turns: list[str] = []
        self.semantic_memory: dict[str, str] = {}
        self._best_candidates: dict[str, SlotCandidate] = {}
        self._turn_counter = 0
        self._extract_mode = extract_mode
        self._slot_llm_extract_fn = slot_llm_extract_fn
        self._episodic_llm_call = episodic_llm_call
        self._legacy_extractor = candidate_extractor
        self.episodic_buffer: list[EpisodicEvent] = []
        self._episodic_slot_hits: dict[tuple[str, str], int] = defaultdict(int)

    def ingest_user_turn(self, text: str) -> None:
        self._turn_counter += 1
        self.user_turns.append(text)

        if self._legacy_extractor is not None:
            candidates = self._legacy_extractor(text, self._turn_counter)
        else:
            categories = utterance_memory_categories(text)
            candidates = self._extract_routed(text, self._turn_counter, categories)
            if MemoryCategory.EPISODIC in categories:
                new_episodic = extract_episodic_events_llm(
                    text,
                    self._turn_counter,
                    episodic_llm_call=self._episodic_llm_call,
                )
                self.episodic_buffer.extend(new_episodic)
                self._consolidate_semantic_from_episodic(new_episodic)

        # Salience gate (still lightweight): apply confidence floor to avoid weak noise.
        for c in candidates:
            if c.confidence < self._CONFIDENCE_FLOOR:
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

    def _extract_routed(
        self,
        text: str,
        turn_idx: int,
        categories: frozenset[MemoryCategory],
    ) -> list[SlotCandidate]:
        out: list[SlotCandidate] = []
        if MemoryCategory.SEMANTIC in categories:
            sem = extract_by_memory_category(
                text,
                turn_idx,
                MemoryCategory.SEMANTIC,
                mode=self._extract_mode,
                llm_extract_fn=self._slot_llm_extract_fn,
            )
            out.extend(sem)  # type: ignore[arg-type]
        if MemoryCategory.SELF_SCHEMA in categories:
            ss = extract_by_memory_category(
                text,
                turn_idx,
                MemoryCategory.SELF_SCHEMA,
                mode=self._extract_mode,
                llm_extract_fn=self._slot_llm_extract_fn,
            )
            out.extend(ss)  # type: ignore[arg-type]
        return merge_slot_candidates(out)

    def _consolidate_semantic_from_episodic(self, new_events: list[EpisodicEvent]) -> None:
        """
        Hippocampus→neocortex style: scan salient episodic traces for latent semantic slots;
        promote to LTM after repeated traces (independent consolidation passes).
        Each episodic event is processed once when appended.
        """
        for ev in new_events:
            if ev.salience_hint < self._EPISODIC_SALIENCE_FOR_CONSOLIDATION:
                continue
            for c in extract_by_memory_category(
                ev.evidence,
                ev.turn_idx,
                MemoryCategory.SEMANTIC,
                mode="regex",
            ):
                slot_key = (c.key, c.value)
                self._episodic_slot_hits[slot_key] += 1
                if self._episodic_slot_hits[slot_key] < self._EPISODIC_PROMOTION_HITS:
                    continue
                if c.confidence < self._CONFIDENCE_FLOOR:
                    continue
                old = self._best_candidates.get(c.key)
                if old is None or c.turn_idx >= old.turn_idx:
                    self._best_candidates[c.key] = c
                    self.semantic_memory[c.key] = c.value

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


def _slot_rows(candidates: list[SlotCandidate]) -> list[dict[str, Any]]:
    return [asdict(c) for c in candidates]


def _episodic_rows(events: list[EpisodicEvent]) -> list[dict[str, Any]]:
    return [asdict(e) for e in events]


def build_extraction_trace(
    episode: Episode,
    *,
    window_size: int = 2,
    extract_mode: str = "regex",
) -> list[dict[str, Any]]:
    """
    Per-turn view of rule-based routing and independent per-type extraction,
    plus layered agent semantic memory after each turn (demo / audit).
    """
    agent = LayeredMemoryAgent(
        window_size=window_size,
        extract_mode=extract_mode,
    )
    trace: list[dict[str, Any]] = []
    for text in episode.user_turns:
        agent.ingest_user_turn(text)
        turn_idx = agent._turn_counter
        cats = utterance_memory_categories(text)
        active = sorted(
            c.value
            for c in cats
            if c
            not in (
                MemoryCategory.SENSORY_BUFFER,
                MemoryCategory.WORKING,
            )
        )
        semantic_raw: list[SlotCandidate] = []
        self_schema_raw: list[SlotCandidate] = []
        episodic_raw: list[EpisodicEvent] = []
        if MemoryCategory.SEMANTIC in cats:
            semantic_raw = extract_by_memory_category(  # type: ignore[assignment]
                text,
                turn_idx,
                MemoryCategory.SEMANTIC,
                mode=extract_mode,
            )
        if MemoryCategory.SELF_SCHEMA in cats:
            self_schema_raw = extract_by_memory_category(  # type: ignore[assignment]
                text,
                turn_idx,
                MemoryCategory.SELF_SCHEMA,
                mode=extract_mode,
            )
        if MemoryCategory.EPISODIC in cats:
            episodic_raw = extract_episodic_events_llm(  # type: ignore[assignment]
                text,
                turn_idx,
                episodic_llm_call=None,
            )
        trace.append(
            {
                "turn_index": turn_idx,
                "user_text": text,
                "routed_categories": active,
                "semantic_candidates": _slot_rows(semantic_raw),
                "self_schema_candidates": _slot_rows(self_schema_raw),
                "episodic_events": _episodic_rows(episodic_raw),
                "semantic_long_term_after_turn": dict(agent.semantic_memory),
                "episodic_buffer_length": len(agent.episodic_buffer),
            }
        )
    return trace


def build_qa_per_question_rows(episodes: list[Episode]) -> list[dict[str, Any]]:
    small = NaiveWindowAgent(window_size=2)
    large = NaiveWindowAgent(window_size=99)
    layered = LayeredMemoryAgent(window_size=2)
    rows: list[dict[str, Any]] = []
    for ep in episodes:
        for turn in ep.user_turns:
            small.ingest_user_turn(turn)
            large.ingest_user_turn(turn)
            layered.ingest_user_turn(turn)
        for qa in ep.qa:
            a_s, c_s, l_s = small.answer(qa.key)
            a_l, c_l, l_l = large.answer(qa.key)
            a_d, c_d, l_d = layered.answer(qa.key)
            rows.append(
                {
                    "episode_id": ep.episode_id,
                    "question": qa.question,
                    "slot_key": qa.key,
                    "expected": qa.expected,
                    "baseline_small_answer": a_s,
                    "baseline_small_correct": a_s == qa.expected,
                    "baseline_small_context_chars": c_s,
                    "baseline_large_answer": a_l,
                    "baseline_large_correct": a_l == qa.expected,
                    "baseline_large_context_chars": c_l,
                    "layered_answer": a_d,
                    "layered_correct": a_d == qa.expected,
                    "layered_context_chars": c_d,
                }
            )
    return rows


def build_full_experiment_artifact(
    *,
    window_size: int = 2,
    extract_mode: str = "regex",
) -> dict[str, Any]:
    episodes = build_dataset()
    metrics = run_experiment()
    traces = {
        ep.episode_id: build_extraction_trace(
            ep, window_size=window_size, extract_mode=extract_mode
        )
        for ep in episodes
    }
    return {
        "metrics": metrics,
        "settings": {
            "window_size": window_size,
            "extract_mode": extract_mode,
        },
        "extraction_traces_by_episode": traces,
        "qa_per_question": build_qa_per_question_rows(episodes),
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
        help="aggregate metrics JSON path",
    )
    run_cmd.add_argument(
        "--full-out",
        type=Path,
        default=Path(__file__).resolve().parent / "experiment_full.json",
        help="full artifact: per-turn extraction trace + per-question QA rows",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.command != "run":
        raise ValueError(f"unsupported command: {args.command}")
    result = run_experiment()
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    full = build_full_experiment_artifact()
    args.full_out.write_text(
        json.dumps(full, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
