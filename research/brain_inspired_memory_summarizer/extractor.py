from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)

ALLOWED_KEYS = {
    "preferred_name",
    "city",
    "pet",
    "rest_day",
    "coffee_preference",
    "boundary",
}

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

_LLM_ROUTE_SCHEMA: dict[str, object] = {
    "name": "memory_route",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "active_subsystems": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["semantic", "episodic", "self_schema"],
                },
            }
        },
        "required": ["active_subsystems"],
    },
}

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
    "- If the utterance is only a bare durable fact with no situational color, return an empty events list.\n"
)

ROUTE_MEMORY_SYSTEM_PROMPT = (
    "You route one user utterance to memory subsystems that should run encoding this turn.\n"
    "Output JSON only: active_subsystems, a subset of: semantic, episodic, self_schema.\n"
    "- semantic: durable facts, preferences, stable user info.\n"
    "- self_schema: explicit boundaries (e.g. how they must not be called).\n"
    "- episodic: situational / what is happening now (activities, mood, immediate context).\n"
    "A single utterance may need multiple subsystems.\n"
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
    gist: str
    salience_hint: float
    evidence: str
    turn_idx: int


LLMExtractFn = Callable[[str, int], list[SlotCandidate]]
LLMCallFn = Callable[[str], str]
EpisodicLLMCallFn = Callable[[str], str]


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
    from openai import OpenAI

    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openrouter_key:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
        model = os.getenv("INTY_MEMORY_EXTRACTOR_MODEL", "openai/gpt-4o-mini")
        logger.info("LLM backend=OpenRouter model=%s", model)
        return client, model
    if openai_key:
        client = OpenAI(api_key=openai_key)
        model = os.getenv("INTY_MEMORY_EXTRACTOR_MODEL", "gpt-4o-mini")
        logger.info("LLM backend=OpenAI model=%s", model)
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
    *,
    operation: str = "json_schema_completion",
) -> str:
    from openai import BadRequestError

    logger.info("LLM %s start model=%s", operation, model)
    logger.debug(
        "LLM %s user_preview=%r",
        operation,
        user_prompt if len(user_prompt) <= 200 else user_prompt[:200] + "...",
    )
    t0 = time.perf_counter()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    create = getattr(client, "chat").completions.create
    used_fallback = False
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
        used_fallback = True
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
    out = _strip_markdown_json_fences(content)
    elapsed = time.perf_counter() - t0
    logger.info(
        "LLM %s done model=%s response_chars=%d elapsed_s=%.2f fallback_json_object=%s",
        operation,
        model,
        len(out),
        elapsed,
        used_fallback,
    )
    return out


def _llm_json_object_completion(
    client: object,
    model: str,
    system_prompt: str,
    user_prompt: str,
    *,
    operation: str = "json_object_completion",
) -> str:
    """Single completion with response_format=json_object (broad provider support for live runs)."""
    logger.info("LLM %s start model=%s", operation, model)
    logger.debug(
        "LLM %s user_preview=%r",
        operation,
        user_prompt if len(user_prompt) <= 200 else user_prompt[:200] + "...",
    )
    t0 = time.perf_counter()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    create = getattr(client, "chat").completions.create
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
    out = _strip_markdown_json_fences(content)
    elapsed = time.perf_counter() - t0
    logger.info(
        "LLM %s done model=%s response_chars=%d elapsed_s=%.2f",
        operation,
        model,
        len(out),
        elapsed,
    )
    return out


def parse_route_memory_json(content: str) -> frozenset[MemoryCategory]:
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("route response must be a JSON object")
    raw = data.get("active_subsystems", [])
    if not isinstance(raw, list):
        raise ValueError("active_subsystems must be a list")
    out: set[MemoryCategory] = {
        MemoryCategory.SENSORY_BUFFER,
        MemoryCategory.WORKING,
    }
    for x in raw:
        if x == "semantic":
            out.add(MemoryCategory.SEMANTIC)
        elif x == "episodic":
            out.add(MemoryCategory.EPISODIC)
        elif x == "self_schema":
            out.add(MemoryCategory.SELF_SCHEMA)
    return frozenset(out)


def route_memory_categories_llm_default(text: str) -> frozenset[MemoryCategory]:
    client, model = _get_llm_client_and_model()
    content = _llm_json_completion(
        client,
        model,
        ROUTE_MEMORY_SYSTEM_PROMPT,
        f"Utterance:\n{text}",
        _LLM_ROUTE_SCHEMA,
        operation="route",
    )
    return parse_route_memory_json(content)


