"""Tool-driven MemoryStore bootstrap for first-run relationship setup.

When ``context.json`` marks the interactive bootstrap flag incomplete,
``run_companion_user_chat_turn`` enters ``USER_CHAT_BOOTSTRAP``.  That track
uses a single in-turn tool loop so the assistant can persist relationship seed
documents via ``memory_store_write_document`` and mark setup complete before
normal user-chat routing resumes.

**Primary path (production):** ``ScopeQueueServing`` claims an InputQueue batch,
runs ``BootstrapUserChatPlugin`` via ``AgenticLoop``, and drains ``OutputQueue``
through the channel presence pump.

**Backup-only:** direct ``_run_companion_turn_core`` / HTTP helpers without
queue-serving batch correlation are unsupported for bootstrap (#3466).  Settled
``USER_CHAT`` may still use a synthetic ``agent-initiated:`` batch as a legacy
direct-turn fallback; do not extend that pattern for bootstrap.

WebSocket startup does not inject a synthetic kickoff user message.  A signed-on
client emits the implicit sign-on greeting track, whose system stack carries the
bootstrap procedure while the tail user line frames the user coming online.  The
bootstrap tool path is still responsible for persisting the relationship seed
documents and flipping the bootstrap completion flag.
"""

from __future__ import annotations

import json
from typing import Any, Final

from loguru import logger
from pydantic import BaseModel, Field, model_validator

from app.core.companion_harness.experience_profile.experience_directives import (
    ExperienceDirectives,
    ExperienceDirectiveTone,
    ExperienceSessionIntent,
    context_mode_for_session_intent,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    BOOTSTRAP_MD_REL,
    BOOTSTRAP_TELEGRAM_PROFILE_MD_REL,
    CONTEXT_JSON_REL,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
    load_template_seed_text,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    BOOTSTRAP_WRITABLE_REL_PATHS,
    CompanionToolName,
)
from app.models.user import Gender
from app.schemas.user import UserAgeGroup, UserProfileSnapshot

from .models import ContextMeta

_SCOPE_PATHS = DEFAULT_MEMORY_STORE_SCOPE_PATHS

# Seed-only rels via MemoryStoreScopePaths accessors (#3413).
_BOOTSTRAP_TEMPLATE_SEED_ONLY_RELS: Final[tuple[str, ...]] = (
    _SCOPE_PATHS.memory_md,
    _SCOPE_PATHS.soul,
)

_INTERACTIVE_TEMPLATE_RELS: Final[tuple[str, ...]] = tuple(
    sorted({*BOOTSTRAP_WRITABLE_REL_PATHS, *_BOOTSTRAP_TEMPLATE_SEED_ONLY_RELS})
)

# TODO(person-identity-schema): TEMPLATE_REFERENCE should show generic templates/IDENTITY.md schema once, — #3390
# not separate USER.md + IDENTITY.md package seeds; runtime bootstrap still writes both paths. #3390

# TODO(bootstrap-prompt-single-source): Bootstrap write/tool rules duplicated across — #3801
# ``prompts/BOOTSTRAP.md``, ``build_bootstrap_tool_call_section``, and
# ``_output_contract_text_interactive_bootstrap_tools``; derive all three from one typed
# policy next to ``BOOTSTRAP_WRITABLE_REL_PATHS`` / ``BOOTSTRAP_TRACK_TOOL_NAMES``.
# CRS bootstrap relationship seed — #3328; consolidate with ``TrackWritePolicy`` — #3367.


def build_bootstrap_tool_call_section() -> str:
    """工具调用 section rendered from typed tool names; accompanies BOOTSTRAP.md."""

    docs = " / ".join(BOOTSTRAP_WRITABLE_REL_PATHS)
    return "\n".join(
        [
            "## 工具调用",
            "",
            "- Bootstrap only done once",
            f"- Call **{CompanionToolName.MEMORY_STORE_READ_DOCUMENT.value}** to read persisted docs before updating",
            f"- Call **{CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT.value}** to update **{docs}** (full markdown body per path)",
            f"- Call **{CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE.value}** when the user clarifies what companionship experience they want "
            f"(e.g. `casual_chat`, `deep_conversation`, `roleplay`, `remote_romance`); optional `tone` (`warm` / `playful` / `cool` / `direct`). "
            "Bond narrative stays in COMPANIONSHIP.md — do not ask the user for harness `context_mode` ids",
            f"- Call **{CompanionToolName.COMPANION_RECORD_USER_PROFILE.value}** optionally when the user confirms USER.md identity fields and DB analytics sync is desired (partial updates OK)",
            f"- Call **{CompanionToolName.COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE.value}** to conclude bootstrap",
            "- 尽快收尾：已有对话足以写初稿时，先 **memory_store_write_document** 写 IDENTITY / STYLE / USER，再 complete；禁止跳过写入直接 complete",
            "- 即使用户配合度低，也基于已有对话写 best-effort 初稿；用户想进入日常相处或已连续多轮无新信息时可提前 complete（仍须先写初稿）",
            "- 不向用户说「初始化完成」「已同步」等工程话术；用关系语境带过即可。",
        ]
    )


