from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from enum import Enum
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

# Brain-inspired split: durable facts/preferences vs stable boundaries/values (self-schema).
SEMANTIC_ALLOWED_KEYS = frozenset(
    {"preferred_name", "city", "pet", "rest_day", "coffee_preference"}
)
SELF_SCHEMA_ALLOWED_KEYS = frozenset({"boundary"})


class MemoryCategory(str, Enum):
    """Cognitive-style memory kinds used for routing and independent extraction."""

    SENSORY_BUFFER = "sensory_buffer"
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    SELF_SCHEMA = "self_schema"


def _slot_candidate_schema_properties(allowed: frozenset[str]) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "key": {
                "type": "string",
                "enum": sorted(allowed),
            },
            "value": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "evidence": {"type": "string"},
            "is_negative": {"type": "boolean"},
        },
        "required": [
            "key",
            "value",
            "confidence",
            "evidence",
            "is_negative",
        ],
    }


def _json_schema_memory_candidates(name: str, allowed: frozenset[str]) -> dict[str, object]:
    return {
        "name": name,
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "candidates": {
                    "type": "array",
                    "items": _slot_candidate_schema_properties(allowed),
                }
            },
            "required": ["candidates"],
        },
    }


_LLM_SEMANTIC_MEMORY_SCHEMA = _json_schema_memory_candidates(
    "semantic_memory_candidates", SEMANTIC_ALLOWED_KEYS
)
_LLM_SELF_SCHEMA_MEMORY_SCHEMA = _json_schema_memory_candidates(
    "self_schema_memory_candidates", SELF_SCHEMA_ALLOWED_KEYS
)

_LLM_EPISODIC_SCHEMA: dict[str, object] = {
    "name": "episodic_events",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "gist": {"type": "string"},
                        "salience_hint": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "evidence": {"type": "string"},
                    },
                    "required": ["gist", "salience_hint", "evidence"],
                },
            }
        },
        "required": ["events"],
    },
}

# LLM instructions: one system prompt per memory class (no cross-type mixing in a single call).
SEMANTIC_MEMORY_SYSTEM_PROMPT = (
    "You extract SEMANTIC memory only from one user utterance.\n"
    "Semantic memory = stable facts, habits, and preferences (names, location, schedule, food/drink, pets).\n"
    "Output JSON only. Each candidate: key, value, confidence, evidence, is_negative.\n"
    f"Allowed keys (semantic only): {', '.join(sorted(SEMANTIC_ALLOWED_KEYS))}.\n"
    "Rules:\n"
    "- Do NOT output boundary or prohibition keys here; those belong to self-schema extraction.\n"
    "- If nothing qualifies as semantic memory, return an empty candidates list.\n"
    "- confidence in [0,1]. For explicit negation, set is_negative=true.\n"
)

SELF_SCHEMA_SYSTEM_PROMPT = (
    "You extract SELF-SCHEMA / boundary memory only from one user utterance.\n"
    "Self-schema here = explicit boundaries the user states (e.g. how they must not be addressed).\n"
    "Output JSON only. Each candidate: key, value, confidence, evidence, is_negative.\n"
    f"Allowed keys (self-schema only): {', '.join(sorted(SELF_SCHEMA_ALLOWED_KEYS))}.\n"
    "Rules:\n"
    "- Do NOT output preferred_name, city, pet, rest_day, or coffee_preference here.\n"
    "- If no boundary-like constraint appears, return an empty candidates list.\n"
    "- confidence in [0,1].\n"
)

EPISODIC_MEMORY_SYSTEM_PROMPT = (
    "You extract EPISODIC memory only from one user utterance.\n"
    "Episodic memory = what happened in this turn: concrete situation, activity, or event, "
    "with time-in-conversation flavor (e.g. 'said they were tired', 'mentioned a movie').\n"
    "Output JSON only. Field events: list of {gist, salience_hint, evidence}.\n"
    "- gist: short neutral summary (one clause).\n"
    "- salience_hint: [0,1] how worth retaining for later consolidation vs noise.\n"
    "- evidence: short verbatim or paraphrase anchored in the utterance.\n"
    "- If the utterance is only a bare durable fact with no situational color, you may return an empty events list.\n"
)


@dataclass(frozen=True)
class SlotCandidate:
    key: str
    value: str
    confidence: float
    evidence: str
    turn_idx: int
    is_negative: bool = False


@dataclass(frozen=True)
class EpisodicEvent:
    """One episodic trace for a single user turn (gist + salience for consolidation)."""

    gist: str
    salience_hint: float
    evidence: str
    turn_idx: int