def route_memory_categories_llm(
    text: str,
    *,
    route_llm_call: LLMCallFn | None = None,
) -> frozenset[MemoryCategory]:
    if route_llm_call is None:
        return route_memory_categories_llm_default(text)
    return parse_route_memory_json(route_llm_call(text))


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
    client, model = _get_llm_client_and_model()
    content = _llm_json_completion(
        client,
        model,
        SEMANTIC_MEMORY_SYSTEM_PROMPT,
        f"Utterance:\n{text}",
        _LLM_SEMANTIC_MEMORY_SCHEMA,
        operation="semantic_slots",
    )
    return _parse_slot_candidates_json(content, turn_idx, SEMANTIC_ALLOWED_KEYS)


def extract_self_schema_candidates_llm_default(text: str, turn_idx: int) -> list[SlotCandidate]:
    client, model = _get_llm_client_and_model()
    content = _llm_json_completion(
        client,
        model,
        SELF_SCHEMA_SYSTEM_PROMPT,
        f"Utterance:\n{text}",
        _LLM_SELF_SCHEMA_MEMORY_SCHEMA,
        operation="self_schema_slots",
    )
    return _parse_slot_candidates_json(content, turn_idx, SELF_SCHEMA_ALLOWED_KEYS)


def extract_episodic_events_llm_default(text: str, turn_idx: int) -> list[EpisodicEvent]:
    client, model = _get_llm_client_and_model()
    content = _llm_json_completion(
        client,
        model,
        EPISODIC_MEMORY_SYSTEM_PROMPT,
        f"Utterance:\n{text}",
        _LLM_EPISODIC_SCHEMA,
        operation="episodic_events",
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
    semantic = extract_semantic_candidates_llm_default(text, turn_idx)
    self_schema = extract_self_schema_candidates_llm_default(text, turn_idx)
    return _resolve_same_turn_conflicts(semantic + self_schema)


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
    if llm_call is None:
        return _extract_candidates_llm_default(text, turn_idx)
    return llm_extract_memory_slots(text, turn_idx, llm_call)


def extract_episodic_events_llm(
    text: str,
    turn_idx: int,
    *,
    episodic_llm_call: EpisodicLLMCallFn | None = None,
) -> list[EpisodicEvent]:
    if episodic_llm_call is None:
        return extract_episodic_events_llm_default(text, turn_idx)
    return llm_extract_episodic_events(text, turn_idx, episodic_llm_call)


def extract_by_memory_category(
    text: str,
    turn_idx: int,
    category: MemoryCategory,
    *,
    llm_extract_fn: LLMExtractFn | None = None,
    episodic_llm_call: EpisodicLLMCallFn | None = None,
) -> list[SlotCandidate] | list[EpisodicEvent]:
    if category in (MemoryCategory.SENSORY_BUFFER, MemoryCategory.WORKING):
        return []

    if category == MemoryCategory.EPISODIC:
        return extract_episodic_events_llm(
            text, turn_idx, episodic_llm_call=episodic_llm_call
        )

    if category == MemoryCategory.SEMANTIC:
        llm_fn = llm_extract_fn or extract_semantic_candidates_llm_default
        slots = llm_fn(text, turn_idx)
        return [c for c in slots if c.key in SEMANTIC_ALLOWED_KEYS]

    if category == MemoryCategory.SELF_SCHEMA:
        llm_fn = llm_extract_fn or extract_self_schema_candidates_llm_default
        slots = llm_fn(text, turn_idx)
        return [c for c in slots if c.key in SELF_SCHEMA_ALLOWED_KEYS]

    raise ValueError(f"unsupported memory category: {category}")


# Boundary value shape from LLM is "不要叫我{name}"; used only for conflict checks, not extraction.
_BOUNDARY_VALUE_RE = re.compile(r"不要叫我(.+)$")


def _resolve_same_turn_conflicts(candidates: list[SlotCandidate]) -> list[SlotCandidate]:
    blocked_names: set[str] = set()
    for c in candidates:
        if c.key != "boundary":
            continue
        m = _BOUNDARY_VALUE_RE.search(c.value.strip())
        if m:
            blocked_names.add(m.group(1).strip())
    if not blocked_names:
        return candidates
    out: list[SlotCandidate] = []
    for c in candidates:
        if c.key == "preferred_name" and c.value in blocked_names:
            continue
        out.append(c)
    return out


def merge_slot_candidates(candidates: list[SlotCandidate]) -> list[SlotCandidate]:
    return _resolve_same_turn_conflicts(candidates)


def extract_candidates(
    text: str,
    turn_idx: int,
    *,
    llm_extract_fn: LLMExtractFn | None = None,
) -> list[SlotCandidate]:
    llm_fn = llm_extract_fn or _extract_candidates_llm_default
    return llm_fn(text, turn_idx)


def build_live_slot_extract_fn() -> LLMExtractFn:
    """
    Real API: two json_object completions per utterance (semantic + self-schema), merged.
    Requires OPENROUTER_API_KEY or OPENAI_API_KEY and `openai` package.
    """

    def fn(text: str, turn_idx: int) -> list[SlotCandidate]:
        client, model = _get_llm_client_and_model()
        sem_user = (
            f"Utterance:\n{text}\n\n"
            "Return JSON only. Either {\"candidates\":[...]} or a JSON array. "
            "Each item: key, value, confidence, evidence, is_negative. "
            f"Allowed keys: {', '.join(sorted(SEMANTIC_ALLOWED_KEYS))}. "
            "Use empty candidates or [] if nothing applies."
        )
        sem_raw = _llm_json_object_completion(
            client,
            model,
            SEMANTIC_MEMORY_SYSTEM_PROMPT,
            sem_user,
            operation="live_semantic_slots",
        )
        semantic = _parse_slot_candidates_json(sem_raw, turn_idx, SEMANTIC_ALLOWED_KEYS)
        ss_user = (
            f"Utterance:\n{text}\n\n"
            "Return JSON only. Either {\"candidates\":[...]} or a JSON array. "
            "Each item: key, value, confidence, evidence, is_negative. "
            f"Allowed keys: {', '.join(sorted(SELF_SCHEMA_ALLOWED_KEYS))}. "
            "Use empty candidates or [] if nothing applies."
        )
        ss_raw = _llm_json_object_completion(
            client,
            model,
            SELF_SCHEMA_SYSTEM_PROMPT,
            ss_user,
            operation="live_self_schema_slots",
        )
        self_schema = _parse_slot_candidates_json(
            ss_raw, turn_idx, SELF_SCHEMA_ALLOWED_KEYS
        )
        return merge_slot_candidates(semantic + self_schema)

    return fn


def build_live_route_llm_call() -> LLMCallFn:
    """Real API: json_object route JSON for one utterance."""

    def route(text: str) -> str:
        client, model = _get_llm_client_and_model()
        user = (
            f"Utterance:\n{text}\n\n"
            'Return JSON only: {"active_subsystems": ["semantic", "episodic", "self_schema", ...]}. '
            "Include every subsystem that should encode this turn. Use [] if none (besides implicit working memory)."
        )
        return _llm_json_object_completion(
            client, model, ROUTE_MEMORY_SYSTEM_PROMPT, user, operation="live_route"
        )

    return route


def build_live_episodic_llm_call() -> EpisodicLLMCallFn:
    """Real API: json_object episodic events for one utterance."""

    def episodic(text: str) -> str:
        client, model = _get_llm_client_and_model()
        user = (
            f"Utterance:\n{text}\n\n"
            'Return JSON only: {"events":[{"gist","salience_hint","evidence"}, ...]}. '
            "Use {\"events\":[]} if no episodic content."
        )
        return _llm_json_object_completion(
            client,
            model,
            EPISODIC_MEMORY_SYSTEM_PROMPT,
            user,
            operation="live_episodic",
        )

    return episodic


def extract_memory_facts(
    text: str,
    *,
    llm_extract_fn: LLMExtractFn | None = None,
) -> dict[str, str]:
    facts: dict[str, str] = {}
    for c in extract_candidates(text, turn_idx=0, llm_extract_fn=llm_extract_fn):
        facts[c.key] = c.value
    return facts


def is_more_reliable_name_candidate(new: SlotCandidate, old: SlotCandidate) -> bool:
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
    if not boundary_text:
        return False
    m = _BOUNDARY_VALUE_RE.search(boundary_text.strip())
    if not m:
        return False
    blocked = m.group(1).strip()
    return preferred_name == blocked
