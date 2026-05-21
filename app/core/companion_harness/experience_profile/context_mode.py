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

from app.core.companion_harness.tools.companion_tool_definitions import BOOTSTRAP_UPDATE_MEMORY_DOC_TOOL

# Reserved profile for interactive bootstrap before the user-facing experience id is chosen.
EXPERIENCE_PROFILE_ID_BOOTSTRAP = "bootstrap"


class ExperienceContextMode(StrEnum):
    """Built-in ``context_mode`` values understood by prompt assembly."""

    UNSPECIFIC = "unspecific"
    INTIMATE = "intimate"
    EMOTIONAL_COMPANION = "emotional_companion"
    BOOTSTRAP = "bootstrap"
    ROLEPLAY = "roleplay"
    INTERACTIVE_FICTION = "interactive_fiction"
    PUBLIC = "public"


_PRIVATE_MEMORY_PROFILE_IDS = frozenset(
    {
        ExperienceContextMode.UNSPECIFIC,
        ExperienceContextMode.INTIMATE,
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
            "交互式关系建立（bootstrap）。\n"
            f"本阶段使用 {BOOTSTRAP_UPDATE_MEMORY_DOC_TOOL.name}.md 是初始化 SOUL.md IDENTITY.md USER.md 等与用户的初步关系锚点；\n"
            "不要延续超过 30 轮对话，否则用户可能会感到厌烦。\n"
            "完成引导后将恢复到常规体验配置（由会话快照或产品默认决定）。\n"
            "需要按照模板询问用户来定义你和用户的基本信息；犹豫不决的用户可以代为体用户建议。\n"
            ""
        )
    if n in _PRIVATE_MEMORY_PROFILE_IDS:
        if n == ExperienceContextMode.INTIMATE:
            return _experience_profile_clause(
                "亲密主会话（intimate）。可加载完整长期记忆，语气可更放松、贴近私人对话，"
                "仍须遵守安全与同意边界。"
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