# Dialogue → memory subsystem routing (explicit rules; not LLM role-play).
_EPISODIC_ROUTE_HINTS = re.compile(
    r"今天|刚才|刚刚|晚上|最近|电影|困|闲聊|会议|待办|散步|午饭|消息|还行|剧情|休息|搬家|顺便|这会儿"
)


def utterance_memory_categories(text: str) -> frozenset[MemoryCategory]:
    """
    Map a user utterance to which memory subsystems should run this turn.
    Deterministic heuristics only (no LLM classification).
    """
    categories: set[MemoryCategory] = {
        MemoryCategory.SENSORY_BUFFER,
        MemoryCategory.WORKING,
    }
    if _EPISODIC_ROUTE_HINTS.search(text):
        categories.add(MemoryCategory.EPISODIC)

    boundary_here = bool(_BOUNDARY_RE.search(text)) or bool(
        re.search(r"(?:不要|别|请勿).{0,8}叫我", text)
    )
    if boundary_here:
        categories.add(MemoryCategory.SELF_SCHEMA)

    semantic_cues = (
        _PREFERRED_PATTERNS
        + (
            _CITY_RE,
            _PET_RE,
            _DAY_RE,
            _COFFEE_RE,
            _NO_COFFEE_RE,
            _NO_PET_RE,
        )
        + _CITY_MOVE_PATTERNS
    )
    if any(p.search(text) for p in semantic_cues):
        categories.add(MemoryCategory.SEMANTIC)

    return frozenset(categories)


LLMExtractFn = Callable[[str, int], list[SlotCandidate]]
LLMCallFn = Callable[[str], str]
EpisodicLLMCallFn = Callable[[str], str]


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


def extract_semantic_candidates_regex(text: str, turn_idx: int) -> list[SlotCandidate]:
    """Semantic slots only (same patterns as full regex path, minus boundary)."""
    return [
        c
        for c in _extract_candidates_regex(text, turn_idx)
        if c.key in SEMANTIC_ALLOWED_KEYS
    ]


def extract_self_schema_candidates_regex(text: str, turn_idx: int) -> list[SlotCandidate]:
    """Boundary / self-schema only."""
    return [
        c
        for c in _extract_candidates_regex(text, turn_idx)
        if c.key in SELF_SCHEMA_ALLOWED_KEYS
    ]


def _extract_episodic_regex(text: str, turn_idx: int) -> list[EpisodicEvent]:
    """Deterministic episodic trace when LLM is unavailable."""
    if not _EPISODIC_ROUTE_HINTS.search(text):
        return []
    gist = text.strip()
    if len(gist) > 96:
        gist = gist[:93] + "..."
    ev = text.strip()
    if len(ev) > 160:
        ev = ev[:157] + "..."
    return [
        EpisodicEvent(
            gist=gist,
            salience_hint=0.55,
            evidence=ev,
            turn_idx=turn_idx,
        )
    ]


def _strip_markdown_json_fences(content: str) -> str:
    if not content.startswith("```"):
        return content
    stripped = content.strip()
    if stripped.startswith("```json"):
        stripped = stripped[len("```json") :].strip()
    elif stripped.startswith("```"):
        stripped = stripped[3:].strip()
    if stripped.endswith("```"):
        stripped = stripped[:-3].strip()
    return stripped or "{}"


def _get_llm_client_and_model() -> tuple[object, str]:
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
        return client, model
    if openai_key:
        client = OpenAI(api_key=openai_key)
        model = os.getenv("INTY_MEMORY_EXTRACTOR_MODEL", "gpt-4o-mini")
        return client, model
    raise ValueError(
        "No API key found for LLM extractor; set OPENROUTER_API_KEY or OPENAI_API_KEY"
    )


def _llm_json_completion(
    client: object,
    model: str,
    system_prompt: str,
    user_prompt: str,
    json_schema: dict[str, object],
) -> str:
    from openai import BadRequestError

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    create = getattr(client, "chat").completions.create
    try:
        resp = create(
            model=model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": json_schema,
            },
            temperature=0.0,
        )
    except BadRequestError:
        # Provider rejects json_schema: fall back to json_object once.
        resp = create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
    choices = getattr(resp, "choices", None)
    if not choices:
        raise ValueError("LLM extractor returned empty choices")
    first = choices[0]
    msg = getattr(first, "message", None)
    if msg is None:
        raise ValueError("LLM extractor returned no message in first choice")
    content = getattr(msg, "content", None) or "{}"
    return _strip_markdown_json_fences(content)


def _parse_slot_candidates_json(
    content: str,
    turn_idx: int,
    allowed: frozenset[str],
) -> list[SlotCandidate]:
    data = json.loads(content)
    raw_items: list[object]
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict):
        raw_items = data.get("candidates", [])
        if not isinstance(raw_items, list):
            raise ValueError("LLM extractor response must include list field candidates")
    else:
        raise ValueError(
            "LLM extractor response must be either list or object with candidates"
        )

    out: list[SlotCandidate] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        if key not in allowed:
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
    return out


