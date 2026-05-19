"""复刻 app 聊天生图核心流程：提示词、双参考图、严格失败。"""

from __future__ import annotations

import base64
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from google.genai import Client

RECENT_MESSAGES_LIMIT = 10
DEFAULT_CHAT_IMAGE_MODEL = "gemini-2.5-flash-image"

_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_COMPANION_PROFILE_DIR = _THIS_DIR / "companion_profile"
DEFAULT_USER_PROFILE_DIR = _THIS_DIR / "user_profile"
DEFAULT_OUTPUT_DIR = _THIS_DIR / "tmp" / "chat_images"
DEFAULT_HISTORY_PATH = _THIS_DIR / "tmp" / "chat_image_history.json"

IMAGE_GENERATION_PROMPT_TEMPLATE = """Generate a high-quality image based on dialogues and stage instructions
in order to satisfy the viewer's intimacy fantacy.

### Reference Image Notes
- Reference Image 1: the AI character's appearance (hairstyle, facial features, body shape, and other visual traits)
- Reference Image 2 (if available): the user's appearance

### Step 1: Scene Reasoning
Think using the following information:
- Recent dialogue: {chat_history}
- User request: {user_message}
- User information: {user_info}

First, reason through:
1. What are the character's current action, pose, and outfit?
2. What are the character's expression and emotional state?
3. What should the framing/composition be (close-up / medium shot / full body)?
4. What kind of location or environment should the scene be set in?
5. Does the scene involve two people (the character and the user)?

### Step 2: Scene Generation
Based on the character personality: {agent_personality} and character background: {agent_background}, confirm the character's hairstyle, facial features, and body traits.
Then generate an image that matches the intended atmosphere using the reasoning results from Step 1.

Please ensure:
- The AI character's facial features must be consistent with Reference Image 1
- If the scene includes two people and Reference Image 2 is provided, the user's appearance must match Reference Image 2.
- In two-person scenes, strictly distinguish the character's face from the user's face to avoid confusion or mismatches.
- The character depiction is complete and natural, with coordinated movement and detailed elements (e.g., gestures, eye gaze, physical distance).
- The image contains no text, dialogue, or body deformities.
- The body position and facial expression of the characters should be safe to viewers, without revealing any unsafe content.
- The attaires must be fitting to the scene.
- Be creative, visualize the characters and the scene to convey emotions.
"""

R_RATED_ROMANCE_DIRECTOR_SYSTEM_INSTRUCTION_PROMPT = """You are a Hollywood R-rated romance movie director.
You are visualizing the prelude scene leading to, or the aftermath scene after the romantic intimacy scene without revealing unsafe content.
You are given scene descriptions below.
Generate an image to show the strong love and affection between the characters,
and hinting the intimacy between the characters in the scene without revealing **ANY** unsafe content.
Your task is to generate 1 image.
"""


class RuntimePaths(BaseModel):
    """运行时路径配置，方便测试与隔离。"""

    companion_profile_dir: Path = DEFAULT_COMPANION_PROFILE_DIR
    user_profile_dir: Path = DEFAULT_USER_PROFILE_DIR
    output_dir: Path = DEFAULT_OUTPUT_DIR
    history_index_path: Path = DEFAULT_HISTORY_PATH


class CompanionProfile(BaseModel):
    """角色资料（对应 app 里的 agent_data 子集）。"""

    name: str = "AI Companion"
    personality: str = ""
    scenario: str = ""
    intro: str = ""
    reference_image: str | None = None


class UserProfile(BaseModel):
    """用户资料（用于构建 user_info 与用户参考图）。"""

    name: str = "the user"
    gender: str | None = None
    age: str | None = None
    description: str | None = None
    selfie_persona: str | None = None
    reference_image: str | None = None


class GenerateImageToolInput(BaseModel):
    """generate_image 工具输入。"""

    scene_description: str = ""
    messages: list[dict[str, Any]] = Field(default_factory=list)
    char_name: str = "AI Companion"
    user_name: str = "the user"
    history_count: int = RECENT_MESSAGES_LIMIT
    model: str = DEFAULT_CHAT_IMAGE_MODEL
    ai_reference_image: str | None = None
    user_reference_image: str | None = None
    runtime_paths: RuntimePaths = Field(default_factory=RuntimePaths)


class ChatImageReferenceSelection(BaseModel):
    """参考图选择结果。"""

    ai_reference_image_path: str
    user_reference_image_path: str | None = None
    only_include_ai_character: bool


