"""Workspace bootstrap 工具：仅允许在 workspace 根目录内读写（与 agentic_ai_companion 工具模式对齐）。"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import date
from pathlib import Path
from typing import Any, Callable

from app.core.agentic_kernel.tools.registry import ToolRegistry
from app.core.agentic_kernel.tools.dispatchers.media import (
    parse_optional_positive_int,
    parse_optional_strength,
)
from app.core.agentic_kernel.tools.dispatchers.workspace import (
    dispatch_workspace_tool,
)

from .fal_z_image_tool import (
    MAX_NUM_IMAGES_PER_CALL,
    _reset_fal_async_client_after_short_lived_loop,
    run_generate_image_z_image_turbo,
    run_modify_image_z_image_turbo,
)
from .file_store import read_text, write_text
from .google_web_search import run_google_web_search

_USER_MD_REL = "USER.md"
_USER_PROFILE_SECTION = "## 身份信息"

# workspace_read_file：可选 max_chars 上限，避免单次 tool 返回撑爆上下文。
WORKSPACE_READ_FILE_MAX_CHARS_CAP: int = 120_000

# REPL 对话轮允许整文件覆盖写入的相对路径（根目录约定文档；不含 transcript/context 等）
REPL_WRITABLE_RELATIVE_PATHS: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "CAPABILITIES.md",
        "HEARTBEAT.md",
        "IDENTITY.md",
        "MEMORY.md",
        "SOUL.md",
        "TOOLS.md",
        "USER.md",
    }
)


_BASE_TOOL_REGISTRY = ToolRegistry(
    (
        "workspace_list_dir",
        "workspace_read_file",
        "workspace_write_file",
        "workspace_mkdir",
        "user_profile_record",
        "google_web_search",
        "generate_image",
        "modify_image",
    )
)


def openai_assistant_message_dict(msg: Any) -> dict[str, Any]:
    """将 chat.completions assistant message 转为可回注 messages 列表的 dict（含 tool_calls）。"""
    raw_tool_calls = getattr(msg, "tool_calls", None)
    out: dict[str, Any] = {
        "role": "assistant",
        "content": msg.content if msg.content is not None else "",
    }
    if not raw_tool_calls:
        return out
    tool_calls: list[dict[str, Any]] = []
    for tc in raw_tool_calls:
        fn = tc.function
        tool_calls.append(
            {
                "id": tc.id,
                "type": getattr(tc, "type", "function"),
                "function": {
                    "name": fn.name,
                    "arguments": fn.arguments if fn.arguments is not None else "",
                },
            }
        )
    out["tool_calls"] = tool_calls
    return out


def append_user_profile_facts_to_user_md(text: str, new_bullets: list[str]) -> str:
    """
    在 USER.md 的「身份信息」小节追加条目；若尚无该小节则在文末追加。
    new_bullets 每项应为完整一行（含前导 `- `）。
    """
    lines = text.splitlines()
    if _USER_PROFILE_SECTION not in lines:
        block = "\n\n" + _USER_PROFILE_SECTION + "\n\n" + "\n".join(new_bullets)
        return text.rstrip() + block + "\n"
    idx = lines.index(_USER_PROFILE_SECTION)
    j = idx + 1
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    insert_at = j
    while insert_at < len(lines) and not lines[insert_at].startswith("## "):
        insert_at += 1
    for k, b in enumerate(new_bullets):
        lines.insert(insert_at + k, b)
    return "\n".join(lines) + "\n"


def tool_user_profile_record(root: Path, items: list[dict[str, Any]]) -> str:
    """
    将用户自愿透露的基本信息追加写入 USER.md 的「身份信息」小节。
    items：每项含 label、value（均为非空短文本）。
    """
    p = resolve_under_workspace(root, _USER_MD_REL)
    if not p.is_file():
        return f"ERROR: missing {_USER_MD_REL!r}"
    today = date.today().isoformat()
    bullets: list[str] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("label", "")).strip()
        value = str(raw.get("value", "")).strip()
        if not label or not value:
            continue
        bullets.append(f"- {label}：{value}（记录日期 {today}）")
    if not bullets:
        return "ERROR: no valid items (need label and value for each entry)"
    prev = read_text(p)
    merged = append_user_profile_facts_to_user_md(prev, bullets)
    write_text(p, merged)
    return f"OK appended {len(bullets)} line(s) to {_USER_MD_REL}"


def resolve_under_workspace(root: Path, relative_path: str) -> Path:
    """
    将相对路径解析为绝对路径；禁止逃出 workspace。
    空字符串表示 workspace 根目录。
    """
    root = root.resolve()
    rel = (relative_path or "").strip().replace("\\", "/")
    if rel.startswith("/"):
        raise ValueError("path must be relative to workspace root")
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes workspace root") from exc
    return candidate


def tool_workspace_list_dir(root: Path, relative_path: str) -> str:
    """列出目录下的直接子项（文件与目录名）；目录名以 / 结尾。"""
    d = resolve_under_workspace(root, relative_path)
    if not d.is_dir():
        return f"ERROR: not a directory: {relative_path!r}"
    names = sorted(d.iterdir(), key=lambda p: p.name.lower())
    lines: list[str] = []
    for p in names:
        if p.name.startswith("."):
            continue
        lines.append(f"{p.name}/" if p.is_dir() else p.name)
    return "\n".join(lines) if lines else "(empty)"


def _parse_optional_max_chars(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        raise ValueError("max_chars must be a positive integer or omitted")
    n: int
    if isinstance(raw, int):
        n = raw
    elif isinstance(raw, float) and raw.is_integer():
        n = int(raw)
    else:
        raise ValueError("max_chars must be a positive integer or omitted")
    if n < 1:
        raise ValueError("max_chars must be at least 1")
    if n > WORKSPACE_READ_FILE_MAX_CHARS_CAP:
        raise ValueError(
            f"max_chars must be at most {WORKSPACE_READ_FILE_MAX_CHARS_CAP}"
        )
    return n


def tool_workspace_read_file(
    root: Path, relative_path: str, max_chars: int | None = None
) -> str:
    p = resolve_under_workspace(root, relative_path)
    if not p.is_file():
        return f"ERROR: not a file: {relative_path!r}"
    body = read_text(p)
    if max_chars is None:
        return body
    if len(body) <= max_chars:
        return body
    return (
        body[:max_chars] + "\n…[truncated: prefix only; file is longer than max_chars]"
    )


def tool_workspace_write_file(root: Path, relative_path: str, content: str) -> str:
    p = resolve_under_workspace(root, relative_path)
    write_text(p, content)
    return f"OK wrote {len(content)} chars to {relative_path}"


def tool_workspace_mkdir(root: Path, relative_path: str) -> str:
    p = resolve_under_workspace(root, relative_path)
    p.mkdir(parents=True, exist_ok=True)
    return f"OK mkdir {relative_path}"


def build_openai_tools() -> list[dict[str, Any]]:
    """OpenAI Chat Completions `tools` 列表。"""
    return [
        {
            "type": "function",
            "function": {
                "name": "workspace_list_dir",
                "description": (
                    "List immediate children of a directory under the workspace root. "
                    "Use empty relative_path for the workspace root. "
                    "Directory names are shown with a trailing slash."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "Directory relative to workspace; use '' for root.",
                        },
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "workspace_read_file",
                "description": (
                    "Read a UTF-8 text file under the workspace. "
                    "Optional max_chars returns only the beginning of the file (prefix), "
                    f"up to {WORKSPACE_READ_FILE_MAX_CHARS_CAP}, to limit tool output size."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "File path relative to workspace root.",
                        },
                        "max_chars": {
                            "type": "integer",
                            "description": (
                                "If set, return at most this many characters from the start of the file "
                                f"(1..{WORKSPACE_READ_FILE_MAX_CHARS_CAP}). Omit to read the full file."
                            ),
                        },
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "workspace_write_file",
                "description": (
                    "Create or overwrite a UTF-8 text file under the workspace. "
                    "Creates parent directories as needed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "File path relative to workspace root.",
                        },
                        "content": {
                            "type": "string",
                            "description": "Full file content.",
                        },
                    },
                    "required": ["relative_path", "content"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "workspace_mkdir",
                "description": "Create a directory under the workspace (mkdir -p).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "Directory path relative to workspace root.",
                        },
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "user_profile_record",
                "description": (
                    "Append structured facts about the user to USER.md under «身份信息». "
                    "Call when the user shares durable basic info (e.g. age, how they wish to be called, "
                    "timezone) that should persist. Do not use for secrets unless the user clearly wants "
                    "them remembered. Speak to the user in companion language only; never mention tools, "
                    "JSON, or filenames."
                ),
                "parameters": {
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
                        },
                    },
                    "required": ["items"],
                    "additionalProperties": False,
                },
            },
        },
    ]


def build_openai_repl_tools() -> list[dict[str, Any]]:
    """
    REPL 对话轮：用户档案追加 + 工作区文档读写（写入仅限 REPL_WRITABLE_RELATIVE_PATHS）。
    """
    full = build_openai_tools()
    by_name = {
        t["function"]["name"]: t
        for t in full
        if t.get("type") == "function" and "function" in t
    }
    names = (
        "user_profile_record",
        "workspace_list_dir",
        "workspace_read_file",
        "workspace_write_file",
    )
    out: list[dict[str, Any]] = []
    for n in names:
        t = by_name.get(n)
        if not t:
            raise KeyError(f"missing tool definition: {n!r}")
        if n == "workspace_list_dir":
            w = dict(t)
            wfn = dict(w["function"])
            wfn["description"] = (
                "List immediate children under the workspace root. "
                "Use empty relative_path for the workspace root. "
                "Directory names end with /. You may explore subdirectories (e.g. memory/) "
                "to understand layout and workspace conventions before reading files."
            )
            w["function"] = wfn
            out.append(w)
        elif n == "workspace_read_file":
            w = dict(t)
            wfn = dict(w["function"])
            wfn["description"] = (
                "Read a UTF-8 file under the workspace for self-orientation (workspace docs, "
                "context.json, memory/*) or before editing allowed root markdown files. "
                "Optional max_chars (1.."
                + str(WORKSPACE_READ_FILE_MAX_CHARS_CAP)
                + ") returns only a prefix of the file to avoid huge tool results; omit for full file. "
                "transcript.jsonl can be very large—prefer the conversation already in the message "
                "history; if you must read it from disk, always pass max_chars."
            )
            w["function"] = wfn
            out.append(w)
        elif n == "workspace_write_file":
            w = dict(t)
            wfn = dict(w["function"])
            wfn["description"] = (
                "Create or overwrite a UTF-8 text file under the workspace. "
                "In REPL, only these root files are writable: "
                + ", ".join(sorted(REPL_WRITABLE_RELATIVE_PATHS))
                + ". When the user explicitly asks to change how you relate, boundaries, or "
                "persistent preferences, read the current file first (e.g. SOUL.md, USER.md), "
                "then write the full updated content. Do not use for transcript.jsonl or context.json."
            )
            w["function"] = wfn
            out.append(w)
        else:
            out.append(t)
    out.append(
        {
            "type": "function",
            "function": {
                "name": "google_web_search",
                "description": (
                    "Search the public web via Google Custom Search JSON API. "
                    "Use when the user needs current events, verifiable facts, or information "
                    "not present in the workspace or conversation. "
                    "Requires GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID in the environment. "
                    "Summarize results in natural language to the user without exposing raw JSON or tool names."
                ),
                "parameters": {
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
            },
        }
    )
    out.append(
        {
            "type": "function",
            "function": {
                "name": "generate_image",
                "description": (
                    "Generate **new** image(s) from text only using Fal z-image-turbo (text-to-image). "
                    "Do **not** use this tool when the user wants to edit, restyle, or inpaint an **existing** image—"
                    "use modify_image (image-to-image) instead, with the source file or URL. "
                    "Call only when the user clearly asks for new picture(s), illustration(s), or visuals from scratch. "
                    "**Identity / portrait lock:** If the output must depict the companion’s agreed look "
                    "(e.g. zodiac-year portrait 生肖像, themed or holiday portrait), treat the **appearance** subsection "
                    "in workspace **IDENTITY.md** (e.g. section titled like 外貌与形象) as the **fixed visual blueprint**: "
                    "copy hair, eyes, face, and other stated traits into `prompt`; do **not** invent, swap, or weaken "
                    "those locked traits—zodiac/theme may only add costume, props, setting, or mood on top. "
                    "Set num_images from conversation context: e.g. user asks for three variants or "
                    "multiple angles → pass that count; single scene or unspecified → omit num_images "
                    f"(defaults to 1). Maximum {MAX_NUM_IMAGES_PER_CALL} per call. "
                    "Requires repo-root config.yaml (fal.api_key, gcs.*, app.gcp_service_account_key) when importing app. "
                    "After success, describe in companion language without reading raw URLs aloud unless helpful."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": (
                                "Full English or Chinese scene description for the image "
                                "(style, subject, mood, composition). "
                                "For companion portraits (incl. zodiac 生肖像): embed traits from IDENTITY.md "
                                "appearance section; do not contradict locked hair/face/eye details."
                            ),
                        },
                        "image_size": {
                            "type": "string",
                            "description": (
                                "Optional fal preset, e.g. portrait_4_3, square_hd, landscape_16_9. "
                                "Omit for prototype default (portrait_4_3)."
                            ),
                        },
                        "num_inference_steps": {
                            "type": "integer",
                            "description": "Optional inference steps (default 8). Must be >= 1.",
                        },
                        "num_images": {
                            "type": "integer",
                            "description": (
                                "How many images to generate this call: infer from the user message "
                                "(e.g. «三张」「几个版本» → matching count). Omit for a single image (default 1). "
                                f"Must be 1..{MAX_NUM_IMAGES_PER_CALL}."
                            ),
                        },
                    },
                    "required": ["prompt"],
                    "additionalProperties": False,
                },
            },
        }
    )
    out.append(
        {
            "type": "function",
            "function": {
                "name": "modify_image",
                "description": (
                    "Edit or restyle an **existing** image using Fal z-image-turbo **image-to-image** "
                    "(not text-to-image). Use when the user asks to change, fix, recolor, restyle, or otherwise "
                    "modify a specific picture—including one previously saved under workspace/generated_images/. "
                    "Provide exactly one source: either source_image_relative_path (file under workspace, e.g. "
                    "generated_images/z_image_....jpeg) or source_image_url (public http(s) URL). "
                    "**Identity lock:** For themed restyles (e.g. zodiac 生肖), align `prompt` with **IDENTITY.md** "
                    "appearance traits; preserve locked facial/hair features—use prompt for additive theme/costume/scene, "
                    "not to replace the agreed face. "
                    "Optional strength (0–1) controls how strongly the output follows the prompt vs. the source. "
                    "Same config/GCS requirements as generate_image."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": (
                                "What to change or the desired look (style, edits, constraints); "
                                "the model conditions on the source image. "
                                "Themed edits (e.g. 生肖): add costume/scene/mood; keep IDENTITY.md appearance-locked traits."
                            ),
                        },
                        "source_image_relative_path": {
                            "type": "string",
                            "description": (
                                "Workspace-relative path to an image file (jpg/png/webp/gif). "
                                "Use e.g. generated_images/... from a prior generate_image result. "
                                "Omit if using source_image_url."
                            ),
                        },
                        "source_image_url": {
                            "type": "string",
                            "description": (
                                "Public http(s) URL of the image to edit. Omit if using source_image_relative_path."
                            ),
                        },
                        "image_size": {
                            "type": "string",
                            "description": (
                                "Optional fal preset (e.g. portrait_4_3, square_hd). "
                                "Omit for prototype default (portrait_4_3)."
                            ),
                        },
                        "num_inference_steps": {
                            "type": "integer",
                            "description": "Optional inference steps (default 8). Must be >= 1.",
                        },
                        "strength": {
                            "type": "number",
                            "description": (
                                "Optional 0..1; higher = follow prompt more, lower = stay closer to source (default 0.6)."
                            ),
                        },
                    },
                    "required": ["prompt"],
                    "additionalProperties": False,
                },
            },
        }
    )
    return out


def _repl_write_allowed(
    root: Path, relative_path: str, write_allowlist: frozenset[str]
) -> str | None:
    """若不允许写入则返回错误信息字符串，否则 None。"""
    p = resolve_under_workspace(root, relative_path)
    rel_posix = p.relative_to(root.resolve()).as_posix()
    if rel_posix not in write_allowlist:
        return (
            "ERROR: REPL workspace_write_file only allows: "
            + ", ".join(sorted(write_allowlist))
            + f"; got {rel_posix!r}"
        )
    return None


async def _dispatch(
    root: Path,
    name: str,
    arguments: dict[str, Any],
    *,
    write_allowlist: frozenset[str] | None = None,
) -> str:
    if not _BASE_TOOL_REGISTRY.is_allowed(name):
        return f"ERROR: unknown tool {name!r}"

    workspace_dispatch_result = dispatch_workspace_tool(
        root=root,
        name=name,
        arguments=arguments,
        write_allowlist=write_allowlist,
        tool_workspace_list_dir=tool_workspace_list_dir,
        tool_workspace_read_file=tool_workspace_read_file,
        tool_workspace_write_file=tool_workspace_write_file,
        tool_workspace_mkdir=tool_workspace_mkdir,
        tool_user_profile_record=tool_user_profile_record,
        parse_optional_max_chars=_parse_optional_max_chars,
        repl_write_allowed=_repl_write_allowed,
    )
    if workspace_dispatch_result is not None:
        return workspace_dispatch_result
    if name == "google_web_search":
        raw_q = arguments.get("query")
        if not isinstance(raw_q, str):
            return "ERROR: query must be a string"
        n_raw = arguments.get("num_results")
        n_opt: int | None
        if n_raw is None:
            n_opt = None
        elif isinstance(n_raw, bool):
            return "ERROR: num_results must be a positive integer or omitted"
        elif isinstance(n_raw, int):
            n_opt = n_raw
        elif isinstance(n_raw, float) and n_raw.is_integer():
            n_opt = int(n_raw)
        else:
            return "ERROR: num_results must be a positive integer or omitted"
        return await run_google_web_search(query=raw_q, num_results=n_opt)
    if name == "generate_image":
        prompt = arguments.get("prompt")
        if not isinstance(prompt, str):
            return "ERROR: prompt must be a string"
        if not prompt.strip():
            return "ERROR: prompt must be non-empty"
        image_size = arguments.get("image_size")
        if image_size is not None and not isinstance(image_size, str):
            return "ERROR: image_size must be a string or omitted"
        image_size_s = image_size.strip() if isinstance(image_size, str) else None
        if image_size_s == "":
            image_size_s = None
        n_steps, err = parse_optional_positive_int(
            arguments.get("num_inference_steps"), field_name="num_inference_steps"
        )
        if err:
            return f"ERROR: {err}"
        n_img, err2 = parse_optional_positive_int(
            arguments.get("num_images"), field_name="num_images"
        )
        if err2:
            return f"ERROR: {err2}"
        if n_img is not None and n_img > MAX_NUM_IMAGES_PER_CALL:
            return (
                "ERROR: num_images must be at most "
                f"{MAX_NUM_IMAGES_PER_CALL} per generate_image call"
            )
        from loguru import logger

        t_img = time.perf_counter()
        out = await run_generate_image_z_image_turbo(
            root,
            prompt=prompt,
            image_size=image_size_s,
            num_inference_steps=n_steps,
            num_images=n_img,
        )
        logger.info(
            "tool generate_image wall_ms={:.0f} ws={} ok={}",
            (time.perf_counter() - t_img) * 1000.0,
            root.name,
            not out.startswith("ERROR:"),
        )
        return out
    if name == "modify_image":
        prompt = arguments.get("prompt")
        if not isinstance(prompt, str):
            return "ERROR: prompt must be a string"
        if not prompt.strip():
            return "ERROR: prompt must be non-empty"
        raw_path = arguments.get("source_image_relative_path")
        raw_url = arguments.get("source_image_url")
        if raw_path is not None and not isinstance(raw_path, str):
            return "ERROR: source_image_relative_path must be a string or omitted"
        if raw_url is not None and not isinstance(raw_url, str):
            return "ERROR: source_image_url must be a string or omitted"
        path_s = raw_path.strip() if isinstance(raw_path, str) else ""
        url_s = raw_url.strip() if isinstance(raw_url, str) else ""
        src_path: Path | None = None
        if path_s:
            try:
                src_path = resolve_under_workspace(root, path_s)
            except ValueError as exc:
                return f"ERROR: {exc}"
            if not src_path.is_file():
                return f"ERROR: source image not found or not a file: {path_s!r}"
        src_url_out: str | None = url_s if url_s else None
        image_size = arguments.get("image_size")
        if image_size is not None and not isinstance(image_size, str):
            return "ERROR: image_size must be a string or omitted"
        image_size_s = image_size.strip() if isinstance(image_size, str) else None
        if image_size_s == "":
            image_size_s = None
        n_steps, err = parse_optional_positive_int(
            arguments.get("num_inference_steps"), field_name="num_inference_steps"
        )
        if err:
            return f"ERROR: {err}"
        strength, err_s = parse_optional_strength(arguments.get("strength"))
        if err_s:
            return f"ERROR: {err_s}"
        from loguru import logger

        t_img = time.perf_counter()
        out = await run_modify_image_z_image_turbo(
            root,
            prompt=prompt,
            source_path=src_path,
            source_image_url=src_url_out,
            image_size=image_size_s,
            num_inference_steps=n_steps,
            strength=strength,
        )
        logger.info(
            "tool modify_image wall_ms={:.0f} ws={} ok={}",
            (time.perf_counter() - t_img) * 1000.0,
            root.name,
            not out.startswith("ERROR:"),
        )
        return out
    return f"ERROR: unknown tool {name!r}"


async def execute_tool_call(
    root: Path,
    name: str,
    arguments_json: str,
    *,
    write_allowlist: frozenset[str] | None = None,
) -> str:
    from loguru import logger

    raw = (arguments_json or "").strip()
    try:
        parsed: dict[str, Any] = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        err = f"ERROR: invalid JSON arguments: {exc}"
        logger.warning("tool {} json_error: {}", name, err)
        return err
    if not isinstance(parsed, dict):
        err = "ERROR: tool arguments must be a JSON object"
        logger.warning("tool {} {}", name, err)
        return err
    try:
        out = await _dispatch(root, name, parsed, write_allowlist=write_allowlist)
    except (OSError, ValueError) as exc:
        err = f"ERROR: {exc}"
        logger.warning("tool {} dispatch: {}", name, err)
        return err
    if out.startswith("ERROR:"):
        logger.warning("tool {} result: {}", name, out)
    else:
        logger.debug("tool {} ok ({} chars)", name, len(out))
    return out


async def _execute_tool_call_blocking_impl(
    root: Path,
    name: str,
    arguments_json: str,
    *,
    write_allowlist: frozenset[str] | None = None,
) -> str:
    """`asyncio.run` 结束前释放 fal 全局 client，避免连续多次 blocking 调用踩 closed loop。"""
    try:
        return await execute_tool_call(
            root, name, arguments_json, write_allowlist=write_allowlist
        )
    finally:
        await _reset_fal_async_client_after_short_lived_loop()


def execute_tool_call_blocking(
    root: Path,
    name: str,
    arguments_json: str,
    *,
    write_allowlist: frozenset[str] | None = None,
) -> str:
    """在无运行中 event loop 时执行工具（测试、bootstrap 的 sync 包装）。"""
    return asyncio.run(
        _execute_tool_call_blocking_impl(
            root, name, arguments_json, write_allowlist=write_allowlist
        )
    )


def tool_executor_for_root(root: Path) -> Callable[[str, str], str]:
    """返回 (name, arguments_json) -> result_str，供循环内调用。"""

    def run(name: str, arguments_json: str) -> str:
        return execute_tool_call_blocking(
            root, name, arguments_json, write_allowlist=None
        )

    return run
