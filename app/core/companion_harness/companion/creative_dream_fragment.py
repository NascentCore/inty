"""巩固（DREAM）成功后可选的一次性「创造性片段」：短补全写入私有 JSONL，不进入主 transcript。"""

from __future__ import annotations

import random
import uuid
from datetime import date

from loguru import logger

from app.core.companion_harness.companion.agent_circadian import (
    local_datetime_from_user_time_context,
)
from app.core.companion_harness.companion.llm_client import CompanionLLMClient
from app.core.companion_harness.companion.utc import utc_iso_ts
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.models import load_transcript_from_store
from app.core.companion_harness.companion.sleep_state import (
    record_creative_fragment_written_failed_rollback,
    try_reserve_creative_fragment_slot,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.config import FeaturesConfig

_CREATIVE_DREAM_FRAGMENTS_REL = ".companion_creative_dream_fragments.jsonl"

_CREATIVE_SYSTEM = (
    "You write ONE short private dream fragment (2-5 sentences). "
    "It is inspired loosely by the user's daytime chat snippets below; "
    "do not quote them; surreal metaphor welcome; no tools; no preamble."
)


def _local_date_key(implicit: ImplicitSignalBundle | None) -> str:
    uctx = implicit.client_time.model_dump(exclude_none=True) if implicit and implicit.client_time else None
    dt = local_datetime_from_user_time_context(uctx)
    if dt is not None:
        return dt.date().isoformat()
    return date.today().isoformat()


def _recent_main_transcript_excerpt(store: MemoryStore, *, max_lines: int = 14) -> str:
    rows = load_transcript_from_store(store, "transcript.jsonl")
    lines: list[str] = []
    for m in rows[-max_lines:]:
        role = getattr(m, "role", "") or ""
        if role not in ("user", "assistant"):
            continue
        body = (getattr(m, "content", None) or "").strip()
        if not body:
            continue
        if getattr(m, "heartbeat", False) is True:
            continue
        inner = getattr(m, "inner_tick", False)
        if inner is True:
            continue
        short = body.replace("\n", " ")
        if len(short) > 220:
            short = short[:217] + "..."
        lines.append(f"{role}: {short}")
    return "\n".join(lines)


def maybe_append_creative_dream_fragment_after_consolidation(
    *,
    store: MemoryStore,
    llm_client: CompanionLLMClient,
    feats: FeaturesConfig,
    implicit: ImplicitSignalBundle | None,
) -> None:
    """概率门控 + 本地日限额；失败或空输出会回滚当日预留槽。"""
    if feats.companion_creative_dream_probability <= 0.0:
        return
    if random.random() >= float(feats.companion_creative_dream_probability):
        return
    local_key = _local_date_key(implicit)
    max_per = int(feats.companion_creative_dream_max_fragments_per_local_day)
    if not try_reserve_creative_fragment_slot(store, local_date=local_key, max_per_day=max_per):
        return
    excerpt = _recent_main_transcript_excerpt(store)
    max_chars = int(feats.companion_creative_dream_max_fragment_chars)
    user_block = excerpt if excerpt else "(no recent main transcript snippets)"
    messages = [
        {"role": "system", "content": _CREATIVE_SYSTEM},
        {
            "role": "user",
            "content": f"Daytime snippets:\n{user_block}\n\nWrite the fragment now.",
        },
    ]
    try:
        text = llm_client.complete_text(messages, model_role="memory")
    except Exception as exc:
        record_creative_fragment_written_failed_rollback(store, local_date=local_key)
        logger.warning("creative_dream complete_text failed: {}", exc)
        return
    frag = (text or "").strip()
    if not frag:
        record_creative_fragment_written_failed_rollback(store, local_date=local_key)
        return
    if len(frag) > max_chars:
        frag = frag[: max_chars - 1] + "…"
    row = {
        "role": "creative_dream",
        "ts": utc_iso_ts(),
        "uuid": str(uuid.uuid4()),
        "fragment": frag,
        "local_date": local_key,
        "source": "after_dream_consolidation",
    }
    store.append_jsonl_record(_CREATIVE_DREAM_FRAGMENTS_REL, row)
    logger.info(
        "creative_dream fragment stored chars={} local_date={}",
        len(frag),
        local_key,
    )