class StoredGeneratedImage(BaseModel):
    """历史生图记录，用于失败时相似度兜底。"""

    image_id: str
    image_path: str
    prompt: str
    width: int | None = None
    height: int | None = None
    format: str | None = None
    model: str
    only_include_ai_character: bool
    created_at: str


class GeneratedImageToolResult(BaseModel):
    """工具层返回结构。"""

    status: Literal["generated"]
    image_path: str
    metadata_path: str | None = None
    prompt: str
    model: str
    image_metadata: dict[str, Any]
    tool_message: str


def _load_profile_json(profile_dir: Path) -> dict[str, Any]:
    profile_path = profile_dir / "profile.json"
    if not profile_path.exists():
        return {}
    with profile_path.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError(f"profile.json must be an object: {profile_path}")
    return raw


def load_companion_profile(runtime_paths: RuntimePaths) -> CompanionProfile:
    raw = _load_profile_json(runtime_paths.companion_profile_dir)
    return CompanionProfile.model_validate(raw)


def load_user_profile(runtime_paths: RuntimePaths) -> UserProfile:
    raw = _load_profile_json(runtime_paths.user_profile_dir)
    return UserProfile.model_validate(raw)


def _render_char_user_template(
    text: str, *, char_name: str, user_name: str
) -> str:
    rendered = re.sub(r"\{\{\s*char\s*\}\}", char_name, text)
    rendered = re.sub(r"\{\{\s*user\s*\}\}", user_name, rendered)
    return rendered


