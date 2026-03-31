from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

_LOG = logging.getLogger("brain_memory_exp")


def configure_logging(*, verbose: bool) -> None:
    """Progress and LLM traces go to stderr; final JSON metrics stay on stdout."""
    level = logging.DEBUG if verbose else logging.INFO
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

try:
    from .extractor import (
        EpisodicEvent,
        MemoryCategory,
        SlotCandidate,
        build_live_episodic_llm_call,
        build_live_route_llm_call,
        build_live_slot_extract_fn,
        extract_by_memory_category,
        extract_candidates,
        extract_episodic_events_llm,
        is_invalid_preferred_name_against_boundary,
        is_more_reliable_name_candidate,
        llm_extract_memory_slots,
        merge_slot_candidates,
        route_memory_categories_llm,
    )
except ImportError:  # script mode (python path/to/main.py)
    from extractor import (  # type: ignore
        EpisodicEvent,
        MemoryCategory,
        SlotCandidate,
        build_live_episodic_llm_call,
        build_live_route_llm_call,
        build_live_slot_extract_fn,
        extract_by_memory_category,
        extract_candidates,
        extract_episodic_events_llm,
        is_invalid_preferred_name_against_boundary,
        is_more_reliable_name_candidate,
        llm_extract_memory_slots,
        merge_slot_candidates,
        route_memory_categories_llm,
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


def benchmark_slot_json_by_line() -> dict[str, str]:
    """Deterministic slot LLM payloads keyed by exact `build_dataset()` user lines (not regex parsing)."""

    def _c(
        key: str,
        value: str,
        conf: float,
        evidence: str,
        *,
        neg: bool = False,
    ) -> dict[str, object]:
        return {
            "key": key,
            "value": value,
            "confidence": conf,
            "evidence": evidence,
            "is_negative": neg,
        }

    return {
        "以后请叫我阿辰。": json.dumps([_c("preferred_name", "阿辰", 0.93, "以后请叫我阿辰")], ensure_ascii=False),
        "今天会议很多，先记个待办。": "[]",
        "我现在住在杭州。": json.dumps([_c("city", "杭州", 0.89, "现在住在杭州")], ensure_ascii=False),
        "最近工作挺忙，回消息可能慢一点。": "[]",
        "我养了一只边牧。": json.dumps([_c("pet", "边牧", 0.88, "养了一只边牧")], ensure_ascii=False),
        "今天的午饭一般般。": "[]",
        "我是周三休息。": json.dumps([_c("rest_day", "周三", 0.91, "周三休息")], ensure_ascii=False),
        "晚上可能去散步。": "[]",
        "我不喝咖啡。": json.dumps(
            [_c("coffee_preference", "不喝咖啡", 0.94, "不喝咖啡", neg=True)],
            ensure_ascii=False,
        ),
        "请不要叫我宝贝。": json.dumps(
            [_c("boundary", "不要叫我宝贝", 0.97, "不要叫我宝贝")],
            ensure_ascii=False,
        ),
        "我搬家了，我现在住在上海。": json.dumps(
            [_c("city", "上海", 0.92, "现在住在上海")],
            ensure_ascii=False,
        ),
        "顺便说下，今天我只是想闲聊。": "[]",
        "刚刚在看电影，剧情还不错。": "[]",
        "这会儿有点困，准备休息了。": "[]",
    }


def benchmark_route_json_by_line() -> dict[str, str]:
    return {
        "以后请叫我阿辰。": json.dumps({"active_subsystems": ["semantic"]}, ensure_ascii=False),
        "今天会议很多，先记个待办。": json.dumps({"active_subsystems": ["episodic"]}, ensure_ascii=False),
        "我现在住在杭州。": json.dumps({"active_subsystems": ["semantic"]}, ensure_ascii=False),
        "最近工作挺忙，回消息可能慢一点。": json.dumps({"active_subsystems": ["episodic"]}, ensure_ascii=False),
        "我养了一只边牧。": json.dumps({"active_subsystems": ["semantic"]}, ensure_ascii=False),
        "今天的午饭一般般。": json.dumps({"active_subsystems": ["episodic"]}, ensure_ascii=False),
        "我是周三休息。": json.dumps({"active_subsystems": ["semantic"]}, ensure_ascii=False),
        "晚上可能去散步。": json.dumps({"active_subsystems": ["episodic"]}, ensure_ascii=False),
        "我不喝咖啡。": json.dumps({"active_subsystems": ["semantic"]}, ensure_ascii=False),
        "请不要叫我宝贝。": json.dumps({"active_subsystems": ["self_schema"]}, ensure_ascii=False),
        "我搬家了，我现在住在上海。": json.dumps(
            {"active_subsystems": ["semantic", "episodic"]}, ensure_ascii=False
        ),
        "顺便说下，今天我只是想闲聊。": json.dumps({"active_subsystems": ["episodic"]}, ensure_ascii=False),
        "刚刚在看电影，剧情还不错。": json.dumps({"active_subsystems": ["episodic"]}, ensure_ascii=False),
        "这会儿有点困，准备休息了。": json.dumps({"active_subsystems": ["episodic"]}, ensure_ascii=False),
    }


def benchmark_episodic_json_by_line() -> dict[str, str]:
    def _ev(gist: str, sal: float, evidence: str) -> dict[str, object]:
        return {"gist": gist, "salience_hint": sal, "evidence": evidence}

    return {
        "今天会议很多，先记个待办。": json.dumps(
            {"events": [_ev("busy with meetings", 0.55, "今天会议很多，先记个待办。")]},
            ensure_ascii=False,
        ),
        "最近工作挺忙，回消息可能慢一点。": json.dumps(
            {"events": [_ev("busy at work", 0.55, "最近工作挺忙，回消息可能慢一点。")]},
            ensure_ascii=False,
        ),
        "今天的午饭一般般。": json.dumps(
            {"events": [_ev("lunch was mediocre", 0.5, "今天的午饭一般般。")]},
            ensure_ascii=False,
        ),
        "晚上可能去散步。": json.dumps(
            {"events": [_ev("may take a walk", 0.5, "晚上可能去散步。")]},
            ensure_ascii=False,
        ),
        "我搬家了，我现在住在上海。": json.dumps(
            {"events": [_ev("moved house", 0.85, "我搬家了，我现在住在上海。")]},
            ensure_ascii=False,
        ),
        "顺便说下，今天我只是想闲聊。": json.dumps(
            {"events": [_ev("small talk", 0.5, "顺便说下，今天我只是想闲聊。")]},
            ensure_ascii=False,
        ),
        "刚刚在看电影，剧情还不错。": json.dumps(
            {"events": [_ev("watching a movie", 0.55, "刚刚在看电影，剧情还不错。")]},
            ensure_ascii=False,
        ),
        "这会儿有点困，准备休息了。": json.dumps(
            {"events": [_ev("tired, going to rest", 0.55, "这会儿有点困，准备休息了。")]},
            ensure_ascii=False,
        ),
    }


def build_benchmark_slot_llm_extract_fn(
    lines_to_json: dict[str, str] | None = None,
) -> Callable[[str, int], list[SlotCandidate]]:
    m = lines_to_json or benchmark_slot_json_by_line()

    def fn(text: str, turn_idx: int) -> list[SlotCandidate]:
        raw = m.get(text)
        if raw is None:
            return []
        return llm_extract_memory_slots(text, turn_idx, lambda _: raw)

    return fn


def build_benchmark_route_llm_call(
    lines_to_json: dict[str, str] | None = None,
) -> Callable[[str], str]:
    m = lines_to_json or benchmark_route_json_by_line()

    def route(text: str) -> str:
        return m.get(text, json.dumps({"active_subsystems": []}, ensure_ascii=False))

    return route


def build_benchmark_episodic_llm_call(
    lines_to_json: dict[str, str] | None = None,
) -> Callable[[str], str]:
    m = lines_to_json or benchmark_episodic_json_by_line()

    def episodic(text: str) -> str:
        return m.get(text, json.dumps({"events": []}, ensure_ascii=False))

    return episodic


def _facts_from_visible_lines(
    lines: list[str],
    llm_extract_fn: Callable[[str, int], list[SlotCandidate]],
) -> dict[str, str]:
    """Merge slot keys from visible lines in order; later lines overwrite."""
    facts: dict[str, str] = {}
    for i, line in enumerate(lines):
        for c in llm_extract_fn(line, i + 1):
            facts[c.key] = c.value
    return facts


class NaiveWindowAgent:
    """
    Baseline agent: only sees a fixed number of recent user lines.
    Memory is read by running the slot LLM on each visible line (no regex).
    """

    def __init__(
        self,
        window_size: int,
        llm_extract_fn: Callable[[str, int], list[SlotCandidate]],
    ) -> None:
        self.window_size = window_size
        self.user_turns: list[str] = []
        self._llm_extract_fn = llm_extract_fn

    def ingest_user_turn(self, text: str) -> None:
        self.user_turns.append(text)

    def _visible_context(self) -> list[str]:
        if len(self.user_turns) <= self.window_size:
            return self.user_turns
        return self.user_turns[-self.window_size :]

    def answer(self, key: str) -> tuple[str, int, int]:
        ctx = self._visible_context()
        extracted = _facts_from_visible_lines(ctx, self._llm_extract_fn)
        return extracted.get(key, _UNKNOWN), _context_chars(ctx), len(ctx)

    @property
    def memory_item_count(self) -> int:
        return 0


class LayeredMemoryAgent:
    """
    Brain-inspired layered-memory agent (LLM-only extraction):
    - Routing: optional `route_llm_call` classifies which subsystems run; default uses API.
    - Encoding: per-category LLM calls (semantic, self-schema, episodic).
    - Consolidation: salient episodic evidence is passed through the semantic slot LLM again;
      repeated (key,value) promotions simulate consolidation.
    - Read path: L4 semantic + short window; missing keys fall back to slot LLM on visible lines.
    """

    _CONFIDENCE_FLOOR = 0.75
    _EPISODIC_SALIENCE_FOR_CONSOLIDATION = 0.65
    _EPISODIC_PROMOTION_HITS = 2

    def __init__(
        self,
        window_size: int,
        candidate_extractor: Callable[[str, int], list[SlotCandidate]] | None = None,
        *,
        slot_llm_extract_fn: Callable[[str, int], list[SlotCandidate]] | None = None,
        route_llm_call: Callable[[str], str] | None = None,
        episodic_llm_call: Callable[[str], str] | None = None,
    ) -> None:
        self.window_size = window_size
        self.user_turns: list[str] = []
        self.semantic_memory: dict[str, str] = {}
        self._best_candidates: dict[str, SlotCandidate] = {}
        self._turn_counter = 0
        self._slot_llm_extract_fn = slot_llm_extract_fn or extract_candidates
        self._route_llm_call = route_llm_call
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
            categories = route_memory_categories_llm(text, route_llm_call=self._route_llm_call)
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
                llm_extract_fn=self._slot_llm_extract_fn,
            )
            out.extend(sem)  # type: ignore[arg-type]
        if MemoryCategory.SELF_SCHEMA in categories:
            ss = extract_by_memory_category(
                text,
                turn_idx,
                MemoryCategory.SELF_SCHEMA,
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
                llm_extract_fn=self._slot_llm_extract_fn,
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

        extracted = _facts_from_visible_lines(ctx, self._slot_llm_extract_fn)
        return extracted.get(key, _UNKNOWN), _context_chars(ctx), len(ctx)

    @property
    def memory_item_count(self) -> int:
        return len(self.semantic_memory)


def evaluate_agent(
    agent: NaiveWindowAgent | LayeredMemoryAgent,
    episodes: list[Episode],
    *,
    arm_name: str = "agent",
) -> EvaluationMetrics:
    total_questions = 0
    correct = 0
    total_context_chars = 0
    total_context_lines = 0
    max_memory_items = 0

    for ep in episodes:
        _LOG.info(
            "[%s] episode=%s ingest %d user turns",
            arm_name,
            ep.episode_id,
            len(ep.user_turns),
        )
        t0 = time.perf_counter()
        for i, turn in enumerate(ep.user_turns, start=1):
            preview = turn if len(turn) <= 80 else turn[:77] + "..."
            _LOG.info(
                "[%s] episode=%s ingest turn %d/%d preview=%r",
                arm_name,
                ep.episode_id,
                i,
                len(ep.user_turns),
                preview,
            )
            agent.ingest_user_turn(turn)
        _LOG.info(
            "[%s] episode=%s ingest done elapsed_s=%.2f ltm_keys=%d",
            arm_name,
            ep.episode_id,
            time.perf_counter() - t0,
            getattr(agent, "memory_item_count", 0),
        )

        for qa in ep.qa:
            answer, chars, lines = agent.answer(qa.key)
            total_questions += 1
            total_context_chars += chars
            total_context_lines += lines
            ok = answer == qa.expected
            if ok:
                correct += 1
            _LOG.info(
                "[%s] QA key=%s answer=%r expected=%r match=%s context_chars=%d context_lines=%d",
                arm_name,
                qa.key,
                answer,
                qa.expected,
                ok,
                chars,
                lines,
            )

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


def run_experiment(*, use_live_llm: bool = False) -> dict[str, float]:
    episodes = build_dataset()
    _LOG.info(
        "run_experiment start episodes=%d use_live_llm=%s",
        len(episodes),
        use_live_llm,
    )
    t_all = time.perf_counter()
    if use_live_llm:
        slot_fn = build_live_slot_extract_fn()
        route_call = build_live_route_llm_call()
        episodic_call = build_live_episodic_llm_call()
    else:
        slot_fn = build_benchmark_slot_llm_extract_fn()
        route_call = build_benchmark_route_llm_call()
        episodic_call = build_benchmark_episodic_llm_call()
    baseline_small = evaluate_agent(
        NaiveWindowAgent(window_size=2, llm_extract_fn=slot_fn),
        episodes,
        arm_name="baseline_small_window",
    )
    baseline_large = evaluate_agent(
        NaiveWindowAgent(window_size=99, llm_extract_fn=slot_fn),
        episodes,
        arm_name="baseline_large_window",
    )
    layered = evaluate_agent(
        LayeredMemoryAgent(
            window_size=2,
            slot_llm_extract_fn=slot_fn,
            route_llm_call=route_call,
            episodic_llm_call=episodic_call,
        ),
        episodes,
        arm_name="layered_memory",
    )

    _LOG.info(
        "run_experiment done elapsed_s=%.2f layered_accuracy=%.3f",
        time.perf_counter() - t_all,
        layered.accuracy,
    )
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
        "use_live_llm": 1.0 if use_live_llm else 0.0,
    }


