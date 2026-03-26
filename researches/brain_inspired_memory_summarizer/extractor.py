from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Callable

_PREFERRED_PATTERNS = (
    re.compile(r"(?:以后)?(?:请)?叫我([A-Za-z\u4e00-\u9fff]{1,16})"),
    re.compile(r"(?:以后)?(?:请)?称呼我([A-Za-z\u4e00-\u9fff]{1,16})"),
    re.compile(r"我(?:更)?喜欢你叫我([A-Za-z\u4e00-\u9fff]{1,16})"),
)
_CITY_RE = re.compile(r"我(?:现在)?住在([A-Za-z\u4e00-\u9fff]{1,24})")
_PET_RE = re.compile(r"我养了一只([A-Za-z\u4e00-\u9fff]{1,24})")
_DAY_RE = re.compile(r"我是周([一二三四五六日天])休息")
_COFFEE_RE = re.compile(r"(不喝咖啡|喝咖啡)")
_BOUNDARY_RE = re.compile(r"(?:请)?(?:不要|别)叫我([A-Za-z\u4e00-\u9fff]{1,16})")
_NO_COFFEE_RE = re.compile(r"(?:不|别|不要)(?:再)?喝咖啡")
_NO_PET_RE = re.compile(r"(?:不|没)(?:有)?养宠物")
_CITY_MOVE_PATTERNS = (
    re.compile(r"(?:我)?搬家了.*?现在住在([A-Za-z\u4e00-\u9fff]{1,24})"),
    re.compile(r"现在住在([A-Za-z\u4e00-\u9fff]{1,24})"),
)

ALLOWED_KEYS = {
    "preferred_name",
    "city",
    "pet",
    "rest_day",
    "coffee_preference",
    "boundary",
}


@dataclass(frozen=True)
class SlotCandidate:
    key: str
    value: str
    confidence: float
    evidence: str
    turn_idx: int
    is_negative: bool = False


LLMExtractFn = Callable[[str, int], list[SlotCandidate]]


def _extract_candidates_regex(text: str, turn_idx: int) -> list[SlotCandidate]:
    """Extract per-turn slot candidates with confidence and evidence."""
    out: list[SlotCandidate] = []
    boundary_blocked_names: set[str] = set()
    for m in _BOUNDARY_RE.finditer(text):
        blocked = m.group(1)
        boundary_blocked_names.add(blocked)
        out.append(
            SlotCandidate(
                key="boundary",
                value=f"不要叫我{blocked}",
                confidence=0.98,
                evidence=m.group(0),
                turn_idx=turn_idx,
            )
        )

    for p in _PREFERRED_PATTERNS:
        for m in p.finditer(text):
            preferred_name = m.group(1)
            if len(preferred_name) <= 1:
                continue
            # Same-turn contradiction: boundary statement wins.
            if preferred_name in boundary_blocked_names:
                continue
            out.append(
                SlotCandidate(
                    key="preferred_name",
                    value=preferred_name,
                    confidence=0.90,
                    evidence=m.group(0),
                    turn_idx=turn_idx,
                )
            )
            break

    city = None
    for p in _CITY_MOVE_PATTERNS:
        city = p.search(text)
        if city:
            break
    if city:
        out.append(
            SlotCandidate(
                key="city",
                value=city.group(1),
                confidence=0.88,
                evidence=city.group(0),
                turn_idx=turn_idx,
            )
        )

    no_pet = _NO_PET_RE.search(text)
    if no_pet:
        out.append(
            SlotCandidate(
                key="pet",
                value="无",
                confidence=0.92,
                evidence=no_pet.group(0),
                turn_idx=turn_idx,
                is_negative=True,
            )
        )
    pet = _PET_RE.search(text)
    if pet and not no_pet:
        out.append(
            SlotCandidate(
                key="pet",
                value=pet.group(1),
                confidence=0.86,
                evidence=pet.group(0),
                turn_idx=turn_idx,
            )
        )

    day = _DAY_RE.search(text)
    if day:
        out.append(
            SlotCandidate(
                key="rest_day",
                value=f"周{day.group(1)}",
                confidence=0.90,
                evidence=day.group(0),
                turn_idx=turn_idx,
            )
        )

    no_coffee = _NO_COFFEE_RE.search(text)
    if no_coffee:
        out.append(
            SlotCandidate(
                key="coffee_preference",
                value="不喝咖啡",
                confidence=0.94,
                evidence=no_coffee.group(0),
                turn_idx=turn_idx,
                is_negative=True,
            )
        )
    coffee = _COFFEE_RE.search(text)
    if coffee and not no_coffee:
        out.append(
            SlotCandidate(
                key="coffee_preference",
                value=coffee.group(1),
                confidence=0.85,
                evidence=coffee.group(0),
                turn_idx=turn_idx,
            )
        )

    return out


