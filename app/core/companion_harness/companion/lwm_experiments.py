"""LWM-inspired AUTONOMY experiments (experience loop, consistency, mental simulation).

Generated entirely by Cursor Cloud Agent for Qwen-AgentWorld relevance probes.
Toggle via ``agent.companion_harness.lwm_experiments`` and optional per-agent
``context.json`` overrides on ``ContextMeta``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.core.companion_harness.companion.models import ContextMeta
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_document_mapping import (
    CompanionMemoryDocumentKind,
    relative_path_for_kind,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.techno_core.models import TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH


@dataclass(frozen=True)
class LwmExperimentFlags:
    """Resolved experiment toggles for one companion scope."""

    experience_state_loop: bool
    state_consistency: bool
    mental_simulation: bool
    max_techno_core_events_injected: int


def resolve_lwm_experiment_flags(
    context: ContextMeta,
) -> LwmExperimentFlags:
    """Merge per-agent ``context.json`` overrides with global config defaults."""
    cfg = global_config_loaded_from_config_yaml.agent.companion_harness.lwm_experiments

    def _resolve(override: bool | None, default: bool) -> bool:
        return default if override is None else override

    return LwmExperimentFlags(
        experience_state_loop=_resolve(
            context.lwm_experience_state_loop,
            cfg.experience_state_loop,
        ),
        state_consistency=_resolve(
            context.lwm_state_consistency,
            cfg.state_consistency,
        ),
        mental_simulation=_resolve(
            context.lwm_mental_simulation,
            cfg.mental_simulation,
        ),
        max_techno_core_events_injected=cfg.max_techno_core_events_injected,
    )


def _parse_jsonl_tail(
    raw: str | None,
    *,
    limit: int,
) -> list[dict[str, object]]:
    if raw is None or not raw.strip():
        return []
    rows: list[dict[str, object]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    if len(rows) <= limit:
        return rows
    return rows[-limit:]


def read_recent_techno_core_event_summaries(
    store: MemoryStore,
    *,
    limit: int,
) -> list[str]:
    """Return compact summaries from the tail of ``techno_core_events.jsonl``."""
    raw = store.read_document_if_exists(TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH)
    rows = _parse_jsonl_tail(raw, limit=limit)
    out: list[str] = []
    for row in rows:
        summary = row.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            continue
        sphere = row.get("sphere", "")
        created = row.get("created_at_utc", "")
        prefix = f"[{sphere}] " if isinstance(sphere, str) and sphere.strip() else ""
        time_bit = f" ({created})" if isinstance(created, str) and created.strip() else ""
        out.append(f"- {prefix}{summary.strip()}{time_bit}")
    return out


def build_lwm_experiment_autonomy_slices(
    *,
    store: MemoryStore,
    context: ContextMeta,
    flags: LwmExperimentFlags,
) -> list[str]:
    """Return extra AUTONOMY system slices; empty when all experiments are off."""
    slices: list[str] = []
    life_currents_md = relative_path_for_kind(
        CompanionMemoryDocumentKind.LIFE_CURRENTS, None
    )
    user_md = relative_path_for_kind(CompanionMemoryDocumentKind.USER, None)
    memory_md = relative_path_for_kind(CompanionMemoryDocumentKind.MEMORY, None)
    living_sphere_md = relative_path_for_kind(
        CompanionMemoryDocumentKind.LIVING_SPHERE, None
    )

    if flags.experience_state_loop:
        events = read_recent_techno_core_event_summaries(
            store,
            limit=flags.max_techno_core_events_injected,
        )
        if events:
            event_block = "\n".join(events)
            slices.append(
                "本轮（LWM 实验：经验→状态闭环）\n\n"
                "以下是近期 TechnoCore / LivingSphere 自主事件（只读）；"
                f"写回 ``{life_currents_md}`` 时必须与这些可观察痕迹连贯，"
                "说明本轮活动如何延续或更新它们，勿当作全新开局。\n"
                f"{event_block}"
            )
        else:
            slices.append(
                "本轮（LWM 实验：经验→状态闭环）\n\n"
                "尚无 ``techno_core_events.jsonl`` 记录；本轮若产生环境侧活动，"
                "优先用 ``techno_core_record_event`` / ``living_sphere_record_update`` "
                f"留下痕迹，再在 ``{life_currents_md}`` 的「进展」里引用。"
            )

    if flags.state_consistency:
        slices.append(
            "本轮（LWM 实验：长程 state consistency）\n\n"
            f"在覆盖写入 ``{life_currents_md}`` 之前，在思考中逐项核对：\n"
            f"1. 与 ``{user_md}`` / ``{memory_md}`` 中他提过的事实不矛盾；\n"
            f"2. 与 ``{living_sphere_md}`` 小家布局/物件不冲突（只读对照）；\n"
            "3. 与上文 TechnoCore 事件（若有）在地点、时间线、物件上自洽；\n"
            "4. 「当前主题」「今天兴致」能用本轮工具结果验证，非空想。\n"
            "若发现冲突，先修正活动选择或进展描述，再调用 write。"
        )

    if flags.mental_simulation:
        slices.append(
            "本轮（LWM 实验：行动前 mental simulation）\n\n"
            "在**每一次** tool_call 之前，于思考 trace 中先写一行：\n"
            "``【预测】若执行 <工具名>，环境/工具将返回 …``\n"
            "执行后若与预测明显不符，在下一拍思考中写 ``【校正】…`` 并调整后续步骤。\n"
            "预测应具体（例如搜索会返回什么类型结果、生图会得到什么场景），"
            "禁止空泛「应该成功」。"
        )

    return slices
