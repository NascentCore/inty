"""Sole contextual-category orchestrator for companion system-prefix assembly.

Gates experience profile, directives, timezone, proactive clauses, and ABOUT.md
by ``TurnComposeContext.track`` and ``phase``. Atomic slice text builders remain
in ``system_messages`` until Phase 2 ``TrackSystemRecipe`` (#3453).
"""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.proactive_chat import (
    BOOTSTRAP_PROACTIVE_CONTEXTUAL_OVERLAY,
)
from app.core.companion_harness.experience_profile.context_mode import (
    experience_profile_system_clause,
)
from app.core.companion_harness.experience_profile.experience_directives import (
    experience_directives_system_clause,
)
from app.core.companion_harness.prompting.compose_context import TurnComposeContext
from app.core.companion_harness.prompting.system_messages import (
    _about_operator_guidance_system_messages,
    _get_inner_tick_autonomy_prompt_slice,
    _infer_time_zone_prompt_slice,
    _inner_tick_ai_private_section,
    _inner_tick_turn_section,
    _proactive_chat_clause,
    _system_message,
)
from app.core.companion_harness.prompting.phase import Phase


def _append_directives(
    out: list[dict[str, Any]],
    ctx: TurnComposeContext,
) -> None:
    directive_clause = experience_directives_system_clause(
        ctx.context_meta.experience_directives
    )
    if directive_clause is not None:
        out.append(_system_message(directive_clause))


def _append_experience_profile(
    out: list[dict[str, Any]],
    ctx: TurnComposeContext,
) -> None:
    out.append(
        _system_message(
            experience_profile_system_clause(ctx.context_meta.context_mode)
        )
    )


def _append_time_zone(out: list[dict[str, Any]]) -> None:
    out.append(_system_message(_infer_time_zone_prompt_slice()))


def _append_proactive_clause(out: list[dict[str, Any]]) -> None:
    out.append(_system_message(_proactive_chat_clause()))


def _append_user_turn_contextual(
    out: list[dict[str, Any]],
    ctx: TurnComposeContext,
) -> None:
    if ctx.phase == Phase.SETTLED:
        _append_experience_profile(out, ctx)
    _append_directives(out, ctx)
    _append_time_zone(out)


def _append_inner_tick_monolog_contextual(
    out: list[dict[str, Any]],
    ctx: TurnComposeContext,
) -> None:
    _append_experience_profile(out, ctx)
    _append_directives(out, ctx)
    out.append(
        _system_message(_inner_tick_ai_private_section(ctx.ai_private_text))
    )
    out.append(_system_message(_inner_tick_turn_section()))


def _append_inner_tick_autonomy_contextual(
    out: list[dict[str, Any]],
    ctx: TurnComposeContext,
) -> None:
    _append_experience_profile(out, ctx)
    _append_directives(out, ctx)
    out.append(_system_message(_get_inner_tick_autonomy_prompt_slice()))


def assemble_contextual_slices(ctx: TurnComposeContext) -> list[dict[str, Any]]:
    """Sole contextual-category orchestrator for all production tracks."""
    out: list[dict[str, Any]] = []
    match ctx.track:
        case (
            CompanionTurnTrack.USER_CHAT
            | CompanionTurnTrack.USER_CHAT_BOOTSTRAP
            | CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
        ):
            _append_user_turn_contextual(out, ctx)
        case CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT:
            match ctx.phase:
                case Phase.BOOTSTRAP:
                    _append_directives(out, ctx)
                    _append_time_zone(out)
                    _append_proactive_clause(out)
                    out.append(
                        _system_message(BOOTSTRAP_PROACTIVE_CONTEXTUAL_OVERLAY)
                    )
                    if ctx.proactive_life_currents_block is not None:
                        out.append(
                            _system_message(ctx.proactive_life_currents_block)
                        )
                case Phase.SETTLED:
                    _append_experience_profile(out, ctx)
                    _append_directives(out, ctx)
                    _append_proactive_clause(out)
                    if ctx.proactive_life_currents_block is not None:
                        out.append(
                            _system_message(ctx.proactive_life_currents_block)
                        )
        case CompanionTurnTrack.INNER_TICK_SCHEDULED:
            match ctx.phase:
                case Phase.BOOTSTRAP:
                    _append_directives(out, ctx)
                    _append_time_zone(out)
                    _append_proactive_clause(out)
                case Phase.SETTLED:
                    _append_experience_profile(out, ctx)
                    _append_directives(out, ctx)
                    _append_proactive_clause(out)
        case CompanionTurnTrack.INNER_TICK_MONOLOG:
            _append_inner_tick_monolog_contextual(out, ctx)
        case CompanionTurnTrack.INNER_TICK_AUTONOMY:
            _append_inner_tick_autonomy_contextual(out, ctx)
        case _ as unexpected:
            raise AssertionError(
                f"assemble_contextual_slices unsupported track={unexpected!r}"
            )
    out.extend(
        _about_operator_guidance_system_messages(
            ctx.bundle,
            ctx.compose_trigger,
        )
    )
    return out