def load_bootstrap_spec_text() -> str:
    """Load the internal bootstrap procedure injected into bootstrap turns."""

    return load_template_seed_text(BOOTSTRAP_MD_REL).rstrip()


def load_bootstrap_telegram_profile_slice_text() -> str:
    """Load the Telegram-only bootstrap overlay prompt slice.

    Paid-ad cohort users arrive via Telegram. The overlay supplements the shared
    bootstrap procedure: use English for user-visible copy until the user switches
    language, open with getting-to-know-you (age range is a natural first question),
    and probe empty identity slots in the user profile document early—one question
    at a time, without delaying bootstrap completion if the user is impatient or skips.
    Tools, profile fields, and completion rules remain in the shared bootstrap procedure.
    """

    return load_template_seed_text(BOOTSTRAP_TELEGRAM_PROFILE_MD_REL).rstrip()


def profile_collection_active(*, context: ContextMeta) -> bool:
    """Whether bootstrap should add Telegram cohort profile-collection guidance.

    Set on new Telegram guest sessions so bootstrap turns nudge the companion toward
    filling unfilled identity slots in the user profile document.
    """
    return context.profile_collection_required


def interactive_bootstrap_active(
    *,
    meta: ContextMeta,
) -> bool:
    """True when this scope should still run ``USER_CHAT_BOOTSTRAP`` / bootstrap Persona slices.

    Driven only by per-session ``context.json`` completion flag — not deploy config.
    The current experience profile may already be non-bootstrap because completion
    can preserve an externally chosen relationship mode.

    TODO(bootstrap-max-turns): Harness-level cap (max user-chat rounds or wall — #3801
    clock) before forcing best-effort MemoryDoc writes + complete — prompt-only
    pacing in ``BOOTSTRAP.md`` is insufficient when the model skips tools.
    But the principle is to let the LLM decide when to complete, not to force it.
    So leave this TODO open for debate and evaluation.
    """

    return not meta.workspace_bootstrap_user_interactive_completed


def build_interactive_bootstrap_template_reference_parts(
    *,
    max_chars_per_seed: int = 6000,
) -> list[str]:
    """Template seed bodies for bootstrap context (incl. SOUL/MEMORY package defaults)."""

    blocks: list[str] = []
    for rel in _INTERACTIVE_TEMPLATE_RELS:
        try:
            seed = load_template_seed_text(rel)
        except FileNotFoundError:
            seed = ""
        body = seed.strip()
        if max_chars_per_seed > 0 and len(body) > max_chars_per_seed:
            body = body[: max_chars_per_seed - 1] + "\n…[truncated]"
        blocks.append(f"## TEMPLATE_REFERENCE {rel}\n\n{body}")
    return blocks


def tool_companion_bootstrap_user_interactive_complete(
    store: MemoryStore,
    note: str | None = None,
) -> str:
    """Mark interactive bootstrap complete in ``context.json``.

    ``context_mode`` remains the real experience profile for the session;
    bootstrap is only a completion flag. Tool callers receive a plain ``OK`` or
    ``ERROR`` status string because the LLM tool loop consumes the result text.
    """

    rel = CONTEXT_JSON_REL
    st = store
    raw_body = st.read_document_if_exists(rel)
    if raw_body is None or not raw_body.strip():
        return "ERROR: missing context.json"
    try:
        data: dict[str, Any] = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid context.json: {exc}"
    if not isinstance(data, dict):
        return "ERROR: context.json must be a JSON object"
    data["workspace_bootstrap_user_interactive_completed"] = True
    if note is not None and str(note).strip():
        data["workspace_bootstrap_user_interactive_complete_note"] = str(
            note
        ).strip()[:2000]
    out = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    st.write_document(rel, out)
    logger.info(
        "companion_bootstrap_user_interactive_complete scope={}",
        st.scope.registry_key(),
    )
    return (
        "OK interactive bootstrap marked complete. IDENTITY / STYLE / USER / MEMORY / SOUL "
        "may still be updated via memory_store_write_document where permitted on later turns."
    )