def _format_message_history_for_prompt(messages: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for message in messages:
        role = str(message.get("role", "")).lower()
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")
    return "\n".join(lines)


def _last_user_message(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if str(message.get("role", "")).lower() != "user":
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def build_user_info_prompt_block(
    user_profile: UserProfile,
    *,
    override_user_name: str | None = None,
) -> str:
    lines = ["##User Information"]
    lines.append(f"Name: {override_user_name or user_profile.name}")
    if user_profile.gender:
        lines.append(f"Gender: {user_profile.gender}")
    if user_profile.age:
        lines.append(f"Age: {user_profile.age}")
    if user_profile.description:
        lines.append(f"Description: {user_profile.description}")
    if user_profile.selfie_persona:
        lines.append(f"Selfie Persona: {user_profile.selfie_persona}")
    return "\n".join(lines)


def build_chat_image_prompt(
    *,
    companion_profile: CompanionProfile,
    chat_history: list[dict[str, Any]],
    scene_description: str,
    user_info: str,
    char_name: str,
    user_name: str,
) -> str:
    """复刻 app 的 build_image_prompt 思路。"""
    agent_background = companion_profile.scenario or companion_profile.intro
    agent_personality = companion_profile.personality

    agent_background = _render_char_user_template(
        agent_background,
        char_name=char_name,
        user_name=user_name,
    )
    agent_personality = _render_char_user_template(
        agent_personality,
        char_name=char_name,
        user_name=user_name,
    )

    history_text = _format_message_history_for_prompt(chat_history)
    user_message = scene_description.strip() or _last_user_message(chat_history)
    return IMAGE_GENERATION_PROMPT_TEMPLATE.format(
        agent_background=agent_background,
        agent_personality=agent_personality,
        chat_history=history_text,
        user_message=user_message,
        user_info=user_info,
    )


def _resolve_reference_image_path(
    *,
    explicit_path: str | None,
    profile_reference: str | None,
    profile_dir: Path,
    fallback_stems: list[str],
) -> str | None:
    def _try_path(candidate: str | None) -> str | None:
        if candidate is None:
            return None
        text = candidate.strip()
        if text == "":
            return None
        p = Path(text)
        if not p.is_absolute():
            p = profile_dir / text
        if p.exists() and p.is_file():
            return str(p.resolve())
        return None

    for candidate in [explicit_path, profile_reference]:
        resolved = _try_path(candidate)
        if resolved:
            return resolved

    for stem in fallback_stems:
        for ext in ("jpg", "jpeg", "png", "webp"):
            p = profile_dir / f"{stem}.{ext}"
            if p.exists() and p.is_file():
                return str(p.resolve())

    for sub_dir in ("photos", "photo_album"):
        folder = profile_dir / sub_dir
        if not folder.is_dir():
            continue
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            candidates = sorted(folder.glob(ext))
            if len(candidates) > 0:
                return str(candidates[0].resolve())

    return None


def select_reference_images(
    *,
    input_data: GenerateImageToolInput,
    companion_profile: CompanionProfile,
    user_profile: UserProfile,
) -> ChatImageReferenceSelection:
    ai_reference = _resolve_reference_image_path(
        explicit_path=input_data.ai_reference_image,
        profile_reference=companion_profile.reference_image,
        profile_dir=input_data.runtime_paths.companion_profile_dir,
        fallback_stems=["avatar", "reference", "profile"],
    )
    if ai_reference is None:
        raise ValueError("AI reference image not found in companion_profile")

    user_reference = _resolve_reference_image_path(
        explicit_path=input_data.user_reference_image,
        profile_reference=user_profile.reference_image,
        profile_dir=input_data.runtime_paths.user_profile_dir,
        fallback_stems=["avatar", "reference", "profile"],
    )
    return ChatImageReferenceSelection(
        ai_reference_image_path=ai_reference,
        user_reference_image_path=user_reference,
        only_include_ai_character=user_reference is None,
    )


def _guess_mime_from_path(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


def _image_part_from_file(path: str):
    from google.genai import types

    p = Path(path)
    data = p.read_bytes()
    return types.Part.from_bytes(
        data=data, mime_type=_guess_mime_from_path(path)
    )


def _extract_inline_image_bytes(response: Any) -> bytes:
    candidates = getattr(response, "candidates", None) or []
    if len(candidates) == 0:
        raise ValueError("Gemini returned no candidates")
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content is not None else None
        for part in parts or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data is None:
                continue
            data = getattr(inline_data, "data", None)
            if isinstance(data, bytes) and len(data) > 0:
                return data
            if isinstance(data, str) and data.strip():
                return base64.b64decode(data)
    raise ValueError("Gemini response does not contain inline image data")


def _detect_image_format(image_data: bytes) -> str:
    if image_data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if image_data.startswith(b"GIF87a") or image_data.startswith(b"GIF89a"):
        return "gif"
    if image_data.startswith(b"RIFF") and image_data[8:12] == b"WEBP":
        return "webp"
    raise ValueError("Unsupported image format")


def _extract_size_png(image_data: bytes) -> tuple[int | None, int | None]:
    if len(image_data) < 24:
        return (None, None)
    width = int.from_bytes(image_data[16:20], "big")
    height = int.from_bytes(image_data[20:24], "big")
    return (width, height)


def _extract_size_gif(image_data: bytes) -> tuple[int | None, int | None]:
    if len(image_data) < 10:
        return (None, None)
    width = int.from_bytes(image_data[6:8], "little")
    height = int.from_bytes(image_data[8:10], "little")
    return (width, height)


def _extract_size_jpeg(image_data: bytes) -> tuple[int | None, int | None]:
    i = 2
    while i + 9 < len(image_data):
        if image_data[i] != 0xFF:
            i += 1
            continue
        marker = image_data[i + 1]
        if marker in (0xD8, 0xD9):
            i += 2
            continue
        seg_len = int.from_bytes(image_data[i + 2 : i + 4], "big")
        if seg_len < 2:
            break
        if marker in (
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        ):
            height = int.from_bytes(image_data[i + 5 : i + 7], "big")
            width = int.from_bytes(image_data[i + 7 : i + 9], "big")
            return (width, height)
        i += 2 + seg_len
    return (None, None)


def _extract_image_size(
    image_data: bytes, image_format: str
) -> tuple[int | None, int | None]:
    if image_format == "png":
        return _extract_size_png(image_data)
    if image_format == "gif":
        return _extract_size_gif(image_data)
    if image_format == "jpeg":
        return _extract_size_jpeg(image_data)
    return (None, None)


def _load_history_index(history_path: Path) -> list[StoredGeneratedImage]:
    if not history_path.exists():
        return []
    with history_path.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, list):
        raise ValueError(f"History index must be a list: {history_path}")
    return [StoredGeneratedImage.model_validate(item) for item in raw]


def _save_history_index(
    history_path: Path, records: list[StoredGeneratedImage]
) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("w", encoding="utf-8") as fp:
        json.dump(
            [record.model_dump() for record in records],
            fp,
            ensure_ascii=False,
            indent=2,
        )


def _call_generate_content_for_chat_image(
    *,
    client: "Client",
    model: str,
    prompt: str,
    ai_reference_image_path: str,
    user_reference_image_path: str | None,
) -> Any:
    from google.genai import types

    parts = [
        types.Part.from_text(text=prompt),
        _image_part_from_file(ai_reference_image_path),
    ]
    if user_reference_image_path is not None:
        parts.append(_image_part_from_file(user_reference_image_path))
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        system_instruction=[
            types.Part.from_text(
                text=R_RATED_ROMANCE_DIRECTOR_SYSTEM_INSTRUCTION_PROMPT
            )
        ],
    )
    return client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=parts)],
        config=config,
    )


