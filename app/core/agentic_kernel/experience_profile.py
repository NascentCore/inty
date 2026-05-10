"""Experience profile ids are stored in companion `context.json` as `context_mode`."""

from __future__ import annotations

from enum import StrEnum

# Reserved profile for interactive bootstrap before the user-facing experience id is chosen.
EXPERIENCE_PROFILE_ID_BOOTSTRAP = "bootstrap"


class ExperienceContextMode(StrEnum):
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

EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING = "## 当前体验配置（context_mode）"


def _experience_profile_clause(body: str) -> str:
    return f"{EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING}\n\n{body}"


def normalize_experience_profile_id(raw: str) -> str:
    s = raw.strip().lower()
    if not s:
        raise ValueError("experience profile id (context_mode) must be non-empty")
    return s


def experience_profile_injects_private_memory(profile_id: str) -> bool:
    return normalize_experience_profile_id(profile_id) in _PRIVATE_MEMORY_PROFILE_IDS


def experience_profile_system_clause(context_mode: str) -> str:
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
