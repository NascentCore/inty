"""Companion LLM function-tool definitions for OpenAI Chat Completions.

Schema single source for companion harness tools. Execution lives in
``companion_tool_runtime`` (``_dispatch`` / ``execute_tool_call``).

New tool checklist:
1. Add ``CompanionToolName`` member
2. Add ``LlmFunctionTool`` to ``COMPANION_LLM_TOOLS``
3. Update REPL / inner-tick name tuples if the tool appears there
4. Add ``_dispatch`` branch in ``companion_tool_runtime``
5. Run ``test_companion_tool_definitions.py``
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.companion_harness.companion.prompt_slices import (
    PROMPT_SLICE_TO_REL,
)
from app.core.companion_harness.tools.openai_tools_prepare import (
    openai_function_tool,
)
from living_sphere.models import (
    LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME,
    LIVING_SPHERE_UPDATES_JSONL_RELATIVE_PATH,
)
from techno_core.models import (
    TECHNO_CORE_EVENTS_JSONL_RELATIVE_PATH,
    TECHNO_CORE_RECORD_EVENT_TOOL_NAME,
)

MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP: int = 120_000

MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "IDENTITY.md",
        "MEMORY.md",
        "SOUL.md",
        "STYLE.md",
        "USER.md",
    }
)

TOOL_TAG_GENERATION = "GENERATION"


_PROMPT_SLICE_ENUM: tuple[str, ...] = tuple(
    sorted(s.value for s in PROMPT_SLICE_TO_REL)
)

assert TECHNO_CORE_RECORD_EVENT_TOOL_NAME == "techno_core_record_event"
assert LIVING_SPHERE_RECORD_UPDATE_TOOL_NAME == "living_sphere_record_update"


class CompanionToolName(StrEnum):
    COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE = (
        "companion_bootstrap_user_interactive_complete"
    )
    COMPANION_RUNTIME_INSPECT = "companion_runtime_inspect"
    COMPANION_SET_EXPERIENCE_PROFILE = "companion_set_experience_profile"
    COMPANION_UPDATE_PROMPT_SLICE = "companion_update_prompt_slice"
    GENERATE_IMAGE = "generate_image"
    GOOGLE_WEB_SEARCH = "google_web_search"
    LIVING_SPHERE_RECORD_UPDATE = "living_sphere_record_update"
    MEMORY_STORE_LIST_PATHS = "memory_store_list_paths"
    MEMORY_STORE_MKDIR = "memory_store_mkdir"
    MEMORY_STORE_READ_DOCUMENT = "memory_store_read_document"
    MEMORY_STORE_WRITE_DOCUMENT = "memory_store_write_document"
    MODIFY_IMAGE = "modify_image"
    PHONE_CALL_USER = "phone_call_user"
    READ_WEB_PAGE = "read_web_page"
    SCHEDULE_TASK = "schedule_task"
    SYNTHESIZE_CHAT_MESSAGE_VOICE = "synthesize_chat_message_voice"
    TECHNO_CORE_RECORD_EVENT = "techno_core_record_event"
    TOOL_UPDATE_AGENT_STATUS_LINE = "tool_update_agent_status_line"
    USER_PROFILE_RECORD = "user_profile_record"


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


COMPANION_LLM_TOOLS: tuple[LlmFunctionTool, ...] = (
    LlmFunctionTool(
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
        tags=frozenset(),
        extra_function_keys={},
    ),
    LlmFunctionTool(
        name=CompanionToolName.COMPANION_RUNTIME_INSPECT,
        description="Return a JSON snapshot of the current companion runtime: in-process LLM config, last chat.completions request (model, messages, tools_summary, OpenRouter extra kwargs), runtime events, and optionally workspace documents from MemoryStore (SOUL, STYLE, USER, MEMORY.md, episodic/gist day paths). Use when the user asks for verifiable facts about the active model, parameters, or injected prompt stack. For self-check only: answer the user in natural language without reading this JSON aloud verbatim.",
        parameters={
            "type": "object",
            "properties": {
                "max_chars_per_doc": {
                    "type": "integer",
                    "description": "Max characters per stored document body (default 8000, min 100).",
                },
                "max_chars_llm_messages": {
                    "type": "integer",
                    "description": "Max serialized size for last request messages array (default 120000, min 1000).",
                },
                "include_store_documents": {
                    "type": "boolean",
                    "description": "If false, omit MemoryStore document bodies (default true).",
                },
                "max_runtime_events": {
                    "type": "integer",
                    "description": "Max newest runtime event records to include (default 20, min 0).",
                },
            },
            "required": [],
            "additionalProperties": False,
        },
        tags=frozenset(),
        extra_function_keys={},
    ),
    LlmFunctionTool(
        name=CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE,
        description="Persist the session experience profile id into context.json as context_mode (normalized lowercase). Call only after the user explicitly agrees to switch (e.g. roleplay vs emotional companion). Requires user_confirmed=true; never infer silently. Takes effect on the next companion turn; do not use memory_store_write_document on context.json.",
        parameters={
            "type": "object",
            "properties": {
                "context_mode": {
                    "type": "string",
                    "description": "Target experience profile id (e.g. intimate, emotional_companion, roleplay, interactive_fiction, public).",
                },
                "user_confirmed": {
                    "type": "boolean",
                    "description": "Must be true only when the user clearly confirmed the mode switch in this conversation.",
                },
                "note": {
                    "type": "string",
                    "description": "Optional short internal note (not shown to user).",
                },
            },
            "required": ["context_mode", "user_confirmed"],
            "additionalProperties": False,
        },
        tags=frozenset(),
        extra_function_keys={},
    ),
    LlmFunctionTool(
        name=CompanionToolName.COMPANION_UPDATE_PROMPT_SLICE,
        description="Overwrite one workspace prompt slice (root markdown) in MemoryStore. Use during interactive relationship bootstrap instead of memory_store_write_document. Pass the full updated markdown as content. TOOLS / significance-perception operator text are fixed package templates, not slices.",
        parameters={
            "type": "object",
            "properties": {
                "slice": {
                    "type": "string",
                    "enum": list(_PROMPT_SLICE_ENUM),
                    "description": "Which prompt document to replace.",
                },
                "content": {
                    "type": "string",
                    "description": "Full UTF-8 body to write for that slice.",
                },
            },
            "required": ["slice", "content"],
            "additionalProperties": False,
        },
        tags=frozenset(),
        extra_function_keys={},
    ),
    LlmFunctionTool(
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
    ),
    LlmFunctionTool(
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
    ),
    LlmFunctionTool(
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
    ),
    LlmFunctionTool(
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
    ),
    LlmFunctionTool(
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
    ),
    LlmFunctionTool(
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
    ),
    LlmFunctionTool(
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
    ),
    LlmFunctionTool(
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
    ),
    LlmFunctionTool(
        name=CompanionToolName.PHONE_CALL_USER,
        description="Place an outbound phone call to the user through the configured PSTN provider. Use only when the current user message explicitly asks you to call now and provides the phone number in that same message (for example, 'Call me at 1234560123'). Never call a number inferred from memory, old messages, or guesses. Do not use from proactive/implicit greeting contexts.",
        parameters={
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "User-provided phone number from the current message.",
                },
                "reason": {
                    "type": "string",
                    "description": "Short reason for audit logs, based on the user's explicit request.",
                },
            },
            "required": ["phone_number", "reason"],
            "additionalProperties": False,
        },
        tags=frozenset(),
        extra_function_keys={},
    ),
    LlmFunctionTool(
        name=CompanionToolName.SYNTHESIZE_CHAT_MESSAGE_VOICE,
        description=(
            "Generate listenable audio for an **existing** assistant (or chat) message "
            "already stored in chat history, and persist the audio URL on that row. "
            "Uses the same TTS pipeline as the product REST endpoint for on-demand playback. "
            "Requires context.json user_id, companion_id, and (when set) chat_id matching "
            "the user's active chat for that companion. "
            "Call only when the user explicitly wants to hear a specific past message by id, "
            "or after you know the numeric message_id from tool/runtime context; "
            "do not guess ids. For a fresh reply as a voice note, prefer the dual-LLM "
            "envelope fields reply_modality / voice_message_script instead of this tool."
        ),
        parameters={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": (
                        "Persisted chat_history message primary key as string "
                        "(same as REST ``.../messages/{message_id}/voice``)."
                    ),
                },
                "language": {
                    "type": "string",
                    "description": (
                        "BCP-47 / product language code for TTS (e.g. zh, en). "
                        "Omit to default to zh."
                    ),
                },
            },
            "required": ["message_id"],
            "additionalProperties": False,
        },
        tags=frozenset(),
        extra_function_keys={},
    ),
    LlmFunctionTool(
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
    ),
    LlmFunctionTool(
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
    ),
    LlmFunctionTool(
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
    ),
    LlmFunctionTool(
        name=CompanionToolName.TOOL_UPDATE_AGENT_STATUS_LINE,
        description='Set the short one-line status shown under your name in the user\'s chat header (mood, vibe, or current thought). Use the same language as the user. Keep it brief (roughly one short sentence). Pass an empty string to clear it. Do not mention this tool or raw JSON to the user. The tool returns a single line: status line cleared, or status line updated to "..."; mirror that in your natural reply when needed.',
        parameters={
            "type": "object",
            "properties": {
                "status_line": {
                    "type": "string",
                    "description": "Header subtitle text, or empty string to clear.",
                }
            },
            "required": ["status_line"],
            "additionalProperties": False,
        },
        tags=frozenset(),
        extra_function_keys={},
    ),
    LlmFunctionTool(
        name=CompanionToolName.USER_PROFILE_RECORD,
        description="Append structured facts about the user to USER.md under «身份信息». Call when the user shares durable basic info (e.g. age, how they wish to be called, timezone) that should persist. Do not use for secrets unless the user clearly wants them remembered. Speak to the user in companion language only; never mention tools, JSON, or filenames.",
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
    ),
)

COMPANION_LLM_TOOLS_BY_NAME: dict[CompanionToolName, LlmFunctionTool] = {
    tool.name: tool for tool in COMPANION_LLM_TOOLS
}

OPENAI_TOOLS_BASE_NAMES: tuple[CompanionToolName, ...] = (
    CompanionToolName.MEMORY_STORE_LIST_PATHS,
    CompanionToolName.MEMORY_STORE_READ_DOCUMENT,
    CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT,
    CompanionToolName.MEMORY_STORE_MKDIR,
    CompanionToolName.USER_PROFILE_RECORD,
    CompanionToolName.TECHNO_CORE_RECORD_EVENT,
    CompanionToolName.SCHEDULE_TASK,
    CompanionToolName.TOOL_UPDATE_AGENT_STATUS_LINE,
    CompanionToolName.PHONE_CALL_USER,
    CompanionToolName.SYNTHESIZE_CHAT_MESSAGE_VOICE,
)

REPL_TOOL_NAMES_SHARED_HEAD: tuple[CompanionToolName, ...] = (
    CompanionToolName.USER_PROFILE_RECORD,
    CompanionToolName.TECHNO_CORE_RECORD_EVENT,
    CompanionToolName.SCHEDULE_TASK,
    CompanionToolName.TOOL_UPDATE_AGENT_STATUS_LINE,
    CompanionToolName.MEMORY_STORE_LIST_PATHS,
    CompanionToolName.MEMORY_STORE_READ_DOCUMENT,
)

REPL_TOOL_NAMES_NON_BOOTSTRAP_TAIL: tuple[CompanionToolName, ...] = (
    CompanionToolName.LIVING_SPHERE_RECORD_UPDATE,
    CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT,
    CompanionToolName.PHONE_CALL_USER,
    CompanionToolName.SYNTHESIZE_CHAT_MESSAGE_VOICE,
)

REPL_TOOL_NAMES_APPENDED: tuple[CompanionToolName, ...] = (
    CompanionToolName.COMPANION_RUNTIME_INSPECT,
    CompanionToolName.COMPANION_SET_EXPERIENCE_PROFILE,
    CompanionToolName.GOOGLE_WEB_SEARCH,
    CompanionToolName.READ_WEB_PAGE,
    CompanionToolName.GENERATE_IMAGE,
    CompanionToolName.MODIFY_IMAGE,
)

REPL_BOOTSTRAP_TOOL_NAMES: tuple[CompanionToolName, ...] = (
    CompanionToolName.COMPANION_UPDATE_PROMPT_SLICE,
    CompanionToolName.COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE,
)

INNER_TICK_TOOL_NAMES: tuple[CompanionToolName, ...] = (
    CompanionToolName.USER_PROFILE_RECORD,
    CompanionToolName.TECHNO_CORE_RECORD_EVENT,
    CompanionToolName.TOOL_UPDATE_AGENT_STATUS_LINE,
    CompanionToolName.MEMORY_STORE_LIST_PATHS,
    CompanionToolName.MEMORY_STORE_READ_DOCUMENT,
    CompanionToolName.MEMORY_STORE_WRITE_DOCUMENT,
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