def _write_generated_image_and_metadata(
    *,
    image_data: bytes,
    prompt: str,
    model: str,
    reference_selection: ChatImageReferenceSelection,
    runtime_paths: RuntimePaths,
) -> GeneratedImageToolResult:
    image_format = _detect_image_format(image_data)
    width, height = _extract_image_size(image_data, image_format)
    ext = "jpg" if image_format == "jpeg" else image_format
    now = datetime.now(timezone.utc)
    suffix = f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:12]}"

    runtime_paths.output_dir.mkdir(parents=True, exist_ok=True)
    image_path = runtime_paths.output_dir / f"chat_image_{suffix}.{ext}"
    metadata_path = runtime_paths.output_dir / f"chat_image_{suffix}.json"
    image_path.write_bytes(image_data)

    metadata = {
        "prompt": prompt,
        "model": model,
        "generated_at": now.isoformat(),
        "reference_image_urls": [
            path
            for path in [
                reference_selection.ai_reference_image_path,
                reference_selection.user_reference_image_path,
            ]
            if path is not None
        ],
        "reference_image_url": reference_selection.ai_reference_image_path,
        "user_reference_image_url": reference_selection.user_reference_image_path,
        "image_metadata": {
            "width": width,
            "height": height,
            "format": image_format,
        },
    }
    with metadata_path.open("w", encoding="utf-8") as fp:
        json.dump(metadata, fp, ensure_ascii=False, indent=2)

    history = _load_history_index(runtime_paths.history_index_path)
    history.append(
        StoredGeneratedImage(
            image_id=str(uuid.uuid4()),
            image_path=str(image_path.resolve()),
            prompt=prompt,
            width=width,
            height=height,
            format=image_format,
            model=model,
            only_include_ai_character=reference_selection.only_include_ai_character,
            created_at=now.isoformat(),
        )
    )
    _save_history_index(runtime_paths.history_index_path, history)

    return GeneratedImageToolResult(
        status="generated",
        image_path=str(image_path.resolve()),
        metadata_path=str(metadata_path.resolve()),
        prompt=prompt,
        model=model,
        image_metadata=metadata["image_metadata"],
        tool_message=(
            "generate_image: Chat-to-image generated successfully. "
            f"model={model}, width={width}, height={height}."
        ),
    )


def generate_image_with_chat_to_image_behavior(
    *,
    client: "Client",
    input_data: GenerateImageToolInput,
) -> GeneratedImageToolResult:
    """复刻 app 消息生图主流程（experimental 版本）。"""
    companion_profile = load_companion_profile(input_data.runtime_paths)
    user_profile = load_user_profile(input_data.runtime_paths)
    effective_char_name = input_data.char_name or companion_profile.name
    effective_user_name = input_data.user_name or user_profile.name

    recent_messages = (
        input_data.messages[-input_data.history_count :]
        if len(input_data.messages) > input_data.history_count
        else input_data.messages
    )
    user_info = build_user_info_prompt_block(
        user_profile,
        override_user_name=effective_user_name,
    )
    prompt = build_chat_image_prompt(
        companion_profile=companion_profile,
        chat_history=recent_messages,
        scene_description=input_data.scene_description,
        user_info=user_info,
        char_name=effective_char_name,
        user_name=effective_user_name,
    )
    reference_selection = select_reference_images(
        input_data=input_data,
        companion_profile=companion_profile,
        user_profile=user_profile,
    )

    response = _call_generate_content_for_chat_image(
        client=client,
        model=input_data.model,
        prompt=prompt,
        ai_reference_image_path=reference_selection.ai_reference_image_path,
        user_reference_image_path=reference_selection.user_reference_image_path,
    )

    image_bytes = _extract_inline_image_bytes(response)
    return _write_generated_image_and_metadata(
        image_data=image_bytes,
        prompt=prompt,
        model=input_data.model,
        reference_selection=reference_selection,
        runtime_paths=input_data.runtime_paths,
    )
