"""Experience profile ids are stored in companion `context.json` as `context_mode`."""

from __future__ import annotations

# Reserved profile for interactive bootstrap before the user-facing experience id is chosen.
EXPERIENCE_PROFILE_ID_BOOTSTRAP = "bootstrap"

_PRIVATE_MEMORY_PROFILE_IDS = frozenset(
    {
        "unspecific",
        "intimate",
        "emotional_companion",
    }
)

_EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING = "## 当前体验配置（context_mode）"


def _experience_profile_clause(body: str) -> str:
    return f"{_EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING}\n\n{body}"


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
    if n in _PRIVATE_MEMORY_PROFILE_IDS:
        if n == "intimate":
            return _experience_profile_clause(
                "亲密主会话（intimate）。可加载完整长期记忆，语气可更放松、贴近私人对话，"
                "仍须遵守安全与同意边界。"
            )
        return _experience_profile_clause(
            "情感陪伴（emotional_companion）。与亲密主会话同等加载私人记忆与日程记忆层；"
            "优先共情与稳定陪伴，避免戏剧化套路；仍须遵守安全与同意边界。"
        )
    if n == "roleplay":
        return _experience_profile_clause(
            "角色扮演（roleplay）。不注入长期私人记忆与当日日记类材料，以免与人设或场景冲突；"
            "以 IC 一致性与场景延续为先，适度克制引用现实侧私密档案。"
        )
    if n == "interactive_fiction":
        return _experience_profile_clause(
            "互动小说（interactive_fiction）。不注入长期私人记忆与当日日记类材料；"
            "以叙事推进与世界状态为准，将用户输入视为行动或选择，保持体裁连贯。"
        )
    if n == "public":
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
