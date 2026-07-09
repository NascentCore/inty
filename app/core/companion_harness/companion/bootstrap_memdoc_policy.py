"""Bootstrap-phase MemDoc write policy for eval arms and production default.

Single semantic source for which paths bootstrap may write via
``memory_store_write_document``, which tools are registered on
``USER_CHAT_BOOTSTRAP``, and how bootstrap prompt slices describe procedure.
"""

from __future__ import annotations

from enum import StrEnum

from app.core.companion_harness.tools.companion_tool_definitions import (
    BOOTSTRAP_TRACK_TOOL_NAMES,
    BOOTSTRAP_WRITABLE_REL_PATHS,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
    CompanionToolName,
)


class BootstrapMemDocPolicy(StrEnum):
    """Whether bootstrap persists Persona MemDocs during AwakeTurn or defers to DreamingBatch."""

    AWAKE_WRITE = "awake_write"
    DREAMING_ONLY = "dreaming_only"
    DREAMING_INCEPTION = "dreaming_inception"


def resolve_bootstrap_memdoc_policy() -> BootstrapMemDocPolicy:
    """Read ``agent.companion_harness.bootstrap_memdoc_policy`` from loaded YAML config."""

    from app.core.config import global_config_loaded_from_config_yaml

    return (
        global_config_loaded_from_config_yaml.agent.companion_harness.bootstrap_memdoc_policy
    )


def bootstrap_writable_rel_paths(
    policy: BootstrapMemDocPolicy,
) -> frozenset[str]:
    """Return bootstrap ``memory_store_write_document`` allowlist for one policy."""

    assert policy is not None
    match policy:
        case BootstrapMemDocPolicy.AWAKE_WRITE:
            return MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP
        case (
            BootstrapMemDocPolicy.DREAMING_ONLY
            | BootstrapMemDocPolicy.DREAMING_INCEPTION
        ):
            return frozenset()


def bootstrap_track_tool_names(
    policy: BootstrapMemDocPolicy,
) -> tuple[CompanionToolName, ...]:
    """OpenAI tool manifest for ``USER_CHAT_BOOTSTRAP`` under one policy."""

    assert policy is not None
    match policy:
        case BootstrapMemDocPolicy.AWAKE_WRITE:
            return BOOTSTRAP_TRACK_TOOL_NAMES
        case (
            BootstrapMemDocPolicy.DREAMING_ONLY
            | BootstrapMemDocPolicy.DREAMING_INCEPTION
        ):
            return tuple(
                name
                for name in BOOTSTRAP_TRACK_TOOL_NAMES
                if name is not CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT
            )


def compose_bootstrap_tool_call_section(
    policy: BootstrapMemDocPolicy,
) -> str:
    """Bootstrap tool-call instructions appended after ``BOOTSTRAP.md``."""

    assert policy is not None
    lines: list[str] = [
        "## 工具调用",
        "",
        "- Bootstrap only done once",
        f"- Call **{CompanionToolName.MEMORY_STORE_READ_DOCUMENT.value}** to read persisted docs",
    ]
    match policy:
        case BootstrapMemDocPolicy.AWAKE_WRITE:
            docs = " / ".join(BOOTSTRAP_WRITABLE_REL_PATHS)
            lines.extend(
                [
                    f"- Call **{CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT.value}** to update **{docs}** (full markdown body per path)",
                    f"- Call **{CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE.value}** when the user clarifies what companionship experience they want "
                    f"(e.g. `casual_chat`, `deep_conversation`, `roleplay`, `remote_romance`); optional `tone` (`warm` / `playful` / `cool` / `direct`). "
                    "Bond narrative stays in COMPANIONSHIP.md — do not ask the user for harness `context_mode` ids",
                    f"- Call **{CompanionToolName.COMPANION_RECORD_USER_PROFILE.value}** optionally when the user confirms USER.md identity fields and DB analytics sync is desired (partial updates OK)",
                    f"- Call **{CompanionToolName.COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE.value}** to conclude bootstrap",
                    "- 尽快收尾：已有对话足以写初稿时，先 **memory_store_write_document** 写 IDENTITY / STYLE / USER，再 complete；禁止跳过写入直接 complete",
                    "- 即使用户配合度低，也基于已有对话写 best-effort 初稿；用户想进入日常相处或已连续多轮无新信息时可提前 complete（仍须先写初稿）",
                ]
            )
        case (
            BootstrapMemDocPolicy.DREAMING_ONLY
            | BootstrapMemDocPolicy.DREAMING_INCEPTION
        ):
            lines.extend(
                [
                    f"- Call **{CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE.value}** when the user clarifies what companionship experience they want "
                    f"(e.g. `casual_chat`, `deep_conversation`, `roleplay`, `remote_romance`); optional `tone` (`warm` / `playful` / `cool` / `direct`). "
                    "Bond narrative will be curated into COMPANIONSHIP.md during sleeping consolidation — do not ask the user for harness `context_mode` ids",
                    f"- Call **{CompanionToolName.COMPANION_RECORD_USER_PROFILE.value}** optionally when the user confirms identity fields and DB analytics sync is desired (partial updates OK)",
                    f"- Call **{CompanionToolName.COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE.value}** to conclude bootstrap once you understand the relationship framing",
                    "- Do **not** call memory_store_write_document during bootstrap; keep relationship facts in the live transcript for DreamingBatch curation",
                    "- When dialogue is sufficient, call complete; do not stall bootstrap for perfect MemDoc drafts",
                ]
            )
    lines.append(
        "- 不向用户说「初始化完成」「已同步」等工程话术；用关系语境带过即可。"
    )
    return "\n".join(lines)


def compose_bootstrap_procedure_overlay(
    policy: BootstrapMemDocPolicy,
) -> str:
    """Policy overlay correcting ``BOOTSTRAP.md`` write-first pacing when tools omit write."""

    assert policy is not None
    match policy:
        case BootstrapMemDocPolicy.AWAKE_WRITE:
            return ""
        case (
            BootstrapMemDocPolicy.DREAMING_ONLY
            | BootstrapMemDocPolicy.DREAMING_INCEPTION
        ):
            return "\n".join(
                [
                    "## Bootstrap MemDoc policy (dreaming curation)",
                    "",
                    "- Relationship seed docs (USER.md, IDENTITY.md, STYLE.md, COMPANIONSHIP.md) are **not** written during bootstrap.",
                    "- Capture names, tone, and companionship framing in dialogue; sleeping consolidation will curate MemDocs after bootstrap completes.",
                    "- You may complete bootstrap without MemDoc drafts when the transcript already carries enough relationship signal.",
                ]
            )


def bootstrap_complete_tool_result_text(
    policy: BootstrapMemDocPolicy,
) -> str:
    """LLM-visible status after ``companion_bootstrap_user_interactive_complete`` succeeds."""

    assert policy is not None
    match policy:
        case BootstrapMemDocPolicy.AWAKE_WRITE:
            return (
                "OK interactive bootstrap marked complete. IDENTITY / STYLE / USER / MEMORY / SOUL "
                "may still be updated via memory_store_write_document where permitted on later turns."
            )
        case BootstrapMemDocPolicy.DREAMING_ONLY:
            return (
                "OK interactive bootstrap marked complete. Persona MemDocs will be curated during "
                "the next DreamingBatch from the bootstrap transcript."
            )
        case BootstrapMemDocPolicy.DREAMING_INCEPTION:
            return (
                "OK interactive bootstrap marked complete. An inception DreamingBatch will curate "
                "Persona MemDocs from the bootstrap transcript as soon as the scope worker runs."
            )
