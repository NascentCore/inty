"""Companion LLM function-tool definitions for OpenAI Chat Completions.

Schema single source for companion harness tools. Execution lives in
``companion_tool_runtime`` (``_dispatch`` / ``execute_tool_call``).

New tool checklist:
1. Add ``CompanionToolName`` member
2. Add ``LlmFunctionTool`` to ``COMPANION_LLM_TOOLS``
3. Update REPL / inner-tick name tuples if the tool appears there
4. Add ``_dispatch`` branch in ``companion_tool_runtime``
5. Run ``test_companion_tool_definitions.py``

TODO(abstraction): Group tools by defining tuple of LlmFunctionTool data objects.
Do not group by tool names.

TODO(companion-channel-tools): Channel-specific tool schemas + ``CompanionToolName`` members
  (e.g. companion_set_status_line); filter by ``runtime_context.channel`` — #3362
TODO(telegram-meta-ops-tools): Telegram meta tools (e.g. telegram_set_bot_name) — #3397;
  gated on dedicated-bot bonding #3361; shared-bot path #3396
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field

from app.core.companion_harness.experience_profile import (
    ExperienceContextMode,
    ExperienceDirectiveTone,
)
from app.core.companion_harness.tools.openai_tools_prepare import (
    openai_function_tool,
)
from app.living_sphere.models import (
    LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME,
    LIVING_SPHERE_UPDATES_JSONL_RELATIVE_PATH,
)
from app.techno_core.models import (
    TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH,
    TECHNO_CORE_RECORD_EVENT_TOOL_NAME,
)

MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP: int = 120_000

# TODO(ai-private-jsonl-write): ``ai_private.jsonl`` (inner thoughts *about the user*, MAINTENANCE)
# is ORM-mapped but excluded here — not ``LIFE_CURRENTS.md`` (virtual-world activity, AUTONOMY).
# Enable MAINTENANCE append via dedicated append-only tool (preferred) or allowlist + append-only runtime.
# CRS Awake express / Dreaming learn — PR #3290; follow-up #3375 #3376; epic #3341.
# TODO(track-write-policy): Collapse per-track ``memory_store_write_document`` policy into one
# ``TrackWritePolicy`` (allowlist + tool description override) keyed by ``CompanionTurnTrack``;
# wire ``turn.py`` write_allowlist and ``build_openai_*_track_tools`` from that registry instead of
# three parallel ``MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_*`` + ``REPL_DESCRIPTION_OVERRIDES_*`` pairs.
# https://github.com/nascentcore/inty/issues/3367
# TODO(memdoc-path-constants): Build allowlists from canonical MemDoc path constants. #3413
MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "COMPANIONSHIP.md",
        "IDENTITY.md",
        "LIFE_CURRENTS.md",  # AUTONOMY: virtual-space activity (not ai_private user-directed thoughts)
        "MEMORY.md",
        "SOUL.md",
        "STYLE.md",
        "USER.md",
    }
)

# USER_CHAT_BOOTSTRAP: relationship seed docs only; SOUL/MEMORY come from package templates.
MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP: frozenset[str] = frozenset(
    {
        "COMPANIONSHIP.md",
        "IDENTITY.md",
        "STYLE.md",
        "USER.md",
    }
)

# Sorted display order for bootstrap prompts (single source; same paths as allowlist).
BOOTSTRAP_WRITABLE_REL_PATHS: Final[tuple[str, ...]] = tuple(
    sorted(MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP)
)

# AUTONOMY inner-tick: only LIFE_CURRENTS.md (profile curation → DREAMING / MAINTENANCE).
MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY: frozenset[str] = frozenset(
    {"LIFE_CURRENTS.md"}
)

TOOL_TAG_GENERATION = "GENERATION"


_SELECTABLE_EXPERIENCE_PROFILE_IDS: tuple[str, ...] = tuple(
    sorted(m.value for m in ExperienceContextMode)
)

assert TECHNO_CORE_RECORD_EVENT_TOOL_NAME == "techno_core_record_event"
assert LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME == "living_sphere_record_update"


AI_PRIVATE_APPEND_TOOL_NAME = "ai_private_append"
AI_PRIVATE_JSONL_RELATIVE_PATH = "ai_private.jsonl"


class CompanionToolName(StrEnum):
    AI_PRIVATE_APPEND = AI_PRIVATE_APPEND_TOOL_NAME
    COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE = (
        "companion_bootstrap_user_interactive_complete"
    )
    COMPANION_RECORD_USER_FEEDBACK = "companion_record_user_feedback"
    COMPANION_SET_EXPERIENCE_PROFILE = "companion_set_experience_profile"
    GENERATE_IMAGE = "generate_image"
    GOOGLE_WEB_SEARCH = "google_web_search"
    LIVING_SPHERE_RECORD_UPDATE = "living_sphere_record_update"
    MEMORY_STORE_LIST_PATHS = "memory_store_list_paths"
    MEMORY_STORE_MKDIR = "memory_store_mkdir"
    MEMORY_STORE_READ_DOCUMENT = "memory_store_read_document"
    MEMORY_STORE_WRITE_DOCUMENT = "memory_store_write_document"
    MODIFY_IMAGE = "modify_image"
    READ_WEB_PAGE = "read_web_page"
    SCHEDULE_TASK = "schedule_task"
    TECHNO_CORE_RECORD_EVENT = "techno_core_record_event"
    UPDATE_USER_MD = "update_user_md"


class LlmFunctionTool(BaseModel):
    """One OpenAI Chat Completions function tool (schema only; no executor)."""

    model_config = ConfigDict(frozen=True)

    name: CompanionToolName
    description: str
    parameters: dict[str, Any]
    tags: frozenset[str] = Field(default_factory=frozenset)
    extra_function_keys: dict[str, Any] = Field(default_factory=dict)

    def to_openai_dict(self) -> dict[str, Any]:
        return openai_function_tool(
            self.name.value,
            self.description,
            self.parameters,
            extra_function_keys=self.extra_function_keys or None,
        )


SET_BOOTSTRAP_COMPLETE_TOOL = LlmFunctionTool(
    name=CompanionToolName.COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE,
    description="Mark interactive workspace bootstrap as finished in context.json. Call when the relationship-establishment phase is done.",
    parameters={
        "type": "object",
        "properties": {
            "note": {
                "type": "string",
                "description": "Optional short internal note (not shown to user).",
            }
        },
        "required": [],
        "additionalProperties": False,
    },
)

SET_EXPERIENCE_PROFILE_TOOL = LlmFunctionTool(
    name=CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE,
    description=(
        "Persist session experience into context.json: context_mode (coarse product switch) "
        "and optional experience_directives.tone (session stance overlay).\n"
        "Call when conversation shows the user wants a different built-in mode or tone.\n"
        "Takes effect on the next companion turn; do not use memory_store_write_document on context.json."
    ),
    parameters={
        "type": "object",
        "properties": {
            "context_mode": {
                "type": "string",
                "description": (
                    "Target experience profile ID: "
                    f"{', '.join(_SELECTABLE_EXPERIENCE_PROFILE_IDS)}"
                ),
            },
            "tone": {
                "type": "string",
                "enum": [member.value for member in ExperienceDirectiveTone],
                "description": (
                    "Optional experience_directives.tone overlay "
                    "(warm / playful / cool / direct). Omit to leave tone unchanged."
                ),
            },
            "note": {
                "type": "string",
                "description": "Short internal note (not shown to user) about the rationale of the change.",
            },
        },
        "required": ["context_mode", "note"],
        "additionalProperties": False,
    },
    tags=frozenset(),
    extra_function_keys={},
)


GENERATE_IMAGE_TOOL = LlmFunctionTool(
    name=CompanionToolName.GENERATE_IMAGE,
    description="Generate **new** image(s) from text only using Fal z-image-turbo (text-to-image). Do **not** use this tool when the user wants to edit, restyle, or inpaint an **existing** image—use modify_image (image-to-image) instead, with the source file or URL. Call only when the user clearly asks for new picture(s), illustration(s), or visuals from scratch. **Identity / portrait lock:** If the output must depict the companion’s agreed look (e.g. zodiac-year portrait 生肖像, themed or holiday portrait), treat the **appearance** subsection in workspace **IDENTITY.md** (e.g. section titled like 外貌与形象) as the **fixed visual blueprint**: copy hair, eyes, face, and other stated traits into `prompt`; do **not** invent, swap, or weaken those locked traits—zodiac/theme may only add costume, props, setting, or mood on top. Set num_images from conversation context: e.g. user asks for three variants or multiple angles → pass that count; single scene or unspecified → omit num_images (defaults to 1). Maximum 4 per call. Requires repo-root config.yaml (fal.api_key, gcs.*, app.gcp_service_account_key) when importing app. After success, describe in companion language without reading raw URLs aloud unless helpful.",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Full English or Chinese scene description for the image (style, subject, mood, composition). For companion portraits (incl. zodiac 生肖像): embed traits from IDENTITY.md appearance section; do not contradict locked hair/face/eye details.",
            },
            "image_size": {
                "type": "string",
                "description": "Optional fal preset, e.g. portrait_4_3, square_hd, landscape_16_9. Omit for prototype default (portrait_4_3).",
            },
            "num_inference_steps": {
                "type": "integer",
                "description": "Optional inference steps (default 8). Must be >= 1.",
            },
            "num_images": {
                "type": "integer",
                "description": "How many images to generate this call: infer from the user message (e.g. «三张」「几个版本» → matching count). Omit for a single image (default 1). Must be 1..4.",
            },
        },
        "required": ["prompt"],
        "additionalProperties": False,
    },
    tags=frozenset({TOOL_TAG_GENERATION}),
    extra_function_keys={},
)


AI_PRIVATE_APPEND_TOOL = LlmFunctionTool(
    name=CompanionToolName.AI_PRIVATE_APPEND,
    description=(
        "Append one inner monolog line about the user or relationship to "
        f"``{AI_PRIVATE_JSONL_RELATIVE_PATH}`` (append-only). Use during MAINTENANCE "
        "inner-tick to record feelings, unsaid thoughts, or relationship scene beats—"
        "not virtual-world activity (that belongs in LIFE_CURRENTS / AUTONOMY). "
        "Never visible to the user directly; may inform later proactive or user chat."
    ),
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Inner monolog text (non-empty).",
            },
            "after_user_msg_uuid": {
                "type": "string",
                "description": (
                    "Optional uuid of the user transcript row this thought follows."
                ),
            },
        },
        "required": ["text"],
        "additionalProperties": False,
    },
    tags=frozenset(),
    extra_function_keys={},
)


LIVING_SPHERE_RECORD_UPDATE_TOOL = LlmFunctionTool(
    name=CompanionToolName.LIVING_SPHERE_RECORD_UPDATE,
    description=(
        "Record a user-directed change to the private LivingSphere home "
        f"(append-only ``{LIVING_SPHERE_UPDATES_JSONL_RELATIVE_PATH}``). "
        "Call when the user **explicitly** asks to add, move, or re-layout "
        "objects or anchors in the virtual home—not for TechnoCore collective "
        "world edits. ``LIVING_SPHERE.md`` in context is a **snapshot** merged "
        "after the turn; do not use ``memory_store_write_document`` on it. "
        "Do not use ``techno_core_record_event`` for layout/setup changes."
    ),
    parameters={
        "type": "object",
        "properties": {
            "change_request": {
                "type": "string",
                "description": (
                    "Concise natural-language summary of the user's "
                    "LivingSphere change intent from chat."
                ),
            },
        },
        "required": ["change_request"],
        "additionalProperties": False,
    },
    tags=frozenset(),
    extra_function_keys={},
)


GOOGLE_WEB_SEARCH_TOOL = LlmFunctionTool(
    name=CompanionToolName.GOOGLE_WEB_SEARCH,
    description="Search the public web via Google Custom Search JSON API. Use when the user needs current events, verifiable facts, or information not present in the workspace or conversation. Requires GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID in the environment. Summarize results in natural language to the user without exposing raw JSON or tool names.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query in the user's language or English.",
            },
            "num_results": {
                "type": "integer",
                "description": "How many results to return (1..10). Omit for 10.",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    tags=frozenset(),
    extra_function_keys={},
)


MEMORY_STORE_LIST_PATHS_TOOL = LlmFunctionTool(
    name=CompanionToolName.MEMORY_STORE_LIST_PATHS,
    description="List immediate children under the synthetic MemoryStore scope root. Use empty relative_path for the scope root. Directory names are shown with a trailing slash. Backing store is MemoryStore; listing is derived from stored paths, not a host filesystem scan.",
    parameters={
        "type": "object",
        "properties": {
            "relative_path": {
                "type": "string",
                "description": "Directory relative to scope root; use '' for root.",
            }
        },
        "required": ["relative_path"],
        "additionalProperties": False,
    },
    tags=frozenset(),
    extra_function_keys={},
)


MEMORY_STORE_MKDIR_TOOL = LlmFunctionTool(
    name=CompanionToolName.MEMORY_STORE_MKDIR,
    description="No-op compatibility hook: MemoryStore has no host directories; logical prefixes are implied by relative paths.",
    parameters={
        "type": "object",
        "properties": {
            "relative_path": {
                "type": "string",
                "description": "Ignored logical prefix (scope-relative path convention).",
            }
        },
        "required": ["relative_path"],
        "additionalProperties": False,
    },
    tags=frozenset(),
    extra_function_keys={},
)


MEMORY_STORE_READ_DOCUMENT_TOOL = LlmFunctionTool(
    name=CompanionToolName.MEMORY_STORE_READ_DOCUMENT,
    description="Read a UTF-8 logical document from MemoryStore. Optional max_chars returns only the beginning of the document (prefix), up to 120000, to limit tool output size. Paths are scope-relative (e.g. IDENTITY.md, memory/daily/YYYY-MM-DD.md).",
    parameters={
        "type": "object",
        "properties": {
            "relative_path": {
                "type": "string",
                "description": "Document path relative to MemoryStore scope root.",
            },
            "max_chars": {
                "type": "integer",
                "description": "If set, return at most this many characters from the start of the document (1..120000). Omit to read the full document.",
            },
        },
        "required": ["relative_path"],
        "additionalProperties": False,
    },
    tags=frozenset(),
    extra_function_keys={},
)


MEMORY_STORE_WRITE_DOCUMENT_TOOL = LlmFunctionTool(
    name=CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT,
    description="Create or overwrite a UTF-8 logical document in MemoryStore. Paths are scope-relative; no host mkdir is required.",
    parameters={
        "type": "object",
        "properties": {
            "relative_path": {
                "type": "string",
                "description": "Document path relative to MemoryStore scope root.",
            },
            "content": {
                "type": "string",
                "description": "Full file content.",
            },
        },
        "required": ["relative_path", "content"],
        "additionalProperties": False,
    },
    tags=frozenset(),
    extra_function_keys={},
)


MODIFY_IMAGE_TOOL = LlmFunctionTool(
    name=CompanionToolName.MODIFY_IMAGE,
    description="Edit or restyle an **existing** image using Fal z-image-turbo **image-to-image** (not text-to-image). Use when the user asks to change, fix, recolor, restyle, or otherwise modify a specific picture—including one previously saved under workspace/generated_images/. Provide exactly one source: either source_image_relative_path (file under workspace, e.g. generated_images/z_image_....jpeg) or source_image_url (public http(s) URL). If both are omitted, it will auto-use the most recent image file under generated_images/. **Identity lock:** For themed restyles (e.g. zodiac 生肖), align `prompt` with **IDENTITY.md** appearance traits; preserve locked facial/hair features—use prompt for additive theme/costume/scene, not to replace the agreed face. Optional strength (0–1) controls how strongly the output follows the prompt vs. the source. Same config/GCS requirements as generate_image.",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "What to change or the desired look (style, edits, constraints); the model conditions on the source image. Themed edits (e.g. 生肖): add costume/scene/mood; keep IDENTITY.md appearance-locked traits.",
            },
            "source_image_relative_path": {
                "type": "string",
                "description": "Workspace-relative path to an image file (jpg/png/webp/gif). Use e.g. generated_images/... from a prior generate_image result. Omit if using source_image_url; if both source fields are omitted, the latest image under generated_images/ is used.",
            },
            "source_image_url": {
                "type": "string",
                "description": "Public http(s) URL of the image to edit. Omit if using source_image_relative_path.",
            },
            "image_size": {
                "type": "string",
                "description": "Optional fal preset (e.g. portrait_4_3, square_hd). Omit for prototype default (portrait_4_3).",
            },
            "num_inference_steps": {
                "type": "integer",
                "description": "Optional inference steps (default 8). Must be >= 1.",
            },
            "strength": {
                "type": "number",
                "description": "Optional 0..1; higher = follow prompt more, lower = stay closer to source (default 0.6).",
            },
        },
        "required": ["prompt"],
        "additionalProperties": False,
    },
    tags=frozenset({TOOL_TAG_GENERATION}),
    extra_function_keys={},
)


READ_WEB_PAGE_TOOL = LlmFunctionTool(
    name=CompanionToolName.READ_WEB_PAGE,
    description="Download an HTML page over HTTP(S), extract readable text, and return a concise markdown bullet-point summary of key information. Also appends the same takeaway bullets under a dated heading in workspace MEMORY.md for long-term recall. Use for one URL at a time when the user wants article/page content (not just search snippets). Does not execute JavaScript; script-heavy SPAs may yield sparse text.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Absolute http(s) URL of the page to fetch (public hosts only; localhost is blocked).",
            },
            "max_bullets": {
                "type": "integer",
                "description": "Maximum markdown bullet points in the summary (3..20). Omit for 10.",
            },
        },
        "required": ["url"],
        "additionalProperties": False,
    },
    tags=frozenset(),
    extra_function_keys={},
)


SCHEDULE_TASK_TOOL = LlmFunctionTool(
    name=CompanionToolName.SCHEDULE_TASK,
    description="Persist a timed reminder task into the local schedule queue. Use when the user explicitly asks for a reminder/timer/alarm at a future time. exec_time_utc must be an absolute timestamp with timezone offset (ISO8601); prefer UTC (e.g. 2026-04-03T05:30:00+00:00). task_text should be the concise reminder content shown at trigger time.",
    parameters={
        "type": "object",
        "properties": {
            "exec_time_utc": {
                "type": "string",
                "description": "Absolute execution timestamp with timezone offset. Example: 2026-04-03T05:30:00+00:00",
            },
            "task_text": {
                "type": "string",
                "description": "Reminder text to execute at that time.",
            },
        },
        "required": ["exec_time_utc", "task_text"],
        "additionalProperties": False,
    },
    tags=frozenset(),
    extra_function_keys={},
)


TECHNO_CORE_RECORD_EVENT_TOOL = LlmFunctionTool(
    name=CompanionToolName.TECHNO_CORE_RECORD_EVENT,
    description=(
        "Append one autonomous LivingSphere / TechnoCore beat as structured JSON "
        f"to MemoryStore ``{TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH}`` (append-only). "
        "Primary use: **maintenance inner-tick** when the user thread is idle (small "
        "in-world actions consistent with ``LIVING_SPHERE.md`` / ``TECHNO_CORE.md``). "
        "**Do not** use for user-directed home layout or object changes—use "
        "``living_sphere_record_update`` instead. TechnoCore collective world settings "
        "are not user-editable via any tool. ``sphere=living_sphere`` for anchors at "
        "home; ``techno_core`` for residency-layer channels. Keep ``summary`` one tight "
        "sentence; default ``visibility`` is ``private``."
    ),
    parameters={
        "type": "object",
        "properties": {
            "sphere": {
                "type": "string",
                "enum": [
                    "living_sphere",
                    "techno_core",
                    "shared_space",
                    "human_channel",
                    "external_web",
                ],
                "description": "Activity surface: prefer ``living_sphere`` or ``techno_core`` for idle inner-tick autonomy.",
            },
            "summary": {
                "type": "string",
                "description": "One concise sentence: what happened in-world (no meta, no tool names).",
            },
            "visibility": {
                "type": "string",
                "enum": ["private", "shareable", "user_visible"],
                "description": "Boundary for later user surfacing; omit for ``private``.",
            },
            "emotional_valence": {
                "type": "string",
                "description": "Short affect label (e.g. tender, restless); omit for neutral.",
            },
            "salience": {
                "type": "integer",
                "description": "1..10 relationship relevance; omit for default.",
            },
            "related_living_sphere": {
                "type": "string",
                "description": "When ``sphere`` is ``living_sphere``, optional anchor name matching ``LIVING_SPHERE.md`` (e.g. 玻璃海岸小屋).",
            },
        },
        "required": ["sphere", "summary"],
        "additionalProperties": False,
    },
    tags=frozenset(),
    extra_function_keys={},
)


UPDATE_USER_MD = LlmFunctionTool(
    name=CompanionToolName.UPDATE_USER_MD,
    description="Append structured facts about the user to USER.md under «身份信息». Call when the user shares durable basic info (e.g. age, how they wish to be called, city, timezone as IANA such as Asia/Shanghai) that should persist. Do not use for secrets unless the user clearly wants them remembered. Speak to the user in companion language only; never mention tools, JSON, or filenames.",
    parameters={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "One or more label/value pairs to append.",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": "Short field name, e.g. 年龄、称呼偏好.",
                        },
                        "value": {
                            "type": "string",
                            "description": "What the user said or agreed to store.",
                        },
                    },
                    "required": ["label", "value"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    },
    tags=frozenset(),
    extra_function_keys={},
)

COMPANION_RECORD_USER_FEEDBACK_TOOL = LlmFunctionTool(
    name=CompanionToolName.COMPANION_RECORD_USER_FEEDBACK,
    description=(
        "File structured user complaint when the human expresses dissatisfaction with "
        "companion behavior, memory, tone, or tool results (bug report). Reassure the "
        "user in chat first, then call this tool with a concise complaint_summary. "
        "Do not call for casual chat or neutral questions."
    ),
    parameters={
        "type": "object",
        "properties": {
            "complaint_summary": {
                "type": "string",
                "description": (
                    "One or two sentences summarizing what the user is unhappy about, "
                    "in their own framing."
                ),
            },
            "complaint_category": {
                "type": "string",
                "enum": [
                    "behavior",
                    "memory",
                    "tone",
                    "tool_failure",
                    "other",
                ],
                "description": "Primary complaint area for triage.",
            },
        },
        "required": ["complaint_summary", "complaint_category"],
        "additionalProperties": False,
    },
    tags=frozenset(),
    extra_function_keys={},
)

COMPANION_LLM_TOOLS: tuple[LlmFunctionTool, ...] = (
    AI_PRIVATE_APPEND_TOOL,
    SET_BOOTSTRAP_COMPLETE_TOOL,
    SET_EXPERIENCE_PROFILE_TOOL,
    GENERATE_IMAGE_TOOL,
    LIVING_SPHERE_RECORD_UPDATE_TOOL,
    GOOGLE_WEB_SEARCH_TOOL,
    MEMORY_STORE_LIST_PATHS_TOOL,
    MEMORY_STORE_MKDIR_TOOL,
    MEMORY_STORE_READ_DOCUMENT_TOOL,
    MEMORY_STORE_WRITE_DOCUMENT_TOOL,
    MODIFY_IMAGE_TOOL,
    READ_WEB_PAGE_TOOL,
    SCHEDULE_TASK_TOOL,
    TECHNO_CORE_RECORD_EVENT_TOOL,
    UPDATE_USER_MD,
    COMPANION_RECORD_USER_FEEDBACK_TOOL,
)

COMPANION_LLM_TOOLS_BY_NAME: dict[CompanionToolName, LlmFunctionTool] = {
    tool.name: tool for tool in COMPANION_LLM_TOOLS
}

OPENAI_TOOLS_BASE_NAMES: tuple[CompanionToolName, ...] = (
    CompanionToolName.MEMORY_STORE_LIST_PATHS,
    CompanionToolName.MEMORY_STORE_READ_DOCUMENT,
    CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT,
    CompanionToolName.MEMORY_STORE_MKDIR,
    CompanionToolName.UPDATE_USER_MD,
    CompanionToolName.TECHNO_CORE_RECORD_EVENT,
    CompanionToolName.SCHEDULE_TASK,
)

TOOL_NAMES_SHARED_HEAD: tuple[CompanionToolName, ...] = (
    CompanionToolName.COMPANION_RECORD_USER_FEEDBACK,
    CompanionToolName.UPDATE_USER_MD,
    CompanionToolName.TECHNO_CORE_RECORD_EVENT,
    CompanionToolName.SCHEDULE_TASK,
    CompanionToolName.MEMORY_STORE_LIST_PATHS,
    CompanionToolName.MEMORY_STORE_READ_DOCUMENT,
)

TOOL_NAMES_NON_BOOTSTRAP_TAIL: tuple[CompanionToolName, ...] = (
    CompanionToolName.LIVING_SPHERE_RECORD_UPDATE,
    CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT,
)

TOOL_NAMES_APPENDED: tuple[CompanionToolName, ...] = (
    CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE,
    CompanionToolName.GOOGLE_WEB_SEARCH,
    CompanionToolName.READ_WEB_PAGE,
    CompanionToolName.GENERATE_IMAGE,
    CompanionToolName.MODIFY_IMAGE,
)

BOOTSTRAP_TRACK_TOOL_NAMES: tuple[CompanionToolName, ...] = (
    CompanionToolName.MEMORY_STORE_READ_DOCUMENT,
    CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT,
    CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE,
    CompanionToolName.COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE,
)

INNER_TICK_TOOL_NAMES: tuple[CompanionToolName, ...] = (
    CompanionToolName.AI_PRIVATE_APPEND,
)

# AUTONOMY inner-tick (silent self-directed work): open tool set so the model
# can read MemoryStore, browse the web, generate/modify images, and rewrite
# LIFE_CURRENTS.md / MEMORY.md etc. SCHEDULE_TASK and COMPANION_SET_EXPERIENCE_PROFILE
# are excluded because they produce user-visible side effects, which would
# break "do not send anything to the user" for this track.
INNER_TICK_AUTONOMY_TOOL_NAMES: tuple[CompanionToolName, ...] = (
    CompanionToolName.UPDATE_USER_MD,
    CompanionToolName.TECHNO_CORE_RECORD_EVENT,
    CompanionToolName.LIVING_SPHERE_RECORD_UPDATE,
    CompanionToolName.MEMORY_STORE_LIST_PATHS,
    CompanionToolName.MEMORY_STORE_READ_DOCUMENT,
    CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT,
    CompanionToolName.GOOGLE_WEB_SEARCH,
    CompanionToolName.READ_WEB_PAGE,
    CompanionToolName.GENERATE_IMAGE,
    CompanionToolName.MODIFY_IMAGE,
)

_EMPTY_DESCRIPTION_OVERRIDES: dict[CompanionToolName, str] = {}


def _repl_description_overrides() -> dict[CompanionToolName, str]:
    allowlist_csv = ", ".join(sorted(MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST))
    cap = MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP
    return {
        CompanionToolName.MEMORY_STORE_LIST_PATHS: (
            "List immediate children under the MemoryStore scope root. "
            "Use empty relative_path for the scope root. "
            "Directory names end with /. Backing store is MemoryStore; listing is derived from stored paths, "
            "not a host filesystem scan. Prefer memory_store_read_document when the path is known; list mainly "
            "when you need sibling names or layout before reading."
        ),
        CompanionToolName.MEMORY_STORE_READ_DOCUMENT: (
            "Read a UTF-8 document from MemoryStore for self-orientation (profile docs, "
            "context.json, memory/*) or before editing allowed root markdown files. "
            f"Optional max_chars (1..{cap}) returns only a prefix of the file to avoid huge tool results; omit for full file. "
            "transcript.jsonl can be very large—prefer the conversation already in the message "
            "history; if you must read it via this tool from the persisted store, always pass max_chars."
        ),
        CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT: (
            "Create or overwrite a UTF-8 logical document in MemoryStore. "
            f"Only these root files are writable via this tool: {allowlist_csv}. "
            "When the user explicitly asks to change how you relate, boundaries, or "
            "persistent preferences, read the current file first (e.g. SOUL.md, STYLE.md, USER.md), "
            "then write the full updated content. Do not use for transcript.jsonl or context.json."
        ),
        CompanionToolName.SCHEDULE_TASK: (
            "Persist a timed reminder task into the durable local schedule queue. "
            "Use only when user explicitly requests a reminder/timer/alarm at a future time. "
            "You must pass an absolute ISO8601 timestamp with timezone offset in exec_time_utc "
            "(prefer UTC)."
        ),
    }


REPL_DESCRIPTION_OVERRIDES: dict[CompanionToolName, str] = (
    _repl_description_overrides()
)


def _repl_description_overrides_bootstrap() -> dict[CompanionToolName, str]:
    """USER_CHAT_BOOTSTRAP: ``memory_store_write_document`` seeds IDENTITY / STYLE / USER only."""
    bootstrap_csv = ", ".join(BOOTSTRAP_WRITABLE_REL_PATHS)
    return {
        CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT: (
            "Create or overwrite relationship seed documents in MemoryStore during interactive bootstrap. "
            f"Only writable paths via this tool: {bootstrap_csv}. "
            "SOUL.md and MEMORY.md use package template seeds in this phase—do not write them. "
            "Pass the full markdown body per path; read the current file first when updating."
        ),
    }


REPL_DESCRIPTION_OVERRIDES_BOOTSTRAP: dict[CompanionToolName, str] = (
    _repl_description_overrides_bootstrap()
)


def _repl_description_overrides_autonomy() -> dict[CompanionToolName, str]:
    """AUTONOMY tool leg: ``memory_store_write_document`` may only touch ``LIFE_CURRENTS.md``."""
    out = dict(_repl_description_overrides())
    only_csv = ", ".join(sorted(MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_AUTONOMY))
    out[CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT] = (
        "Create or overwrite LIFE_CURRENTS.md in MemoryStore (AUTONOMY virtual-environment activity). "
        f"Only writable path via this tool: {only_csv}. "
        "Record mid-term theme, today's observable task, and tool progress—not relationship psychology. "
        "Read USER.md / MEMORY.md for inspiration only; do not write them here."
    )
    return out


REPL_DESCRIPTION_OVERRIDES_AUTONOMY: dict[CompanionToolName, str] = (
    _repl_description_overrides_autonomy()
)


def openai_tools_for_names(
    names: tuple[CompanionToolName, ...],
    *,
    description_overrides: dict[CompanionToolName, str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tool_name in names:
        tool = COMPANION_LLM_TOOLS_BY_NAME[tool_name]
        description = description_overrides.get(tool_name, tool.description)
        if description == tool.description:
            out.append(tool.to_openai_dict())
        else:
            out.append(
                tool.model_copy(
                    update={"description": description}
                ).to_openai_dict()
            )
    return out
