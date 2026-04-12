"""Transcript context compaction (deterministic episodic + semantic snapshot).

Ported from experimental/agentic_ai_companion/memory_compaction.py for production
companion kernel: when the OpenAI-style message list for a turn exceeds a character
budget, older dialogue is folded into a single structured system snapshot while
keeping recent user/assistant turns verbatim.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .memory_store import MemoryStore
from .models import ChatMessage

COMPACTION_SYSTEM_TAG = "[MEMORY_COMPACTION_SNAPSHOT]"
_MAX_TEXT_PREVIEW = 220

_EMOTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "stressed": ("stressed", "stress", "anxious", "overwhelmed"),
    "sad": ("sad", "down", "depressed", "lonely"),
    "excited": ("excited", "thrilled", "can't wait", "aroused"),
    "angry": ("angry", "mad", "furious", "annoyed"),
    "calm": ("calm", "relaxed", "peaceful"),
}


class CompactionConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_context_chars: int = Field(gt=200)
    keep_recent_messages: int = Field(gt=2)
    max_messages_per_episode: int = Field(gt=2)
    max_episodic_entries: int = Field(gt=2)
    max_semantic_entries: int = Field(gt=2)
    summary_max_chars: int = Field(gt=200)
    retrieval_episode_count: int = Field(gt=1)
    retrieval_semantic_count: int = Field(gt=1)
    retrieval_open_loop_count: int = Field(gt=1)


class MemoryEpisode(BaseModel):
    model_config = ConfigDict(frozen=True)

    episode_id: str
    turn_start: int
    turn_end: int
    summary: str
    salient_facts: list[str]
    emotional_tags: list[str]
    open_loops: list[str]
    importance: float = Field(ge=0.0, le=1.0)
    last_access_turn: int = Field(ge=0)


class SemanticMemoryItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    fact: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_episode_ids: list[str]
    updated_turn: int = Field(ge=0)


class CompactionState(BaseModel):
    model_config = ConfigDict(frozen=True)

    running_summary: str
    episodic_memory: list[MemoryEpisode]
    semantic_memory: list[SemanticMemoryItem]
    compaction_count: int = Field(ge=0)

    @classmethod
    def empty(cls) -> CompactionState:
        return cls(
            running_summary="",
            episodic_memory=[],
            semantic_memory=[],
            compaction_count=0,
        )


class CompactionOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    messages: list[dict[str, Any]]
    state: CompactionState
    did_compact: bool
    reason: str
    approx_chars_before: int = Field(ge=0)
    approx_chars_after: int = Field(ge=0)


class ConversationCompactor:
    def __init__(
        self, config: CompactionConfig, *, initial_state: CompactionState | None = None
    ) -> None:
        self._config = config
        self._state = (
            initial_state if initial_state is not None else CompactionState.empty()
        )

    @property
    def state(self) -> CompactionState:
        return self._state

    def maybe_compact(
        self, *, messages: list[dict[str, Any]], turn: int
    ) -> CompactionOutcome:
        before_chars = estimate_messages_chars(messages)
        if before_chars <= self._config.max_context_chars:
            return CompactionOutcome(
                messages=messages,
                state=self._state,
                did_compact=False,
                reason="under_budget",
                approx_chars_before=before_chars,
                approx_chars_after=before_chars,
            )

        system_messages = [
            m
            for m in messages
            if m.get("role") == "system" and not _is_compaction_message(m)
        ]
        dialogue_messages = [m for m in messages if m.get("role") != "system"]
        if len(dialogue_messages) <= self._config.keep_recent_messages:
            return CompactionOutcome(
                messages=messages,
                state=self._state,
                did_compact=False,
                reason="not_enough_dialogue",
                approx_chars_before=before_chars,
                approx_chars_after=before_chars,
            )

        old_dialogue = dialogue_messages[: -self._config.keep_recent_messages]
        recent_dialogue = dialogue_messages[-self._config.keep_recent_messages :]

        next_state = self._absorb_old_dialogue(old_dialogue=old_dialogue, turn=turn)
        memory_msg = {
            "role": "system",
            "content": self._build_compaction_system_prompt(
                state=next_state, turn=turn
            ),
        }
        compacted_messages = [*system_messages, memory_msg, *recent_dialogue]
        after_chars = estimate_messages_chars(compacted_messages)
        if after_chars >= before_chars:
            minimal_memory_msg = {
                "role": "system",
                "content": self._build_minimal_compaction_system_prompt(
                    state=next_state, turn=turn
                ),
            }
            compacted_messages = [
                *system_messages,
                minimal_memory_msg,
                *recent_dialogue,
            ]
            after_chars = estimate_messages_chars(compacted_messages)
        if after_chars >= before_chars:
            compacted_messages = [*system_messages, *recent_dialogue]
            after_chars = estimate_messages_chars(compacted_messages)
        self._state = next_state

        return CompactionOutcome(
            messages=compacted_messages,
            state=next_state,
            did_compact=True,
            reason="over_budget_compacted",
            approx_chars_before=before_chars,
            approx_chars_after=after_chars,
        )

    def _absorb_old_dialogue(
        self, *, old_dialogue: list[dict[str, Any]], turn: int
    ) -> CompactionState:
        chunks = _chunk_messages(
            messages=old_dialogue, max_messages=self._config.max_messages_per_episode
        )
        new_episodes: list[MemoryEpisode] = [
            _build_episode(chunk=chunk, turn=turn) for chunk in chunks if chunk
        ]
        merged_episodes = [*self._state.episodic_memory, *new_episodes]
        merged_episodes = _trim_episodes(
            episodes=merged_episodes, max_entries=self._config.max_episodic_entries
        )

        merged_semantic = _merge_semantic_memory(
            existing=self._state.semantic_memory,
            new_episodes=new_episodes,
            turn=turn,
            max_entries=self._config.max_semantic_entries,
        )

        next_summary = _merge_running_summary(
            previous_summary=self._state.running_summary,
            new_episodes=new_episodes,
            max_chars=self._config.summary_max_chars,
        )

        return CompactionState(
            running_summary=next_summary,
            episodic_memory=merged_episodes,
            semantic_memory=merged_semantic,
            compaction_count=self._state.compaction_count + 1,
        )

    def _build_compaction_system_prompt(
        self, *, state: CompactionState, turn: int
    ) -> str:
        ranked_episodes = _rank_episodes_for_retrieval(
            episodes=state.episodic_memory, turn=turn
        )[: self._config.retrieval_episode_count]
        ranked_semantic = sorted(
            state.semantic_memory, key=lambda item: item.confidence, reverse=True
        )[: self._config.retrieval_semantic_count]
        open_loops = _collect_open_loops(
            episodes=ranked_episodes, max_items=self._config.retrieval_open_loop_count
        )

        episode_lines = [
            (
                f"- [turn {ep.turn_start}-{ep.turn_end}] {ep.summary} "
                f"(importance={ep.importance:.2f}, tags={','.join(ep.emotional_tags) or 'none'})"
            )
            for ep in ranked_episodes
        ]
        semantic_lines = [
            f"- {item.fact} (confidence={item.confidence:.2f})"
            for item in ranked_semantic
        ]
        open_loop_lines = [f"- {item}" for item in open_loops]

        return "\n".join(
            [
                COMPACTION_SYSTEM_TAG,
                f"turn={turn}",
                "Long-term memory snapshot from compressed older dialogue. Prefer the "
                "user's latest message when facts conflict.",
                "## Running Summary",
                state.running_summary or "- (none)",
                "## Semantic Memory",
                "\n".join(semantic_lines) if semantic_lines else "- (none)",
                "## Episodic Memory",
                "\n".join(episode_lines) if episode_lines else "- (none)",
                "## Open Loops",
                "\n".join(open_loop_lines) if open_loop_lines else "- (none)",
            ]
        )

    def _build_minimal_compaction_system_prompt(
        self, *, state: CompactionState, turn: int
    ) -> str:
        top_semantic = sorted(
            state.semantic_memory, key=lambda item: item.confidence, reverse=True
        )[:3]
        semantic_lines = [f"- {item.fact[:80]}" for item in top_semantic]
        running_summary = state.running_summary[-280:]
        return "\n".join(
            [
                COMPACTION_SYSTEM_TAG,
                f"turn={turn}",
                "Older dialogue was compressed; prefer the user's latest input.",
                "Summary:",
                running_summary or "- (none)",
                "Facts:",
                "\n".join(semantic_lines) if semantic_lines else "- (none)",
            ]
        )


def estimate_messages_chars(messages: list[dict[str, Any]]) -> int:
    return sum(len(str(m.get("content") or "")) for m in messages)


def load_compaction_state_from_store(
    store: MemoryStore, relative_path: str
) -> CompactionState | None:
    raw = store.read_document_if_exists(relative_path)
    if raw is None or not raw.strip():
        return None
    return CompactionState.model_validate_json(raw)


def save_compaction_state_to_store(
    store: MemoryStore, relative_path: str, state: CompactionState
) -> None:
    body = state.model_dump_json(indent=2, exclude_none=True) + "\n"
    store.write_document(relative_path, body)


def transcript_rows_to_openai_dialogue(rows: list[ChatMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in rows:
        if m.role not in ("user", "assistant"):
            continue
        out.append({"role": m.role, "content": m.content})
    return out


def _is_compaction_message(message: dict[str, Any]) -> bool:
    content = str(message.get("content") or "")
    return content.startswith(COMPACTION_SYSTEM_TAG)


def _chunk_messages(
    *, messages: list[dict[str, Any]], max_messages: int
) -> list[list[dict[str, Any]]]:
    return [
        messages[i : i + max_messages] for i in range(0, len(messages), max_messages)
    ]


def _build_episode(*, chunk: list[dict[str, Any]], turn: int) -> MemoryEpisode:
    user_texts = _collect_role_texts(chunk=chunk, role="user")
    assistant_texts = _collect_role_texts(chunk=chunk, role="assistant")
    start_turn = _guess_turn_from_chunk(chunk=chunk, fallback=turn)
    end_turn = turn

    summary = _build_episode_summary(
        user_texts=user_texts, assistant_texts=assistant_texts
    )
    salient_facts = _extract_salient_facts(user_texts=user_texts)
    emotional_tags = _extract_emotional_tags(texts=user_texts + assistant_texts)
    open_loops = _extract_open_loops(user_texts=user_texts)
    importance = _score_importance(
        summary=summary,
        salient_facts=salient_facts,
        emotional_tags=emotional_tags,
        open_loops=open_loops,
    )

    episode_seed = "|".join([summary, str(start_turn), str(end_turn)])
    episode_id = hashlib.sha1(episode_seed.encode("utf-8")).hexdigest()[:12]
    return MemoryEpisode(
        episode_id=episode_id,
        turn_start=start_turn,
        turn_end=end_turn,
        summary=summary,
        salient_facts=salient_facts,
        emotional_tags=emotional_tags,
        open_loops=open_loops,
        importance=importance,
        last_access_turn=turn,
    )


def _collect_role_texts(*, chunk: list[dict[str, Any]], role: str) -> list[str]:
    texts: list[str] = []
    for message in chunk:
        if message.get("role") != role:
            continue
        text = str(message.get("content") or "").strip()
        if text:
            texts.append(text)
    return texts


def _guess_turn_from_chunk(*, chunk: list[dict[str, Any]], fallback: int) -> int:
    user_messages = [m for m in chunk if m.get("role") == "user"]
    if not user_messages:
        return max(1, fallback - 1)
    return max(1, fallback - len(user_messages))


def _build_episode_summary(*, user_texts: list[str], assistant_texts: list[str]) -> str:
    user_preview = " ".join(user_texts)[:_MAX_TEXT_PREVIEW].strip()
    assistant_preview = " ".join(assistant_texts)[:_MAX_TEXT_PREVIEW].strip()
    if user_preview and assistant_preview:
        return f"User: {user_preview} | Assistant: {assistant_preview}"
    if user_preview:
        return f"User: {user_preview}"
    if assistant_preview:
        return f"Assistant: {assistant_preview}"
    return "empty segment"


def _extract_salient_facts(*, user_texts: list[str]) -> list[str]:
    patterns = (
        r"\b(?:i am|i'm|my name is|i work as|i live in|i like|i love|i hate|i prefer|i need|i want)\b[^.?!\n]*",
    )
    found: list[str] = []
    for text in user_texts:
        lowered = text.lower()
        for pattern in patterns:
            for match in re.finditer(pattern, lowered):
                fact = match.group(0).strip(" ,.;:!?")
                if len(fact) >= 8:
                    found.append(fact)
        for sentence in _split_sentences(text):
            normalized = sentence.lower()
            if "remember" in normalized and len(sentence) >= 8:
                found.append(sentence.strip())
    return _dedupe_keep_order(found)


def _extract_emotional_tags(*, texts: list[str]) -> list[str]:
    joined = " ".join(texts).lower()
    tags: list[str] = []
    for tag, keywords in _EMOTION_KEYWORDS.items():
        if any(keyword in joined for keyword in keywords):
            tags.append(tag)
    return tags


def _extract_open_loops(*, user_texts: list[str]) -> list[str]:
    loops: list[str] = []
    for text in user_texts:
        for sentence in _split_sentences(text):
            s = sentence.strip()
            lowered = s.lower()
            if not s:
                continue
            if s.endswith("?"):
                loops.append(s)
                continue
            if (
                "please" in lowered
                or lowered.startswith("can you")
                or lowered.startswith("could you")
            ):
                loops.append(s)
    return _dedupe_keep_order(loops)


def _split_sentences(text: str) -> list[str]:
    return [
        segment.strip()
        for segment in re.split(r"(?<=[.!?])\s+", text)
        if segment.strip()
    ]


def _score_importance(
    *,
    summary: str,
    salient_facts: list[str],
    emotional_tags: list[str],
    open_loops: list[str],
) -> float:
    score = 0.3
    score += min(len(salient_facts), 3) * 0.15
    score += min(len(emotional_tags), 2) * 0.1
    score += min(len(open_loops), 2) * 0.1
    if "remember" in summary.lower():
        score += 0.1
    return min(score, 1.0)


def _trim_episodes(
    *, episodes: list[MemoryEpisode], max_entries: int
) -> list[MemoryEpisode]:
    ranked = sorted(
        episodes,
        key=lambda item: (item.importance, item.last_access_turn, item.turn_end),
        reverse=True,
    )
    return ranked[:max_entries]


def _merge_semantic_memory(
    *,
    existing: list[SemanticMemoryItem],
    new_episodes: list[MemoryEpisode],
    turn: int,
    max_entries: int,
) -> list[SemanticMemoryItem]:
    by_key: dict[str, SemanticMemoryItem] = {item.key: item for item in existing}
    for episode in new_episodes:
        for fact in episode.salient_facts:
            key = _semantic_key(fact)
            current = by_key.get(key)
            if current is None:
                by_key[key] = SemanticMemoryItem(
                    key=key,
                    fact=fact,
                    confidence=min(0.55 + episode.importance * 0.35, 0.98),
                    source_episode_ids=[episode.episode_id],
                    updated_turn=turn,
                )
                continue
            merged_sources = _dedupe_keep_order(
                [*current.source_episode_ids, episode.episode_id]
            )
            by_key[key] = SemanticMemoryItem(
                key=key,
                fact=fact if len(fact) >= len(current.fact) else current.fact,
                confidence=min(current.confidence + 0.08, 0.99),
                source_episode_ids=merged_sources,
                updated_turn=turn,
            )
    merged = sorted(
        by_key.values(),
        key=lambda item: (item.confidence, item.updated_turn),
        reverse=True,
    )
    return merged[:max_entries]


def _semantic_key(fact: str) -> str:
    words = re.sub(r"[^a-zA-Z0-9\s]+", " ", fact.lower()).split()
    compact = " ".join(words[:10])
    return compact or hashlib.sha1(fact.encode("utf-8")).hexdigest()[:12]


def _merge_running_summary(
    *, previous_summary: str, new_episodes: list[MemoryEpisode], max_chars: int
) -> str:
    if not new_episodes:
        return previous_summary[:max_chars]
    append_part = " | ".join(episode.summary for episode in new_episodes[:3])
    merged = f"{previous_summary} | {append_part}".strip(" |")
    if len(merged) <= max_chars:
        return merged
    return merged[-max_chars:]


def _rank_episodes_for_retrieval(
    *, episodes: list[MemoryEpisode], turn: int
) -> list[MemoryEpisode]:
    def rank_score(item: MemoryEpisode) -> float:
        recency = 1.0 / (1.0 + max(turn - item.turn_end, 0))
        return item.importance * 0.7 + recency * 0.3

    return sorted(episodes, key=rank_score, reverse=True)


def _collect_open_loops(*, episodes: list[MemoryEpisode], max_items: int) -> list[str]:
    loops: list[str] = []
    for episode in episodes:
        loops.extend(episode.open_loops)
    return _dedupe_keep_order(loops)[:max_items]


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out