def extract_semantic_candidates_llm_default(text: str, turn_idx: int) -> list[SlotCandidate]:
    """Semantic memory only: independent LLM instruction pass."""
    client, model = _get_llm_client_and_model()
    content = _llm_json_completion(
        client,
        model,
        SEMANTIC_MEMORY_SYSTEM_PROMPT,
        f"Utterance:\n{text}",
        _LLM_SEMANTIC_MEMORY_SCHEMA,
    )
    return _parse_slot_candidates_json(content, turn_idx, SEMANTIC_ALLOWED_KEYS)


def extract_self_schema_candidates_llm_default(text: str, turn_idx: int) -> list[SlotCandidate]:
    """Self-schema / boundary memory only: independent LLM instruction pass."""
    client, model = _get_llm_client_and_model()
    content = _llm_json_completion(
        client,
        model,
        SELF_SCHEMA_SYSTEM_PROMPT,
        f"Utterance:\n{text}",
        _LLM_SELF_SCHEMA_MEMORY_SCHEMA,
    )
    return _parse_slot_candidates_json(content, turn_idx, SELF_SCHEMA_ALLOWED_KEYS)


def extract_episodic_events_llm_default(text: str, turn_idx: int) -> list[EpisodicEvent]:
    """Episodic traces only: independent LLM instruction pass."""
    client, model = _get_llm_client_and_model()
    content = _llm_json_completion(
        client,
        model,
        EPISODIC_MEMORY_SYSTEM_PROMPT,
        f"Utterance:\n{text}",
        _LLM_EPISODIC_SCHEMA,
    )
    data = json.loads(content)
    raw: list[object]
    if isinstance(data, dict):
        ev = data.get("events", [])
        if not isinstance(ev, list):
            raise ValueError("LLM episodic response must include list field events")
        raw = ev
    elif isinstance(data, list):
        raw = data
    else:
        raise ValueError("LLM episodic response must be object with events or a list")

    out: list[EpisodicEvent] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        gist = str(item.get("gist", "")).strip()
        evidence = str(item.get("evidence", "")).strip()
        if not gist:
            continue
        salience_raw = item.get("salience_hint", 0.0)
        salience = float(salience_raw)
        if salience < 0.0:
            salience = 0.0
        if salience > 1.0:
            salience = 1.0
        out.append(
            EpisodicEvent(
                gist=gist,
                salience_hint=salience,
                evidence=evidence or gist,
                turn_idx=turn_idx,
            )
        )
    return out


def _extract_candidates_llm_default(text: str, turn_idx: int) -> list[SlotCandidate]:
    """
    LLM-based slot extraction: two independent instruction passes (semantic + self-schema).
    Uses OpenRouter when OPENROUTER_API_KEY is set; otherwise OpenAI direct.
    """
    semantic = extract_semantic_candidates_llm_default(text, turn_idx)
    self_schema = extract_self_schema_candidates_llm_default(text, turn_idx)
    merged = semantic + self_schema
    return _resolve_same_turn_conflicts(merged)


def _slot_candidates_from_parsed_items(
    raw_items: list[object], turn_idx: int, allowed: frozenset[str]
) -> list[SlotCandidate]:
    out: list[SlotCandidate] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        if key not in allowed:
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
    return out


def llm_extract_memory_slots(
    text: str,
    turn_idx: int,
    llm_call: LLMCallFn,
) -> list[SlotCandidate]:
    """
    Public LLM extraction helper (single JSON payload for tests).
    Splits parsed candidates by key into semantic vs self-schema paths logically,
    then merges — same outcome as two independent LLM calls when keys are correct.
    `llm_call` must return JSON:
    {"candidates":[{"key","value","confidence","evidence","is_negative"}]} or a list.
    """
    content = llm_call(text)
    data = json.loads(content)
    raw_items: list[object]
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict):
        items = data.get("candidates", [])
        if not isinstance(items, list):
            raise ValueError("LLM extractor response must include list field candidates")
        raw_items = items
    else:
        raise ValueError("LLM extractor response must be object or list JSON")

    semantic = _slot_candidates_from_parsed_items(
        raw_items, turn_idx, SEMANTIC_ALLOWED_KEYS
    )
    self_schema = _slot_candidates_from_parsed_items(
        raw_items, turn_idx, SELF_SCHEMA_ALLOWED_KEYS
    )
    return _resolve_same_turn_conflicts(semantic + self_schema)