def _slot_rows(candidates: list[SlotCandidate]) -> list[dict[str, Any]]:
    return [asdict(c) for c in candidates]


def _episodic_rows(events: list[EpisodicEvent]) -> list[dict[str, Any]]:
    return [asdict(e) for e in events]


def build_extraction_trace(
    episode: Episode,
    *,
    window_size: int = 2,
    slot_llm_extract_fn: Callable[[str, int], list[SlotCandidate]] | None = None,
    route_llm_call: Callable[[str], str] | None = None,
    episodic_llm_call: Callable[[str], str] | None = None,
) -> list[dict[str, Any]]:
    """
    Per-turn view of LLM routing and independent per-type extraction,
    plus layered agent semantic memory after each turn (demo / audit).
    """
    slot_fn = slot_llm_extract_fn or build_benchmark_slot_llm_extract_fn()
    route_call = route_llm_call or build_benchmark_route_llm_call()
    epi_call = episodic_llm_call or build_benchmark_episodic_llm_call()
    agent = LayeredMemoryAgent(
        window_size=window_size,
        slot_llm_extract_fn=slot_fn,
        route_llm_call=route_call,
        episodic_llm_call=epi_call,
    )
    trace: list[dict[str, Any]] = []
    for text in episode.user_turns:
        agent.ingest_user_turn(text)
        turn_idx = agent._turn_counter
        cats = route_memory_categories_llm(text, route_llm_call=route_call)
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
                llm_extract_fn=slot_fn,
            )
        if MemoryCategory.SELF_SCHEMA in cats:
            self_schema_raw = extract_by_memory_category(  # type: ignore[assignment]
                text,
                turn_idx,
                MemoryCategory.SELF_SCHEMA,
                llm_extract_fn=slot_fn,
            )
        if MemoryCategory.EPISODIC in cats:
            episodic_raw = extract_episodic_events_llm(  # type: ignore[assignment]
                text,
                turn_idx,
                episodic_llm_call=epi_call,
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


def build_qa_per_question_rows(
    episodes: list[Episode],
    *,
    use_live_llm: bool = False,
) -> list[dict[str, Any]]:
    if use_live_llm:
        slot_fn = build_live_slot_extract_fn()
        route_call = build_live_route_llm_call()
        episodic_call = build_live_episodic_llm_call()
    else:
        slot_fn = build_benchmark_slot_llm_extract_fn()
        route_call = build_benchmark_route_llm_call()
        episodic_call = build_benchmark_episodic_llm_call()
    small = NaiveWindowAgent(window_size=2, llm_extract_fn=slot_fn)
    large = NaiveWindowAgent(window_size=99, llm_extract_fn=slot_fn)
    layered = LayeredMemoryAgent(
        window_size=2,
        slot_llm_extract_fn=slot_fn,
        route_llm_call=route_call,
        episodic_llm_call=episodic_call,
    )
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
    use_live_llm: bool = False,
) -> dict[str, Any]:
    episodes = build_dataset()
    _LOG.info(
        "build_full_experiment_artifact: re-running metrics (duplicate work) use_live_llm=%s",
        use_live_llm,
    )
    metrics = run_experiment(use_live_llm=use_live_llm)
    if use_live_llm:
        slot_fn = build_live_slot_extract_fn()
        route_call = build_live_route_llm_call()
        episodic_call = build_live_episodic_llm_call()
        extraction_label = "llm_live_api"
    else:
        slot_fn = build_benchmark_slot_llm_extract_fn()
        route_call = build_benchmark_route_llm_call()
        episodic_call = build_benchmark_episodic_llm_call()
        extraction_label = "llm_only_benchmark_stubs"
    traces: dict[str, list[dict[str, Any]]] = {}
    for ep in episodes:
        _LOG.info("build_extraction_trace episode=%s turns=%d", ep.episode_id, len(ep.user_turns))
        traces[ep.episode_id] = build_extraction_trace(
            ep,
            window_size=window_size,
            slot_llm_extract_fn=slot_fn,
            route_llm_call=route_call,
            episodic_llm_call=episodic_call,
        )
    return {
        "metrics": metrics,
        "settings": {
            "window_size": window_size,
            "extraction": extraction_label,
            "use_live_llm": use_live_llm,
        },
        "extraction_traces_by_episode": traces,
        "qa_per_question": _log_qa_build(
            build_qa_per_question_rows(episodes, use_live_llm=use_live_llm)
        ),
    }


