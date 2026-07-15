"""Tests for ``assemble_contextual_slices`` contextual gate matrix."""

from __future__ import annotations

from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.proactive_chat import (
    BOOTSTRAP_PROACTIVE_CONTEXTUAL_OVERLAY,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.experience_profile.experience_directives import (
    ExperienceDirectiveTone,
    ExperienceDirectives,
    ExperienceSessionIntent,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    ABOUT_MD_REL,
)
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.prompting.compose_context import (
    build_turn_compose_context,
)
from app.core.companion_harness.prompting.contextual import assemble_contextual_slices
from app.core.companion_harness.prompting.leg_kind import PromptLegKind
from app.core.companion_harness.prompting.phase import Phase
from app.core.companion_harness.companion.models import ContextMeta
from app.core.companion_harness.memory.memory_store_scope import (
    load_template_seed_text,
)


def _store(tmp_path) -> MemoryStore:
    return MemoryStore(
        scope=CompanionScope("contextual", "agent", tmp_path.name),
        repository=None,
    )


def _runtime() -> TurnRuntimeContext:
    return TurnRuntimeContext(
        channel=ChannelKind.APP_WS,
        implicit_signal_bundle=None,
    )


def _bundle(*, about_md: str = "") -> PromptBundle:
    return PromptBundle(
        identity="id\n",
        soul="s\n",
        style_md="st\n",
        user_md="u\n",
        memory_md="m\n",
        about_md=about_md,
    )


def _joined(messages: list[dict]) -> str:
    return "\n".join(
        str(m["content"]) for m in messages if m["role"] == "system"
    )


def test_settled_user_turn_contextual(tmp_path) -> None:
    about_body = load_template_seed_text(ABOUT_MD_REL).strip()
    ctx = build_turn_compose_context(
        bundle=_bundle(about_md=about_body),
        context_meta=ContextMeta(context_mode="intimate"),
        runtime_context=_runtime(),
        store=_store(tmp_path),
        track=CompanionTurnTrack.USER_CHAT,
        phase=Phase.SETTLED,
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text="",
        proactive_life_currents_block=None,
    )
    joined = _joined(assemble_contextual_slices(ctx))
    assert "用户当地时间与作息" in joined
    assert about_body.split("\n")[0] in joined


def test_bootstrap_user_turn_contextual_greeting_no_about(tmp_path) -> None:
    about_body = load_template_seed_text(ABOUT_MD_REL).strip()
    ctx = build_turn_compose_context(
        bundle=_bundle(about_md=about_body),
        context_meta=ContextMeta(),
        runtime_context=_runtime(),
        store=_store(tmp_path),
        track=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
        phase=Phase.BOOTSTRAP,
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text="",
        proactive_life_currents_block=None,
    )
    joined = _joined(assemble_contextual_slices(ctx))
    assert "用户当地时间与作息" in joined
    assert about_body.split("\n")[0] not in joined


def test_monolog_contextual(tmp_path) -> None:
    about_body = load_template_seed_text(ABOUT_MD_REL).strip()
    ctx = build_turn_compose_context(
        bundle=_bundle(about_md=about_body),
        context_meta=ContextMeta(),
        runtime_context=_runtime(),
        store=_store(tmp_path),
        track=CompanionTurnTrack.INNER_TICK_MONOLOG,
        phase=Phase.SETTLED,
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text="private line",
        proactive_life_currents_block=None,
    )
    joined = _joined(assemble_contextual_slices(ctx))
    assert "内在活动（ai_private）" in joined
    assert "用户当地时间与作息" not in joined
    assert about_body.split("\n")[0] not in joined


def test_proactive_settled_contextual(tmp_path) -> None:
    life_block = "LIFE_CURRENTS hint block"
    ctx = build_turn_compose_context(
        bundle=_bundle(),
        context_meta=ContextMeta(),
        runtime_context=_runtime(),
        store=_store(tmp_path),
        track=CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
        phase=Phase.SETTLED,
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text="",
        proactive_life_currents_block=life_block,
    )
    joined = _joined(assemble_contextual_slices(ctx))
    assert "本轮（陪伴主动聊天）" in joined
    assert life_block in joined
    assert "用户当地时间与作息" not in joined


def test_proactive_bootstrap_contextual(tmp_path) -> None:
    ctx = build_turn_compose_context(
        bundle=_bundle(),
        context_meta=ContextMeta(),
        runtime_context=_runtime(),
        store=_store(tmp_path),
        track=CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
        phase=Phase.BOOTSTRAP,
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text="",
        proactive_life_currents_block=None,
    )
    joined = _joined(assemble_contextual_slices(ctx))
    assert "本轮（陪伴主动聊天）" in joined
    assert BOOTSTRAP_PROACTIVE_CONTEXTUAL_OVERLAY.split("\n")[0] in joined
    assert "用户当地时间与作息" in joined


def test_scheduled_bootstrap_contextual(tmp_path) -> None:
    ctx = build_turn_compose_context(
        bundle=_bundle(),
        context_meta=ContextMeta(),
        runtime_context=_runtime(),
        store=_store(tmp_path),
        track=CompanionTurnTrack.INNER_TICK_SCHEDULED,
        phase=Phase.BOOTSTRAP,
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text="",
        proactive_life_currents_block=None,
    )
    joined = _joined(assemble_contextual_slices(ctx))
    assert "本轮（陪伴主动聊天）" in joined
    assert "用户当地时间与作息" in joined
    assert BOOTSTRAP_PROACTIVE_CONTEXTUAL_OVERLAY.split("\n")[0] not in joined


def test_scheduled_settled_contextual(tmp_path) -> None:
    ctx = build_turn_compose_context(
        bundle=_bundle(),
        context_meta=ContextMeta(
            context_mode="emotional_companion",
            experience_directives=ExperienceDirectives(
                intent=ExperienceSessionIntent.CASUAL_CHAT,
                tone=ExperienceDirectiveTone.WARM,
            ),
        ),
        runtime_context=_runtime(),
        store=_store(tmp_path),
        track=CompanionTurnTrack.INNER_TICK_SCHEDULED,
        phase=Phase.SETTLED,
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text="",
        proactive_life_currents_block=None,
    )
    joined = _joined(assemble_contextual_slices(ctx))
    assert "本轮（陪伴主动聊天）" in joined
    assert "LIFE_CURRENTS" not in joined


def test_autonomy_contextual(tmp_path) -> None:
    ctx = build_turn_compose_context(
        bundle=_bundle(),
        context_meta=ContextMeta(),
        runtime_context=_runtime(),
        store=_store(tmp_path),
        track=CompanionTurnTrack.INNER_TICK_AUTONOMY,
        phase=Phase.SETTLED,
        leg_kind=PromptLegKind.SINGLE_LLM,
        ai_private_text="",
        proactive_life_currents_block=None,
    )
    joined = _joined(assemble_contextual_slices(ctx))
    assert "本轮（AUTONOMY 自主活动）" in joined
