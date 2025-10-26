import json
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.utils import gemini as gemini_utils


# 统一的情绪枚举字符串，作为 LLM 选择与对外 API 的标准值
# 注意：大小写、空格需与此表严格一致
EMOTION_LIST: List[Tuple[str, str]] = [
    ("Neutral", "中性、默认、不带明显情绪"),
    ("Happy", "开心、愉快、温暖微笑"),
    ("Surprise", "惊讶、意外、突然变化"),
    ("Angry", "生气、愤怒、不满"),
    ("Sad", "难过、伤心、失落"),
    ("Confused", "困惑、疑惑、不理解"),
    ("Shy", "害羞、局促、含蓄"),
    ("Excited", "兴奋、激动、热情"),
    ("Pleased", "满意、欣慰、被取悦"),
    ("Bored", "无聊、提不起劲"),
    ("Disgust", "厌恶、反感、排斥"),
    ("Fear", "害怕、恐惧、不安"),
    ("Embarrassed", "尴尬、不好意思"),
    ("Tired", "疲惫、劳累"),
    ("Sleepy", "困倦、想睡"),
    ("Thinking", "思考、沉思、权衡"),
    ("Curious", "好奇、求知欲强"),
    ("Skeptical", "怀疑、将信将疑"),
    ("Flirt", "打趣、调侃、暧昧"),
    ("Determined", "坚定、下定决心"),
]


def _emotion_names() -> List[str]:
    return [name for name, _ in EMOTION_LIST]


def _emotion_descriptions_text() -> str:
    lines = [f"- {name}: {desc}" for name, desc in EMOTION_LIST]
    return "\n".join(lines)


_mapping_lock = threading.Lock()
_emotion_to_image: Dict[str, str] = {}


def list_emotions() -> List[dict]:
    """返回可选情绪及描述。"""
    return [{"name": name, "description": desc} for name, desc in EMOTION_LIST]


def get_mapping() -> Dict[str, str]:
    with _mapping_lock:
        return dict(_emotion_to_image)


def set_mapping(new_mapping: Dict[str, str], replace: bool = True) -> Dict[str, str]:
    """
    设置情绪到图片 URL 的映射。

    Args:
        new_mapping: {emotion_name: image_url}
        replace: True 则整体替换，False 则合并覆盖
    """
    allowed = set(_emotion_names())
    invalid = [k for k in new_mapping.keys() if _normalize_emotion(k) not in allowed]
    if invalid:
        raise ValueError(f"包含非法情绪: {invalid}")

    with _mapping_lock:
        if replace:
            _emotion_to_image.clear()
        for k, v in new_mapping.items():
            canonical = _canonical_emotion(k)
            _emotion_to_image[canonical] = v
        return dict(_emotion_to_image)


def _normalize_emotion(value: str) -> str:
    return (value or "").strip()


def _canonical_emotion(value: str) -> str:
    """将任意大小写/前后空格的输入映射到标准情绪名，找不到则返回原值。"""
    norm = _normalize_emotion(value)
    for name in _emotion_names():
        if name.lower() == norm.lower():
            return name
    return norm


@dataclass
class EmotionSelectInput:
    utterance: str
    context: Optional[str] = None
    character_state: Optional[str] = None


def select_emotion_with_gemini(inp: EmotionSelectInput) -> str:
    """
    调用 Gemini，让其在 20 个情绪中选择并仅输出 JSON {"emotion": "..."}。
    若返回不合规或不在列表，则回退 Neutral。
    """
    system_prompt = (
        "你是一个Live2D角色情绪控制器。\n"
        "根据用户提供的对话文本和情境，你必须从以下列表中选择一个最合适的情绪名称作为输出。\n"
        "你只能输出JSON且只包含一个键 emotion；emotion 的值必须严格取自下列列表之一，大小写一致。\n"
        "若无法判断，请选择 Neutral。\n\n"
        "可用情绪列表(共20项)：\n"
        f"{_emotion_descriptions_text()}\n\n"
        "输出要求：\n"
        "- 只输出 JSON，形如 {\"emotion\": \"Happy\" }；不得输出其他文字。\n"
        "- emotion 必须为上面列表中的一个。\n"
    )

    user_block = [
        "当前情境：",
        inp.context.strip() if inp.context else "(无)
",
        "\n角色台词：",
        inp.utterance.strip(),
    ]
    if inp.character_state:
        user_block.extend(["\n角色状态：", inp.character_state.strip()])

    full_prompt = system_prompt + "\n" + "".join(user_block)

    client = gemini_utils.get_genai_client()

    # 使用结构化 JSON 响应，便于解析和前期约束
    from google.genai import types

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "emotion": types.Schema(type=types.Type.STRING),
            },
            required=["emotion"],
        ),
    )

    model = global_config_loaded_from_config_yaml.agent.model
    try:
        resp = client.models.generate_content(
            model=model,
            contents=full_prompt,
            config=config,
        )
    except Exception as e:
        logger.error(f"Gemini API 调用失败: {e}")
        return "Neutral"

    raw_text: Optional[str] = None
    try:
        raw_text = getattr(resp, "text", None)
        if not raw_text and getattr(resp, "candidates", None):
            parts = getattr(resp.candidates[0].content, "parts", [])
            texts = [p.text for p in parts if getattr(p, "text", None)]
            raw_text = "\n".join(texts).strip() if texts else None
    except Exception:  # 容错解析
        raw_text = None

    if not raw_text:
        logger.warning("Gemini 返回空文本，使用 Neutral")
        return "Neutral"

    try:
        data = json.loads(raw_text)
        selected = _canonical_emotion(str(data.get("emotion", "")).strip())
        if selected in _emotion_names():
            return selected
    except Exception as e:
        logger.warning(f"解析 Gemini JSON 失败，将回退 Neutral。raw={raw_text} err={e}")

    return "Neutral"


def get_image_for_emotion(emotion: str) -> Optional[str]:
    canonical = _canonical_emotion(emotion)
    with _mapping_lock:
        return _emotion_to_image.get(canonical)