def _extract_candidates_llm_default(text: str, turn_idx: int) -> list[SlotCandidate]:
    """
    LLM-based extractor.
    Uses OpenRouter when OPENROUTER_API_KEY is set; otherwise OpenAI direct.
    """
    try:
        from openai import OpenAI
    except ImportError as e:
        raise ImportError(
            "openai package is required for LLM memory extraction backend"
        ) from e

    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openrouter_key:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
        model = os.getenv("INTY_MEMORY_EXTRACTOR_MODEL", "openai/gpt-4o-mini")
    elif openai_key:
        client = OpenAI(api_key=openai_key)
        model = os.getenv("INTY_MEMORY_EXTRACTOR_MODEL", "gpt-4o-mini")
    else:
        raise ValueError(
            "No API key found for LLM extractor; set OPENROUTER_API_KEY or OPENAI_API_KEY"
        )

    system_prompt = (
        "You extract stable user-memory slots from one user utterance.\n"
        "Return ONLY JSON object with key `candidates`.\n"
        "Each candidate item must contain: key, value, confidence, evidence, is_negative.\n"
        "Allowed keys: preferred_name, city, pet, rest_day, coffee_preference, boundary.\n"
        "Rules:\n"
        "- Keep only durable user facts/preferences/boundaries.\n"
        "- If no durable memory, return {\"candidates\": []}.\n"
        "- confidence must be in [0,1].\n"
        "- For explicit negation or prohibition, set is_negative=true.\n"
    )
    user_prompt = f"Utterance:\n{text}"
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    content = resp.choices[0].message.content or '{"candidates":[]}'
    data = json.loads(content)
    raw_items = data.get("candidates", [])
    if not isinstance(raw_items, list):
        raise ValueError("LLM extractor response must include list field candidates")

    out: list[SlotCandidate] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        if key not in ALLOWED_KEYS:
            continue
        value = str(item.get("value", "")).strip()
        evidence = str(item.get("evidence", "")).strip()
        if not value:
            continue
        confidence_raw = item.get("confidence", 0.0)
        confidence = float(confidence_raw)
        if confidence < 0.0:
            confidence = 0.0
        if confidence > 1.0:
            confidence = 1.0
        is_negative = bool(item.get("is_negative", False))
        out.append(
            SlotCandidate(
                key=key,
                value=value,
                confidence=confidence,
                evidence=evidence or value,
                turn_idx=turn_idx,
                is_negative=is_negative,
            )
        )
    return _resolve_same_turn_conflicts(out)


def _resolve_same_turn_conflicts(candidates: list[SlotCandidate]) -> list[SlotCandidate]:
    """
    Keep same-turn extraction consistent:
    if boundary forbids a name, drop preferred_name with same blocked token.
    """
    blocked_names: set[str] = set()
    for c in candidates:
        if c.key != "boundary":
            continue
        m = _BOUNDARY_RE.search(c.value)
        if m:
            blocked_names.add(m.group(1))
    if not blocked_names:
        return candidates
    out: list[SlotCandidate] = []
    for c in candidates:
        if c.key == "preferred_name" and c.value in blocked_names:
            continue
        out.append(c)
    return out


def extract_candidates(
    text: str,
    turn_idx: int,
    *,
    mode: str = "auto",
    llm_extract_fn: LLMExtractFn | None = None,
) -> list[SlotCandidate]:
    """
    Public extraction API with pluggable backend.
    mode:
    - llm: require llm extractor
    - regex: require regex extractor
    - auto: try llm, fallback to regex on configuration/parsing errors
    """
    if mode not in {"llm", "regex", "auto"}:
        raise ValueError(f"unsupported extractor mode: {mode}")
    if mode == "regex":
        return _extract_candidates_regex(text, turn_idx)

    llm_fn = llm_extract_fn or _extract_candidates_llm_default
    if mode == "llm":
        return llm_fn(text, turn_idx)

    # auto mode
    try:
        return llm_fn(text, turn_idx)
    except (ImportError, ValueError, json.JSONDecodeError):
        return _extract_candidates_regex(text, turn_idx)


def extract_memory_facts(text: str, *, mode: str = "auto") -> dict[str, str]:
    """
    Compatibility helper used by baseline agent:
    direct text parse to key-value facts.
    """
    facts: dict[str, str] = {}
    for c in extract_candidates(text, turn_idx=0, mode=mode):
        facts[c.key] = c.value
    return facts


def is_more_reliable_name_candidate(new: SlotCandidate, old: SlotCandidate) -> bool:
    """Reliability rule for preferred-name candidate overwrite."""
    if new.is_negative and not old.is_negative:
        return False
    if old.is_negative and not new.is_negative:
        return True
    if new.turn_idx > old.turn_idx:
        return True
    if new.turn_idx < old.turn_idx:
        return False
    if new.confidence > old.confidence:
        return True
    if new.confidence < old.confidence:
        return False
    return len(new.evidence) > len(old.evidence)


def is_invalid_preferred_name_against_boundary(
    preferred_name: str, boundary_text: str | None
) -> bool:
    """Check cross-slot contradiction: preferred_name blocked by boundary."""
    if not boundary_text:
        return False
    m = _BOUNDARY_RE.search(boundary_text)
    if not m:
        return False
    blocked = m.group(1)
    return preferred_name == blocked
