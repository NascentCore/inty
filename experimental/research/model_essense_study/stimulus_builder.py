from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Sequence

from loguru import logger

from research.model_essense_study.schema import (
    StimulusCandidateRecord,
    StimulusRecord,
)

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(\+?\d[\d\-\s()]{7,}\d)")
WHITESPACE_PATTERN = re.compile(r"\s+")
WORD_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
URL_PATTERN = re.compile(r"https?://\S+")


def _sanitize_text(text: str) -> str:
    no_email = EMAIL_PATTERN.sub("[EMAIL]", text)
    no_phone = PHONE_PATTERN.sub("[PHONE]", no_email)
    no_url = URL_PATTERN.sub("[URL]", no_phone)
    compact = WHITESPACE_PATTERN.sub(" ", no_url).strip()
    return compact


def _english_ratio(text: str) -> float:
    if not text:
        return 0.0
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    ascii_letters = [ch for ch in letters if ch.isascii()]
    return len(ascii_letters) / len(letters)


def _word_count(text: str) -> int:
    return len(WORD_PATTERN.findall(text))


def _near_dedup_key(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^a-z0-9\s']", " ", lowered)
    lowered = WHITESPACE_PATTERN.sub(" ", lowered).strip()
    tokens = lowered.split(" ")
    normalized = " ".join(tokens[:40])
    return normalized


def _build_stimulus_id(source_hash: str, message_id: int, text: str) -> str:
    digest = hashlib.sha256(
        f"{source_hash}:{message_id}:{text}".encode("utf-8")
    ).hexdigest()
    return f"stim-{digest[:12]}"


def _topic_bucket(text: str) -> str:
    lowered = text.lower()
    if any(k in lowered for k in ("stress", "anxious", "anxiety", "sad", "depressed")):
        return "emotional_support"
    if any(k in lowered for k in ("love", "relationship", "boyfriend", "girlfriend", "date", "kiss", "sex")):
        return "relationship"
    if any(k in lowered for k in ("should i", "what should", "advice", "help me decide")):
        return "advice"
    if any(k in lowered for k in ("hello", "hi ", "hey ", "nice to meet", "how are you")):
        return "greeting"
    return "general"


@dataclass(frozen=True)
class StimulusBuildResult:
    items: list[StimulusRecord]
    summary: dict[str, object]


def _prioritize_candidates(
    candidates: Sequence[StimulusCandidateRecord],
) -> list[StimulusCandidateRecord]:
    # Keep deterministic priority: newer first if created_at exists, else by candidate_id
    return sorted(
        candidates,
        key=lambda item: (item.created_at or "", item.candidate_id),
        reverse=True,
    )


def build_stimuli(
    *,
    candidates: Sequence[StimulusCandidateRecord],
    target_count: int,
    min_length: int,
    max_length: int,
    english_ratio_min: float,
) -> StimulusBuildResult:
    dedup_seen: set[str] = set()
    bucketed: dict[str, list[StimulusRecord]] = {}
    filtered_counts = {
        "too_short_or_long": 0,
        "low_english_ratio": 0,
        "word_count_out_of_range": 0,
        "deduplicated": 0,
    }
    candidate_sorted = _prioritize_candidates(candidates)
    for item in candidate_sorted:
        clean_text = _sanitize_text(item.text)
        if len(clean_text) < min_length or len(clean_text) > max_length:
            filtered_counts["too_short_or_long"] += 1
            continue
        ratio = _english_ratio(clean_text)
        if ratio < english_ratio_min:
            filtered_counts["low_english_ratio"] += 1
            continue
        wc = _word_count(clean_text)
        if wc == 0 or wc > 120:
            filtered_counts["word_count_out_of_range"] += 1
            continue
        dedup_key = _near_dedup_key(clean_text)
        if dedup_key in dedup_seen:
            filtered_counts["deduplicated"] += 1
            continue
        dedup_seen.add(dedup_key)
        bucket = _topic_bucket(clean_text)
        record = StimulusRecord(
            stimulus_id=_build_stimulus_id(
                item.source_session_id_hash, item.source_chat_message_id, clean_text
            ),
            text=clean_text,
            source_chat_id_hash=item.source_session_id_hash,
            source_message_id=item.source_chat_message_id,
            language="en",
            char_count=len(clean_text),
            english_ratio=ratio,
            topic_bucket=bucket,
        )
        bucketed.setdefault(bucket, []).append(record)

    if not bucketed:
        return StimulusBuildResult(
            items=[],
            summary={
                "selected_count": 0,
                "target_count": target_count,
                "topic_distribution": {},
                "avg_length_chars": 0,
                "avg_english_ratio": 0.0,
                "candidate_count": len(candidates),
                "filtered_counts": filtered_counts,
            },
        )

    selected: list[StimulusRecord] = []
    buckets = sorted(bucketed.keys())
    per_round = max(1, target_count // len(buckets))
    while len(selected) < target_count:
        progressed = False
        for bucket in buckets:
            bucket_items = bucketed[bucket]
            take_n = min(per_round, len(bucket_items))
            if take_n == 0:
                continue
            progressed = True
            selected.extend(bucket_items[:take_n])
            del bucket_items[:take_n]
            if len(selected) >= target_count:
                break
        if not progressed:
            break
    selected_final = selected[:target_count]
    topic_distribution: dict[str, int] = {}
    for item in selected_final:
        topic_distribution[item.topic_bucket] = (
            topic_distribution.get(item.topic_bucket, 0) + 1
        )
    avg_len = (
        sum(len(item.text) for item in selected_final) / len(selected_final)
        if selected_final
        else 0
    )
    avg_ratio = (
        sum(item.english_ratio for item in selected_final) / len(selected_final)
        if selected_final
        else 0.0
    )
    summary = {
        "candidate_count": len(candidates),
        "selected_count": len(selected_final),
        "target_count": target_count,
        "topic_distribution": topic_distribution,
        "avg_length_chars": round(avg_len, 2),
        "avg_english_ratio": round(avg_ratio, 4),
        "filtered_counts": filtered_counts,
    }
    logger.info(
        "Stimulus selection completed: selected={} target={}",
        len(selected_final),
        target_count,
    )
    return StimulusBuildResult(items=selected_final, summary=summary)


def build_mock_stimulus_candidates() -> list[StimulusCandidateRecord]:
    samples: list[str] = []
    greetings = [
        "Hey",
        "Hi",
        "Hello",
    ]
    concerns = [
        "I've been stressed at work this week",
        "I had an argument with my partner yesterday",
        "I feel confused about my next life step",
        "I miss someone and don't know what to do",
        "I keep overthinking before sleep",
    ]
    asks = [
        "could you help me sort out my thoughts?",
        "what would you do in my situation?",
        "how can I calm down tonight?",
        "should I text them first or wait?",
        "can you help me decide what matters most?",
    ]
    closings = [
        "I want your honest advice.",
        "Please be direct with me.",
        "I trust your perspective.",
        "I need a practical next step.",
        "I also care about the emotional side.",
    ]
    for greeting in greetings:
        for concern in concerns:
            for ask in asks:
                for closing in closings:
                    samples.append(f"{greeting}, {concern}; {ask} {closing}")

    relationship_questions = [
        "Do you think trust can be rebuilt after betrayal?",
        "How can two people reconnect after emotional distance?",
        "What does a healthy relationship boundary look like?",
        "Why do people avoid hard conversations in love?",
        "Can affection and independence coexist long-term?",
    ]
    reflective_prefix = [
        "I have been wondering lately:",
        "I keep asking myself:",
        "I need your view on this:",
        "This question has been on my mind:",
    ]
    for prefix in reflective_prefix:
        for question in relationship_questions:
            samples.append(f"{prefix} {question}")

    out: list[StimulusCandidateRecord] = []
    idx = 1
    for text in samples:
        source_hash = hashlib.sha256(f"mock-chat:{idx}".encode("utf-8")).hexdigest()[:16]
        out.append(
            StimulusCandidateRecord(
                candidate_id=f"mock-{idx}",
                text=text,
                source_chat_message_id=idx,
                source_session_id_hash=source_hash,
                created_at=None,
            )
        )
        idx += 1
    return out