def llm_extract_episodic_events(
    text: str,
    turn_idx: int,
    episodic_llm_call: EpisodicLLMCallFn,
) -> list[EpisodicEvent]:
    """
    Parse episodic JSON from `episodic_llm_call` (independent of slot extraction).
    Expected: {"events":[{"gist","salience_hint","evidence"}]} or a list of objects.
    """
    content = episodic_llm_call(text)
    data = json.loads(content)
    raw: list[object]
    if isinstance(data, dict):
        ev = data.get("events", [])
        if not isinstance(ev, list):
            raise ValueError("Episodic LLM response must include list field events")
        raw = ev
    elif isinstance(data, list):
        raw = data
    else:
        raise ValueError("Episodic LLM response must be object with events or list")

    out: list[EpisodicEvent] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        gist = str(item.get("gist", "")).strip()
        evidence = str(item.get("evidence", "")).strip()
        if not gist:
            continue
        salience_raw = item.get("salience_hint", 0.0)
        salience = float(salience_raw)
        if salience < 0.0:
            salience = 0.0
        if salience > 1.0:
            salience = 1.0
        out.append(
            EpisodicEvent(
                gist=gist,
                salience_hint=salience,
                evidence=evidence or gist,
                turn_idx=turn_idx,
            )
        )
    return out


def extract_candidates_llm(
    text: str,
    turn_idx: int,
    *,
    llm_call: LLMCallFn | None = None,
) -> list[SlotCandidate]:
    """
    Public LLM candidate extractor.
    - With `llm_call`: use provided callable (great for tests/mocks).
    - Without `llm_call`: use default OpenAI/OpenRouter backend.
    """
    if llm_call is None:
        return _extract_candidates_llm_default(text, turn_idx)
    try:
        return llm_extract_memory_slots(text, turn_idx, llm_call)
    except (json.JSONDecodeError, ValueError, TypeError):
        return _extract_candidates_regex(text, turn_idx)


def extract_episodic_events_llm(
    text: str,
    turn_idx: int,
    *,
    episodic_llm_call: EpisodicLLMCallFn | None = None,
) -> list[EpisodicEvent]:
    """
    Episodic extraction: independent LLM instructions, or regex fallback.
    """
    if episodic_llm_call is None:
        try:
            return extract_episodic_events_llm_default(text, turn_idx)
        except (ImportError, ValueError, json.JSONDecodeError):
            return _extract_episodic_regex(text, turn_idx)
    try:
        return llm_extract_episodic_events(text, turn_idx, episodic_llm_call)
    except (json.JSONDecodeError, ValueError, TypeError):
        return _extract_episodic_regex(text, turn_idx)


def extract_by_memory_category(
    text: str,
    turn_idx: int,
    category: MemoryCategory,
    *,
    mode: str = "auto",
    llm_extract_fn: LLMExtractFn | None = None,
    episodic_llm_call: EpisodicLLMCallFn | None = None,
) -> list[SlotCandidate] | list[EpisodicEvent]:
    """
    Run extraction for exactly one memory category (independent backends).
    Returns SlotCandidate list for slot layers; EpisodicEvent list for episodic.
    """
    if mode not in {"llm", "regex", "auto"}:
        raise ValueError(f"unsupported extractor mode: {mode}")

    if category in (MemoryCategory.SENSORY_BUFFER, MemoryCategory.WORKING):
        return []

    if category == MemoryCategory.EPISODIC:
        if mode == "regex":
            return _extract_episodic_regex(text, turn_idx)
        return extract_episodic_events_llm(
            text, turn_idx, episodic_llm_call=episodic_llm_call
        )

    if category == MemoryCategory.SEMANTIC:
        if mode == "regex":
            return extract_semantic_candidates_regex(text, turn_idx)
        llm_fn = llm_extract_fn or extract_semantic_candidates_llm_default
        try:
            slots = llm_fn(text, turn_idx)
            return [c for c in slots if c.key in SEMANTIC_ALLOWED_KEYS]
        except (ImportError, ValueError, json.JSONDecodeError):
            return extract_semantic_candidates_regex(text, turn_idx)

    if category == MemoryCategory.SELF_SCHEMA:
        if mode == "regex":
            return extract_self_schema_candidates_regex(text, turn_idx)
        llm_fn = llm_extract_fn or extract_self_schema_candidates_llm_default
        try:
            slots = llm_fn(text, turn_idx)
            return [c for c in slots if c.key in SELF_SCHEMA_ALLOWED_KEYS]
        except (ImportError, ValueError, json.JSONDecodeError):
            return extract_self_schema_candidates_regex(text, turn_idx)

    raise ValueError(f"unsupported memory category: {category}")


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


def merge_slot_candidates(candidates: list[SlotCandidate]) -> list[SlotCandidate]:
    """Merge lists from independent extractors; apply same-turn boundary/name rules."""
    return _resolve_same_turn_conflicts(candidates)


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
