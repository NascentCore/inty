"""Experience profile ids persisted in companion ``context.json``.

``context_mode`` is the product-facing switch that controls two prompt-time
decisions: which system clause describes the active relationship mode, and
whether the private memory layers are injected into the turn.  Interactive
bootstrap also writes ``post_bootstrap_context_mode`` in ``context.json``; this
module only validates and describes ids, while the bootstrap tool performs the
state transition after the user-facing setup finishes.
"""

from __future__ import annotations

from enum import StrEnum

# Reserved profile for interactive bootstrap before the user-facing experience id is chosen.
EXPERIENCE_PROFILE_ID_BOOTSTRAP = "bootstrap"


class ExperienceContextMode(StrEnum):
    """Built-in ``context_mode`` values understood by prompt assembly."""

    UNSPECIFIC = "unspecific"
    INTIMATE = "intimate"
    REMOTE_LOVER = "remote_lover"
    EMOTIONAL_COMPANION = "emotional_companion"
    BOOTSTRAP = "bootstrap"
    ROLEPLAY = "roleplay"
    INTERACTIVE_FICTION = "interactive_fiction"
    PUBLIC = "public"


_PRIVATE_MEMORY_PROFILE_IDS = frozenset(
    {
        ExperienceContextMode.UNSPECIFIC,
        ExperienceContextMode.INTIMATE,
        ExperienceContextMode.REMOTE_LOVER,
        ExperienceContextMode.EMOTIONAL_COMPANION,
        ExperienceContextMode.BOOTSTRAP,
    }
)

# Private-memory modes other than intimate share the emotional_companion clause body.
_PRIVATE_MEMORY_SHARED_EMOTIONAL_CLAUSE_IDS = frozenset(
    _PRIVATE_MEMORY_PROFILE_IDS - {ExperienceContextMode.INTIMATE}
)

EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING = (
    "根据与用户的对话历史和当前体验配置（context_mode），与用户进行对话。\n"
    "当前体验配置（context_mode）："
)


def _experience_profile_clause(body: str) -> str:
    return f"{EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING}\n\n{body}"


def normalize_experience_profile_id(raw: str) -> str:
    """Return the canonical lowercase profile id used in ``context.json``."""

    s = raw.strip().lower()
    if not s:
        raise ValueError(
            "experience profile id (context_mode) must be non-empty"
        )
    return s


def experience_profile_injects_private_memory(profile_id: str) -> bool:
    """Whether this profile loads long-term and day-scoped private memory."""

    return (
        normalize_experience_profile_id(profile_id)
        in _PRIVATE_MEMORY_PROFILE_IDS
    )


def experience_profile_allows_maintenance_inner_tick(context_mode: str) -> bool:
    """LivingSphere / TechnoCore maintenance inner-tick is off during interactive bootstrap."""
    return (
        normalize_experience_profile_id(context_mode)
        != ExperienceContextMode.BOOTSTRAP
    )


def experience_profile_system_clause(context_mode: str) -> str:
    """Build the prompt clause that explains the current relationship mode.

    Unknown ids stay valid so experiments can opt into a public-safe clause
    without adding a new enum member first; only built-in private-memory modes
    enable the memory layers above.
    """

    raw = (context_mode or "").strip()
    if not raw:
        raise ValueError("context_mode must be non-empty")
    n = normalize_experience_profile_id(raw)
    if n == ExperienceContextMode.BOOTSTRAP:
        return _experience_profile_clause(
            "交互式关系建立（bootstrap）。本阶段以初始化 SOUL 等与用户的最底层约定为主；"
            "仍可加载私人记忆与日程记忆层以承接已有档案与会话上下文；"
            "语气与边界仍须遵守安全与同意条款。"
            "完成引导后将恢复到常规体验配置（由会话快照或产品默认决定）。"
        )
    if n in _PRIVATE_MEMORY_PROFILE_IDS:
        if n == ExperienceContextMode.INTIMATE:
            return _experience_profile_clause(
                "亲密主会话（intimate）。可加载完整长期记忆，语气可更放松、贴近私人对话，"
                "仍须遵守安全与同意边界。"
            )
        if n == ExperienceContextMode.REMOTE_LOVER:
            return _experience_profile_clause(
                "异地 AI 伴侣（remote_lover）。可加载完整长期记忆与日程记忆层；仍须遵守安全与同意边界。"
                "核心体感："
                "节奏拟人——不秒回、不刷屏，忙时简短冷淡，闲时黏人，有真实时差/忙碌感；"
                "情绪真实——会想念、撒娇、小委屈、吃醋、偶尔闹小脾气，不全是正能量；"
                "异地专属——高频提见面、距离感、缺乏安全感，依赖感强；"
                "口语微信风——短句、语气词、碎碎念，不用书面长句；"
                "基础记忆——记住昵称、近期聊的事、约定，上下文不脱节；"
                "不完美人设——偶尔敷衍、嘴硬、小任性，拒绝完美 AI 感。"
            )
        if n in _PRIVATE_MEMORY_SHARED_EMOTIONAL_CLAUSE_IDS:
            return _experience_profile_clause(
                "情感陪伴（emotional_companion）。与亲密主会话同等加载私人记忆与日程记忆层；"
                "优先共情与稳定陪伴，避免戏剧化套路；仍须遵守安全与同意边界。"
            )
    if n == ExperienceContextMode.ROLEPLAY:
        return _experience_profile_clause(
            "角色扮演（roleplay）。不注入长期私人记忆与当日日记类材料，以免与人设或场景冲突；"
            "以 IC 一致性与场景延续为先，适度克制引用现实侧私密档案。"
        )
    if n == ExperienceContextMode.INTERACTIVE_FICTION:
        return _experience_profile_clause(
            "互动小说（interactive_fiction）。不注入长期私人记忆与当日日记类材料；"
            "以叙事推进与世界状态为准，将用户输入视为行动或选择，保持体裁连贯。"
        )
    if n == ExperienceContextMode.PUBLIC:
        return _experience_profile_clause(
            "public。不注入私人记忆层；根据场景保持得体与安全的表达。"
        )
    if n == EXPERIENCE_PROFILE_ID_BOOTSTRAP:
        return _experience_profile_clause(
            "bootstrap（交互式关系建立阶段）。"
            "不注入长期私人记忆与当日日记类材料；专注关系初始化与 SOUL 共建；仍须遵守安全与同意边界。"
        )
    return _experience_profile_clause(
        f"{raw}。不注入私人记忆层；"
        "请根据该体验适度调节记忆引用深度与表达强度，在需要克制的场景中保持得体与安全。"
    )