def _log_qa_build(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    _LOG.info("build_qa_per_question_rows done rows=%d", len(rows))
    return rows


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
        default=None,
        help="full artifact path (default: experiment_full.json or experiment_full_live.json)",
    )
    run_cmd.add_argument(
        "--live-llm",
        action="store_true",
        help="call real OpenAI/OpenRouter API (needs OPENROUTER_API_KEY or OPENAI_API_KEY); slow, non-deterministic",
    )
    run_cmd.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="DEBUG on stderr (includes LLM user_preview); default is INFO progress on stderr",
    )
    run_cmd.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="only WARNING+ on stderr (minimal noise; final JSON still on stdout)",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.command != "run":
        raise ValueError(f"unsupported command: {args.command}")
    if getattr(args, "quiet", False) and getattr(args, "verbose", False):
        raise ValueError("use only one of --quiet and --verbose")
    if getattr(args, "quiet", False):
        configure_logging(verbose=False)
        logging.getLogger().setLevel(logging.WARNING)
    else:
        configure_logging(verbose=bool(getattr(args, "verbose", False)))
    live = bool(getattr(args, "live_llm", False))
    _LOG.info("main run live_llm=%s", live)
    result = run_experiment(use_live_llm=live)
    out_path = args.out
    if live and args.out == Path(__file__).resolve().parent / "experiment_results.json":
        out_path = Path(__file__).resolve().parent / "experiment_results_live.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _LOG.info("wrote metrics -> %s", out_path)
    full_out = args.full_out
    if full_out is None:
        full_out = (
            Path(__file__).resolve().parent / "experiment_full_live.json"
            if live
            else Path(__file__).resolve().parent / "experiment_full.json"
        )
    full = build_full_experiment_artifact(use_live_llm=live)
    full_out.write_text(
        json.dumps(full, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _LOG.info("wrote full artifact -> %s", full_out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