class CompanionSetExperienceProfileToolInput(BaseModel):
    """Arguments for ``companion_set_experience_profile`` tool handler."""

    experience_intent: ExperienceSessionIntent = Field(
        description=(
            "What companionship experience the user wants: casual chat, deep conversation, "
            "role-play, emotional support, remote romance, or interactive fiction."
        ),
    )
    note: str = Field(
        description="Short internal audit note (not shown to user)."
    )
    tone: ExperienceDirectiveTone | None = Field(
        default=None,
        description="Optional experience_directives.tone overlay; omit to leave unchanged.",
    )


def tool_companion_set_experience_profile(
    store: MemoryStore,
    tool_input: CompanionSetExperienceProfileToolInput,
) -> str:
    """Persist ``experience_directives`` and mapped ``context_mode`` in ``context.json``."""

    normalized = context_mode_for_session_intent(tool_input.experience_intent)
    rel_ctx = CONTEXT_JSON_REL
    st = store
    raw_body = st.read_document_if_exists(rel_ctx)
    if raw_body is None or not str(raw_body).strip():
        return "ERROR: missing context.json"
    try:
        data: dict[str, Any] = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid context.json: {exc}"
    if not isinstance(data, dict):
        return "ERROR: context.json must be a JSON object"
    previous = str(data.get("context_mode", "")).strip() or "(unset)"
    existing_directives = ExperienceDirectives.model_validate(
        data.get("experience_directives") or {}
    )
    directive_updates: dict[
        str, ExperienceSessionIntent | ExperienceDirectiveTone
    ] = {
        "intent": tool_input.experience_intent,
    }
    if tool_input.tone is not None:
        directive_updates["tone"] = tool_input.tone
    directives = existing_directives.model_copy(update=directive_updates)
    updated = ContextMeta.model_validate(
        {
            **data,
            "context_mode": normalized,
            "experience_directives": directives,
        }
    )
    persisted = updated.model_dump(mode="json")
    # Audit note only; not part of ContextMeta (ephemeral tool rationale).
    persisted["experience_change_note"] = tool_input.note.strip()[:2000]
    out = json.dumps(persisted, indent=2, ensure_ascii=False) + "\n"
    st.write_document(rel_ctx, out)
    logger.info(
        "companion_set_experience_profile scope={} {} -> {} intent={} tone={}",
        st.scope.registry_key(),
        previous,
        normalized,
        tool_input.experience_intent.value,
        directives.tone.value if directives.tone is not None else None,
    )
    tone_suffix = ""
    if tool_input.tone is not None:
        tone_suffix = f"; experience_directives.tone={tool_input.tone.value!r}"
    return (
        f"OK experience intent set to {tool_input.experience_intent.value!r} "
        f"(context_mode {normalized!r}, previous {previous!r}){tone_suffix}; "
        "applies starting the next companion turn."
    )


class CompanionRecordUserProfileToolInput(BaseModel):
    """Arguments for ``companion_record_user_profile`` bootstrap tool."""

    gender: Gender | None = Field(
        default=None,
        description="User gender when confirmed.",
    )
    age_group: UserAgeGroup | None = Field(
        default=None,
        description="User age bucket when confirmed.",
    )
    location: str | None = Field(
        default=None,
        description="City or region when confirmed.",
    )
    iana_timezone: str | None = Field(
        default=None,
        description="Optional IANA timezone inferred from location.",
    )
    note: str = Field(
        description="Short internal audit note (not shown to user).",
    )

    @model_validator(mode="after")
    def _at_least_one_profile_field(
        self,
    ) -> CompanionRecordUserProfileToolInput:
        has_field = (
            self.gender is not None
            or self.age_group is not None
            or (self.location is not None and self.location.strip() != "")
            or (
                self.iana_timezone is not None
                and self.iana_timezone.strip() != ""
            )
        )
        if not has_field:
            raise ValueError(
                "at least one of gender, age_group, location, iana_timezone is required"
            )
        return self

    def to_snapshot(self) -> UserProfileSnapshot:
        """Map validated tool input to persistence snapshot."""
        location = self.location.strip() if self.location else None
        tz = self.iana_timezone.strip() if self.iana_timezone else None
        return UserProfileSnapshot(
            gender=self.gender,
            age_group=self.age_group,
            location=location if location else None,
            iana_timezone=tz if tz else None,
        )
