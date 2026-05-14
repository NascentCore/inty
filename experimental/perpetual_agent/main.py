"""Perpetual agent demos.

1) pulse mode: perpetual loop with pulse + call_user tools
2) living mode: model-orchestrated virtual companion with proactive outreach
"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from xml.sax.saxutils import escape as xml_escape
from typing import Any

from .living_companion import (
    CompanionState,
    InMemoryChannelTransport,
    ModelCatalog,
    PerpetualCompanionAgent,
    ScriptedModelExecutor,
    classify_emotion,
)
from .telegram_agentic_loop import PULSE_TOOL_DEFINITION, run_telegram_llm_session

SYSTEM_PROMPT_TEMPLATE = """
You are a perpetual demo agent.
Current pulse counter: {pulse_count}

You can call core tools:
- pulse(seconds: integer)
- call_user(phone_number: string, reason: string)
- emotions(emotion: string, expression?: string, reason?: string)
- compact_recent_conversation_into_layer(layer_name, layer_content, recent_message_count)
- compact_named_layers_into_layer(layer_name, layer_content, source_layer_names)
- per-layer tools named like update_layer_<layer_name> for non-conversation layers

Emotion rules:
- keep the emotional_state_layer up-to-date as user mood changes
- use the emotions tool when you need to explicitly shift emotional state
- emotional_state_layer affects tone/stance in following turns

Compaction rules:
- every layer has nesting_level
- compacting conversation messages creates a new layer with nesting_level=1
- compacting named layers requires identical source nesting_level and creates target nesting_level+1
- named-layer compaction source layers must be contiguous in stack order

When pulse is called:
1) sleep for the given seconds
2) increment the pulse counter
3) continue the loop

When the user asks "call me at <number>":
1) call call_user immediately with that number
2) provide a short reason for the call
3) do not ask for extra confirmation if a number is already present
""".strip()

CALL_USER_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "call_user",
        "description": (
            "Place a phone call through Twilio and connect audio to a Gemini Live bridge."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "Target user's phone number in E.164 format.",
                },
                "reason": {
                    "type": "string",
                    "description": "Short reason/purpose for this phone call.",
                },
            },
            "required": ["phone_number", "reason"],
            "additionalProperties": False,
        },
    },
}


EMOTIONS_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "emotions",
        "description": (
            "Update the agent emotional_state_layer that influences following turns."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "emotion": {
                    "type": "string",
                    "description": "Target emotional state label, e.g. sad, neutral, joyful.",
                },
                "expression": {
                    "type": "string",
                    "description": (
                        "Optional expression style. If omitted, defaults are derived from emotion."
                    ),
                },
                "reason": {
                    "type": "string",
                    "description": "Optional short reason/context for the emotional update.",
                },
            },
            "required": ["emotion"],
            "additionalProperties": False,
        },
    },
}


COMPACT_CONVERSATION_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "compact_recent_conversation_into_layer",
        "description": (
            "Compact recent conversation messages into a new named character layer "
            "inserted just below the conversation layer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "layer_name": {
                    "type": "string",
                    "description": (
                        "Name/title for the new layer, e.g. 'midnight_reflection'."
                    ),
                },
                "layer_content": {
                    "type": "string",
                    "description": (
                        "Canonical content/instruction for the new compacted layer."
                    ),
                },
                "recent_message_count": {
                    "type": "integer",
                    "description": (
                        "How many most recent conversation messages should be compacted."
                    ),
                },
            },
            "required": ["layer_name", "layer_content", "recent_message_count"],
            "additionalProperties": False,
        },
    },
}


COMPACT_NAMED_LAYERS_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "compact_named_layers_into_layer",
        "description": (
            "Compact multiple named character layers into a higher-level layer. "
            "All source layers must share the same nesting level and must be contiguous."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "layer_name": {
                    "type": "string",
                    "description": (
                        "Name/title for the new merged layer, e.g. 'phase_2_memory'."
                    ),
                },
                "layer_content": {
                    "type": "string",
                    "description": "Canonical content/instruction for the merged layer.",
                },
                "source_layer_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Names of source named layers to compact. "
                        "All must exist, have identical nesting level, and be contiguous in stack order."
                    ),
                },
            },
            "required": ["layer_name", "layer_content", "source_layer_names"],
            "additionalProperties": False,
        },
    },
}


@dataclass
class CharacterLayer:
    name: str
    content: str
    is_conversation_layer: bool = False
    nesting_level: int = 0
    raw_messages: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class EmotionalStateLayer:
    emotion: str = "neutral"
    expression: str = "warm"
    update_source: str = "default"


def _default_expression_for_emotion(emotion: str) -> str:
    emotion_to_expression = {
        "sad": "gentle",
        "angry": "calm",
        "joyful": "playful",
        "neutral": "warm",
    }
    return emotion_to_expression.get(emotion, "warm")


def _normalize_emotion_label(emotion: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", emotion.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        raise ValueError("emotion cannot be empty after normalization.")
    return normalized


def _flatten_text(*, text: str, max_chars: int = 120) -> str:
    flattened = re.sub(r"\s+", " ", text).strip()
    return flattened[:max_chars]


def _render_emotional_state_layer(layer: EmotionalStateLayer) -> str:
    return (
        "[emotional_state_layer]\n"
        f"Current emotion: {layer.emotion}\n"
        f"Current expression: {layer.expression}\n"
        f"Update source: {layer.update_source}"
    )


def _latest_user_message(conversation_messages: list[dict[str, Any]]) -> str | None:
    for message in reversed(conversation_messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return None


def _apply_emotion_classification_from_user_message(
    *, layer: EmotionalStateLayer, user_message: str
) -> dict[str, str]:
    classification = classify_emotion(user_message)
    layer.emotion = classification.emotion
    layer.expression = classification.expression
    layer.update_source = (
        "user_message_classifier:" f"{_flatten_text(text=user_message, max_chars=80)}"
    )
    return {
        "updated_emotion": layer.emotion,
        "updated_expression": layer.expression,
        "update_source": layer.update_source,
    }


def _execute_emotions_tool(
    *,
    layer: EmotionalStateLayer,
    emotion: str,
    expression: str | None,
    reason: str | None,
) -> dict[str, str]:
    normalized_emotion = _normalize_emotion_label(emotion)
    normalized_expression = (
        expression or ""
    ).strip() or _default_expression_for_emotion(normalized_emotion)
    normalized_reason = (reason or "").strip() or "emotions tool update"
    layer.emotion = normalized_emotion
    layer.expression = normalized_expression
    layer.update_source = (
        f"emotions_tool:{_flatten_text(text=normalized_reason, max_chars=80)}"
    )
    return {
        "updated_emotion": layer.emotion,
        "updated_expression": layer.expression,
        "update_source": layer.update_source,
    }


def _normalize_layer_name(layer_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", layer_name.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        raise ValueError("Layer name cannot be empty after normalization.")
    return normalized


def _layer_update_tool_name(layer_name: str) -> str:
    return f"update_layer_{_normalize_layer_name(layer_name)}"


def _build_layer_update_tool_definition(layer: CharacterLayer) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": _layer_update_tool_name(layer.name),
            "description": (
                f"Update content of character layer '{layer.name}'. "
                "You may also rename the layer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "New content for this layer.",
                    },
                    "rename_to": {
                        "type": "string",
                        "description": (
                            "Optional new layer name. Tool name will change on next turn."
                        ),
                    },
                },
                "required": ["content"],
                "additionalProperties": False,
            },
        },
    }


def _build_seed_layer_raw_messages(
    *, layer_name: str, layer_content: str, is_conversation_layer: bool
) -> list[dict[str, str]]:
    layer_type = "conversation" if is_conversation_layer else "character"
    return [
        {
            "role": "system",
            "content": (
                f"[seed_layer name={layer_name} type={layer_type} nesting_level=0]\n"
                f"{layer_content}"
            ),
        }
    ]


def _build_default_character_layers() -> list[CharacterLayer]:
    return [
        CharacterLayer(
            name="fundamental_identity",
            content=(
                "Fundamental aspect: stable identity, mission, and non-negotiable values "
                "for the agent."
            ),
            raw_messages=_build_seed_layer_raw_messages(
                layer_name="fundamental_identity",
                layer_content=(
                    "Fundamental aspect: stable identity, mission, and non-negotiable values "
                    "for the agent."
                ),
                is_conversation_layer=False,
            ),
        ),
        CharacterLayer(
            name="interaction_style",
            content=(
                "Interactive aspect: preferred dialogue style, empathy strategy, and tone "
                "for user-facing responses."
            ),
            raw_messages=_build_seed_layer_raw_messages(
                layer_name="interaction_style",
                layer_content=(
                    "Interactive aspect: preferred dialogue style, empathy strategy, and tone "
                    "for user-facing responses."
                ),
                is_conversation_layer=False,
            ),
        ),
        CharacterLayer(
            name="conversation",
            content=(
                "Shallowest layer. Represents current live conversation context and should "
                "remain append-only through normal dialogue."
            ),
            is_conversation_layer=True,
            raw_messages=_build_seed_layer_raw_messages(
                layer_name="conversation",
                layer_content=(
                    "Shallowest layer. Represents current live conversation context and should "
                    "remain append-only through normal dialogue."
                ),
                is_conversation_layer=True,
            ),
        ),
    ]


def _validate_character_layers(layers: list[CharacterLayer]) -> None:
    if not layers:
        raise ValueError("Character layers cannot be empty.")
    conversation_layers = [layer for layer in layers if layer.is_conversation_layer]
    if len(conversation_layers) != 1:
        raise ValueError("Exactly one conversation layer is required.")
    if not layers[-1].is_conversation_layer:
        raise ValueError("Conversation layer must be the shallowest (last) layer.")
    for layer in layers:
        if layer.nesting_level < 0:
            raise ValueError("Layer nesting_level must be >= 0.")
    normalized_non_conversation_names = [
        _normalize_layer_name(layer.name)
        for layer in layers
        if not layer.is_conversation_layer
    ]
    if len(normalized_non_conversation_names) != len(
        set(normalized_non_conversation_names)
    ):
        raise ValueError(
            "Duplicate non-conversation layer names are not allowed after normalization."
        )


def _render_layer_message(layer: CharacterLayer) -> str:
    layer_kind = "conversation" if layer.is_conversation_layer else "character"
    return (
        f"[character_layer name={layer.name} type={layer_kind} nesting_level={layer.nesting_level}]\n"
        f"{layer.content}"
    )


def _build_layer_messages(layers: list[CharacterLayer]) -> list[dict[str, str]]:
    _validate_character_layers(layers)
    return [
        {"role": "system", "content": _render_layer_message(layer)} for layer in layers
    ]


def _build_layer_tools(layers: list[CharacterLayer]) -> list[dict[str, Any]]:
    _validate_character_layers(layers)
    layer_tools: list[dict[str, Any]] = []
    for layer in layers:
        if layer.is_conversation_layer:
            continue
        layer_tools.append(_build_layer_update_tool_definition(layer))
    return layer_tools


def _find_layer_by_update_tool_name(
    *, layers: list[CharacterLayer], tool_name: str
) -> CharacterLayer | None:
    for layer in layers:
        if layer.is_conversation_layer:
            continue
        if _layer_update_tool_name(layer.name) == tool_name:
            return layer
    return None


def _execute_layer_update_tool(
    *,
    layers: list[CharacterLayer],
    tool_name: str,
    content: str,
    rename_to: str | None,
) -> dict[str, Any]:
    layer = _find_layer_by_update_tool_name(layers=layers, tool_name=tool_name)
    if layer is None:
        raise ValueError(f"Unsupported layer update tool call: {tool_name}")
    if rename_to is not None:
        normalized_updated_name = _normalize_layer_name(rename_to)
        if normalized_updated_name == "conversation":
            raise ValueError(
                "Only the shallow conversation layer may be named conversation."
            )
        for existing_layer in layers:
            if existing_layer is layer or existing_layer.is_conversation_layer:
                continue
            if _normalize_layer_name(existing_layer.name) == normalized_updated_name:
                raise ValueError(
                    "Layer rename would collide with an existing layer name after normalization."
                )
        layer.name = normalized_updated_name
    _validate_character_layers(layers)
    layer.content = content
    return {
        "updated_layer_name": layer.name,
        "updated_layer_tool_name": _layer_update_tool_name(layer.name),
        "layer_content": layer.content,
    }


def _ensure_unique_compacted_layer_name(
    *, layers: list[CharacterLayer], normalized_layer_name: str
) -> None:
    for layer in layers:
        if layer.is_conversation_layer:
            continue
        if _normalize_layer_name(layer.name) == normalized_layer_name:
            raise ValueError(
                "Compacted layer name collides with an existing layer after normalization."
            )


def _extract_message_preview(message: dict[str, Any]) -> str:
    role = str(message.get("role", "unknown"))
    content = str(message.get("content", ""))
    flattened = re.sub(r"\s+", " ", content).strip()
    if not flattened:
        flattened = "<empty>"
    return f"{role}: {flattened}"


def _clone_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [copy.deepcopy(message) for message in messages]


def _extract_layer_preview(layer: CharacterLayer) -> str:
    flattened = re.sub(r"\s+", " ", layer.content).strip()
    if not flattened:
        flattened = "<empty>"
    return f"layer={layer.name} nesting_level={layer.nesting_level} content={flattened[:220]}"


def _sanitize_tool_output_for_conversation(
    *, tool_name: str, tool_output: dict[str, Any]
) -> dict[str, Any]:
    sanitized_output = copy.deepcopy(tool_output)
    if tool_name == "compact_recent_conversation_into_layer":
        raw_messages = sanitized_output.pop("raw_compacted_messages", None)
        if isinstance(raw_messages, list):
            sanitized_output["raw_compacted_message_count"] = len(raw_messages)
            sanitized_output["raw_compacted_messages_omitted"] = True
    if tool_name == "compact_named_layers_into_layer":
        raw_messages = sanitized_output.pop("raw_source_messages", None)
        if isinstance(raw_messages, list):
            sanitized_output["raw_source_message_count"] = len(raw_messages)
            sanitized_output["raw_source_messages_omitted"] = True
    return sanitized_output


def _execute_compact_conversation_layer_tool(
    *,
    layers: list[CharacterLayer],
    conversation_messages: list[dict[str, Any]],
    layer_name: str,
    layer_content: str,
    recent_message_count: int,
    max_compactable_messages: int | None = None,
) -> dict[str, Any]:
    _validate_character_layers(layers)
    if recent_message_count <= 0:
        raise ValueError("recent_message_count must be > 0")
    if recent_message_count > len(conversation_messages):
        raise ValueError(
            "recent_message_count cannot exceed current conversation message count"
        )
    if max_compactable_messages is not None:
        if max_compactable_messages < 0:
            raise ValueError("max_compactable_messages must be >= 0")
        if max_compactable_messages > len(conversation_messages):
            raise ValueError(
                "max_compactable_messages cannot exceed current conversation message count"
            )
        if recent_message_count > max_compactable_messages:
            raise ValueError(
                "Compaction can only include messages older than the current tool-call envelope."
            )
    normalized_name = _normalize_layer_name(layer_name)
    if normalized_name == "conversation":
        raise ValueError("Compacted layer name cannot be conversation.")
    _ensure_unique_compacted_layer_name(
        layers=layers, normalized_layer_name=normalized_name
    )
    if max_compactable_messages is None:
        compactable_end_index = len(conversation_messages)
    else:
        compactable_end_index = max_compactable_messages
    compacted_start_index = compactable_end_index - recent_message_count
    compacted_slice = conversation_messages[compacted_start_index:compactable_end_index]
    del conversation_messages[compacted_start_index:compactable_end_index]

    compacted_transcript = "\n".join(
        f"- {_extract_message_preview(message)}" for message in compacted_slice
    )
    compacted_layer = CharacterLayer(
        name=normalized_name,
        content=f"{layer_content}\n\nCompacted transcript:\n{compacted_transcript}",
        nesting_level=1,
        raw_messages=_clone_messages(compacted_slice),
    )
    conversation_layer_index = len(layers) - 1
    layers.insert(conversation_layer_index, compacted_layer)
    _validate_character_layers(layers)
    return {
        "created_layer_name": compacted_layer.name,
        "created_layer_tool_name": _layer_update_tool_name(compacted_layer.name),
        "created_layer_nesting_level": compacted_layer.nesting_level,
        "compacted_message_count": recent_message_count,
        "raw_compacted_messages": _clone_messages(compacted_layer.raw_messages),
        "remaining_conversation_messages": len(conversation_messages),
    }


def _execute_compact_named_layers_tool(
    *,
    layers: list[CharacterLayer],
    layer_name: str,
    layer_content: str,
    source_layer_names: list[str],
) -> dict[str, Any]:
    _validate_character_layers(layers)
    if not source_layer_names:
        raise ValueError("source_layer_names must contain at least one layer name.")

    normalized_source_names = [
        _normalize_layer_name(name) for name in source_layer_names
    ]
    if len(normalized_source_names) != len(set(normalized_source_names)):
        raise ValueError(
            "source_layer_names cannot contain duplicates after normalization."
        )

    index_by_name: dict[str, int] = {}
    for idx, layer in enumerate(layers):
        if layer.is_conversation_layer:
            continue
        index_by_name[_normalize_layer_name(layer.name)] = idx

    selected_indices = []
    for normalized_name in normalized_source_names:
        if normalized_name not in index_by_name:
            raise ValueError(f"Unknown source layer for compaction: {normalized_name}")
        selected_indices.append(index_by_name[normalized_name])
    selected_indices = sorted(selected_indices)
    for idx in range(1, len(selected_indices)):
        if selected_indices[idx] != selected_indices[idx - 1] + 1:
            raise ValueError(
                "Named-layer compaction requires source layers to be contiguous in the layer stack."
            )
    selected_layers = [layers[idx] for idx in selected_indices]

    source_nesting_levels = {layer.nesting_level for layer in selected_layers}
    if len(source_nesting_levels) != 1:
        raise ValueError(
            "Named-layer compaction requires all source layers to share the same nesting_level."
        )

    normalized_target_name = _normalize_layer_name(layer_name)
    if normalized_target_name == "conversation":
        raise ValueError("Compacted layer name cannot be conversation.")
    _ensure_unique_compacted_layer_name(
        layers=layers, normalized_layer_name=normalized_target_name
    )

    compacted_transcript = "\n".join(
        f"- {_extract_layer_preview(layer)}" for layer in selected_layers
    )
    merged_raw_messages: list[dict[str, Any]] = []
    for layer in selected_layers:
        merged_raw_messages.extend(_clone_messages(layer.raw_messages))

    merged_layer = CharacterLayer(
        name=normalized_target_name,
        content=f"{layer_content}\n\nCompacted layers:\n{compacted_transcript}",
        nesting_level=selected_layers[0].nesting_level + 1,
        raw_messages=merged_raw_messages,
    )

    insert_at = selected_indices[0]
    for idx in reversed(selected_indices):
        del layers[idx]
    layers.insert(insert_at, merged_layer)
    _validate_character_layers(layers)

    return {
        "created_layer_name": merged_layer.name,
        "created_layer_tool_name": _layer_update_tool_name(merged_layer.name),
        "created_layer_nesting_level": merged_layer.nesting_level,
        "compacted_layer_names": [layer.name for layer in selected_layers],
        "compacted_source_nesting_level": selected_layers[0].nesting_level,
        "raw_source_message_count": len(merged_raw_messages),
        "raw_source_messages": _clone_messages(merged_raw_messages),
    }


@dataclass(frozen=True)
class TwilioCallConfig:
    account_sid: str
    auth_token: str
    from_number: str
    gemini_live_bridge_ws_url: str
    bridge_system_prompt: str


def _required_env(env_name: str) -> str:
    value = (os.environ.get(env_name) or "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {env_name}")
    return value


def _load_twilio_call_config() -> TwilioCallConfig:
    return TwilioCallConfig(
        account_sid=_required_env("TWILIO_ACCOUNT_SID"),
        auth_token=_required_env("TWILIO_AUTH_TOKEN"),
        from_number=_required_env("TWILIO_PHONE_NUMBER"),
        gemini_live_bridge_ws_url=_required_env("GEMINI_LIVE_BRIDGE_WS_URL"),
        bridge_system_prompt=(
            os.environ.get("GEMINI_LIVE_CALL_SYSTEM_PROMPT")
            or "You are a helpful voice assistant."
        ).strip(),
    )


def _build_gemini_stream_twiml(
    *,
    gemini_live_bridge_ws_url: str,
    reason: str,
    system_prompt: str,
) -> str:
    escaped_url = xml_escape(gemini_live_bridge_ws_url, {'"': "&quot;"})
    escaped_reason = xml_escape(reason, {'"': "&quot;"})
    escaped_system_prompt = xml_escape(system_prompt, {'"': "&quot;"})
    return (
        "<Response>"
        "<Say>Connecting you to a Gemini live voice assistant.</Say>"
        "<Connect>"
        f'<Stream url="{escaped_url}">'
        '<Parameter name="reason" value="'
        f"{escaped_reason}"
        '"/>'
        '<Parameter name="system_prompt" value="'
        f"{escaped_system_prompt}"
        '"/>'
        "</Stream>"
        "</Connect>"
        "</Response>"
    )


def _create_twilio_call(
    *,
    to_number: str,
    reason: str,
    config: TwilioCallConfig,
    urlopen: Any = urllib.request.urlopen,
) -> dict[str, Any]:
    twiml = _build_gemini_stream_twiml(
        gemini_live_bridge_ws_url=config.gemini_live_bridge_ws_url,
        reason=reason,
        system_prompt=config.bridge_system_prompt,
    )
    body = urllib.parse.urlencode(
        {"From": config.from_number, "To": to_number, "Twiml": twiml}
    ).encode("utf-8")
    request = urllib.request.Request(
        url=f"https://api.twilio.com/2010-04-01/Accounts/{config.account_sid}/Calls.json",
        method="POST",
        data=body,
        headers={
            "Authorization": (
                "Basic "
                + base64.b64encode(
                    f"{config.account_sid}:{config.auth_token}".encode("utf-8")
                ).decode("utf-8")
            ),
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _is_call_request_prompt(text: str) -> bool:
    return bool(re.search(r"\bcall\s+me\s+at\b", text, flags=re.IGNORECASE))


def _tool_choice_for_user_prompt(user_prompt: str) -> str | dict[str, Any]:
    if _is_call_request_prompt(user_prompt):
        return {"type": "function", "function": {"name": "call_user"}}
    return "auto"


def _render_system_prompt(pulse_count: int) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(pulse_count=pulse_count)


def _serialize_tool_calls(tool_calls: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": tc.id,
            "type": tc.type,
            "function": {
                "name": tc.function.name,
                "arguments": tc.function.arguments,
            },
        }
        for tc in tool_calls
    ]


def _create_openai_client(api_key_env: str, base_url: str) -> Any:
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
    return OpenAI(api_key=os.environ[api_key_env], base_url=base_url)


def _execute_pulse_tool(seconds: int, pulse_count: int) -> tuple[int, dict[str, Any]]:
    time.sleep(seconds)
    updated_pulse_count = pulse_count + 1
    return (
        updated_pulse_count,
        {
            "slept_seconds": seconds,
            "pulse_count": updated_pulse_count,
            "note": "pulse complete, back to prompt",
        },
    )


def _execute_call_user_tool(
    *,
    phone_number: str,
    reason: str,
    create_call: Any = _create_twilio_call,
) -> dict[str, Any]:
    config = _load_twilio_call_config()
    twilio_response = create_call(to_number=phone_number, reason=reason, config=config)
    return {
        "to_number": phone_number,
        "reason": reason,
        "twilio_call_sid": twilio_response["sid"],
        "twilio_status": twilio_response["status"],
    }


def run_perpetual_agent(
    user_prompt: str,
    model: str,
    max_steps: int,
    client: Any | None,
    api_key_env: str,
    base_url: str,
) -> None:
    active_client = client or _create_openai_client(
        api_key_env=api_key_env, base_url=base_url
    )
    pulse_count = 0
    character_layers = _build_default_character_layers()
    emotional_state_layer = EmotionalStateLayer()
    last_classified_user_message: str | None = None
    conversation_messages: list[dict[str, Any]] = [
        {"role": "user", "content": user_prompt}
    ]
    forced_tool_choice = _tool_choice_for_user_prompt(user_prompt=user_prompt)

    for step in range(1, max_steps + 1):
        latest_user_message = _latest_user_message(conversation_messages)
        if (
            latest_user_message is not None
            and latest_user_message != last_classified_user_message
        ):
            _apply_emotion_classification_from_user_message(
                layer=emotional_state_layer,
                user_message=latest_user_message,
            )
            last_classified_user_message = latest_user_message

        request_messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": _render_system_prompt(pulse_count=pulse_count),
            }
        ]
        request_messages.extend(_build_layer_messages(character_layers))
        request_messages.append(
            {
                "role": "system",
                "content": _render_emotional_state_layer(emotional_state_layer),
            }
        )
        request_messages.extend(conversation_messages)
        request_tools = [
            PULSE_TOOL_DEFINITION,
            CALL_USER_TOOL_DEFINITION,
            EMOTIONS_TOOL_DEFINITION,
            COMPACT_CONVERSATION_TOOL_DEFINITION,
            COMPACT_NAMED_LAYERS_TOOL_DEFINITION,
            *_build_layer_tools(character_layers),
        ]

        response = active_client.chat.completions.create(
            model=model,
            messages=request_messages,
            tools=request_tools,
            tool_choice=forced_tool_choice if step == 1 else "auto",
        )
        assistant_message = response.choices[0].message
        assistant_content = assistant_message.content or ""
        tool_calls = assistant_message.tool_calls or []

        if not tool_calls:
            conversation_messages.append(
                {"role": "assistant", "content": assistant_content}
            )
            print(f"[step={step}] assistant: {assistant_content}")
            continue

        conversation_messages.append(
            {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": _serialize_tool_calls(tool_calls),
            }
        )
        current_tool_call_envelope_start_index = len(conversation_messages) - 1

        for tool_call in tool_calls:
            tool_args = json.loads(tool_call.function.arguments)
            if tool_call.function.name == "pulse":
                seconds = int(tool_args["seconds"])
                print(f"[step={step}] pulse(seconds={seconds})")
                pulse_count, tool_output = _execute_pulse_tool(
                    seconds=seconds, pulse_count=pulse_count
                )
            elif tool_call.function.name == "call_user":
                phone_number = str(tool_args["phone_number"]).strip()
                reason = str(tool_args["reason"]).strip()
                print(f"[step={step}] call_user(phone_number={phone_number})")
                tool_output = _execute_call_user_tool(
                    phone_number=phone_number,
                    reason=reason,
                )
            elif tool_call.function.name == "emotions":
                emotion = str(tool_args["emotion"]).strip()
                expression = (
                    str(tool_args["expression"]).strip()
                    if "expression" in tool_args and tool_args["expression"] is not None
                    else None
                )
                reason = (
                    str(tool_args["reason"]).strip()
                    if "reason" in tool_args and tool_args["reason"] is not None
                    else None
                )
                print(
                    f"[step={step}] emotions(emotion={emotion}, "
                    f"expression={expression or '<auto>'})"
                )
                tool_output = _execute_emotions_tool(
                    layer=emotional_state_layer,
                    emotion=emotion,
                    expression=expression,
                    reason=reason,
                )
            elif tool_call.function.name == "compact_recent_conversation_into_layer":
                layer_name = str(tool_args["layer_name"]).strip()
                layer_content = str(tool_args["layer_content"]).strip()
                recent_message_count = int(tool_args["recent_message_count"])
                print(
                    f"[step={step}] compact_recent_conversation_into_layer("
                    f"layer_name={layer_name}, recent_message_count={recent_message_count})"
                )
                tool_output = _execute_compact_conversation_layer_tool(
                    layers=character_layers,
                    conversation_messages=conversation_messages,
                    layer_name=layer_name,
                    layer_content=layer_content,
                    recent_message_count=recent_message_count,
                    max_compactable_messages=current_tool_call_envelope_start_index,
                )
                # Compaction removes only messages older than the current envelope,
                # so the envelope index shifts left by exactly this count.
                current_tool_call_envelope_start_index -= recent_message_count
            elif tool_call.function.name == "compact_named_layers_into_layer":
                layer_name = str(tool_args["layer_name"]).strip()
                layer_content = str(tool_args["layer_content"]).strip()
                source_layer_names = [
                    str(item).strip() for item in tool_args["source_layer_names"]
                ]
                print(
                    f"[step={step}] compact_named_layers_into_layer("
                    f"layer_name={layer_name}, source_layer_names={source_layer_names})"
                )
                tool_output = _execute_compact_named_layers_tool(
                    layers=character_layers,
                    layer_name=layer_name,
                    layer_content=layer_content,
                    source_layer_names=source_layer_names,
                )
            elif (
                _find_layer_by_update_tool_name(
                    layers=character_layers, tool_name=tool_call.function.name
                )
                is not None
            ):
                tool_output = _execute_layer_update_tool(
                    layers=character_layers,
                    tool_name=tool_call.function.name,
                    content=str(tool_args["content"]).strip(),
                    rename_to=(
                        str(tool_args["rename_to"]).strip()
                        if "rename_to" in tool_args
                        and tool_args["rename_to"] is not None
                        else None
                    ),
                )
            else:
                raise ValueError(f"Unsupported tool call: {tool_call.function.name}")
            tool_output_for_conversation = _sanitize_tool_output_for_conversation(
                tool_name=tool_call.function.name, tool_output=tool_output
            )
            conversation_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": json.dumps(tool_output_for_conversation),
                }
            )


def _print_event(*, step: int, event_type: str, content: str) -> None:
    print(f"[{event_type} step={step}] {content}")


def _optional_env(env_name: str) -> str | None:
    value = (os.environ.get(env_name) or "").strip()
    if not value:
        return None
    return value


def run_living_companion_demo(
    *,
    companion_name: str,
    user_name: str,
    user_contact: str,
    initial_virtual_age_years: float,
    clock_rate: float,
    proactive_interval_seconds: float,
    tick_seconds: float,
    user_messages: list[str],
) -> None:
    model_catalog = ModelCatalog.default()
    transport = InMemoryChannelTransport()
    state = CompanionState(
        companion_name=companion_name,
        user_name=user_name,
        user_contact=user_contact,
        initial_virtual_age_years=initial_virtual_age_years,
        clock_rate=clock_rate,
        now=0.0,
    )
    agent = PerpetualCompanionAgent(
        state=state,
        model_catalog=model_catalog,
        model_executor=ScriptedModelExecutor(),
        channel_transport=transport,
        proactive_interval_seconds=proactive_interval_seconds,
    )

    now = 0.0
    for idx, message in enumerate(user_messages, start=1):
        now += tick_seconds
        events = agent.tick(now=now, user_message=message)
        for event in events:
            _print_event(
                step=idx,
                event_type="user_turn",
                content=(
                    f"channel={event.channel.value} model={event.metadata['model_name']} "
                    f"emotion={event.metadata['emotion']} expression={event.metadata['expression']} "
                    f"age={agent.state.virtual_age_years:.4f} msg={event.content}"
                ),
            )

    now += proactive_interval_seconds + 1.0
    proactive_events = agent.tick(now=now)
    for idx, event in enumerate(proactive_events, start=1):
        _print_event(
            step=idx,
            event_type="heartbeat",
            content=(
                f"channel={event.channel.value} model={event.metadata['model_name']} "
                f"proactive={event.metadata['proactive']} age={agent.state.virtual_age_years:.4f} "
                f"msg={event.content}"
            ),
        )


def _ensure_root_logging(level_name: str) -> None:
    import logging

    if logging.root.handlers:
        return
    level = getattr(logging, level_name)
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s %(message)s",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Perpetual agent demos with pulse/call_user and living modes"
    )
    parser.add_argument(
        "--mode",
        choices=["living", "pulse"],
        default="living",
        help="Run the scripted living companion demo, or the original pulse demo.",
    )
    parser.add_argument("--user-prompt")
    parser.add_argument("--model")
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    parser.add_argument("--companion-name", default="Ivy")
    parser.add_argument("--user-name", default="Alex")
    parser.add_argument("--user-contact", default="alex@example.com")
    parser.add_argument("--initial-virtual-age-years", type=float, default=2.0)
    parser.add_argument("--clock-rate", type=float, default=10.0)
    parser.add_argument("--proactive-interval-seconds", type=float, default=300.0)
    parser.add_argument("--tick-seconds", type=float, default=90.0)
    parser.add_argument(
        "--telegram-bot-token-env",
        default="TELEGRAM_BOT_TOKEN",
        help="Environment variable name storing Telegram bot token.",
    )
    parser.add_argument(
        "--telegram-chat-id",
        default=None,
        help=(
            "Telegram chat id to target. If omitted, first incoming message sets target chat."
        ),
    )
    parser.add_argument(
        "--telegram-poll-timeout-seconds",
        type=int,
        default=20,
        help="Long-poll timeout for Telegram getUpdates in --telegram-llm mode.",
    )
    parser.add_argument(
        "--telegram-llm",
        action="store_true",
        help=(
            "Telegram long-poll inbox + OpenAI chat (drain before each completion); "
            "requires --model and API key env."
        ),
    )
    parser.add_argument(
        "--telegram-llm-max-user-turns",
        type=int,
        default=50,
        help="Max inbound Telegram batches handled (each batch may merge multiple updates).",
    )
    parser.add_argument(
        "--telegram-llm-no-merge-batches",
        action="store_true",
        help="Append one chat message per Telegram update instead of merging into one user turn.",
    )
    parser.add_argument(
        "--telegram-llm-pulse-tool",
        action="store_true",
        help="Register pulse(seconds) tool for the Telegram LLM session.",
    )
    parser.add_argument(
        "--user-message",
        action="append",
        default=[],
        help="Repeat this flag to feed multiple user turns in living mode.",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help=(
            "Stderr logging level when the root logger has no handlers yet "
            "(normal CLI runs)."
        ),
    )
    args = parser.parse_args()

    _ensure_root_logging(args.log_level)

    if args.mode == "pulse":
        assert args.user_prompt, "--user-prompt is required in pulse mode"
        assert args.model, "--model is required in pulse mode"
        run_perpetual_agent(
            user_prompt=args.user_prompt,
            model=args.model,
            max_steps=args.max_steps,
            client=None,
            api_key_env=args.api_key_env,
            base_url=args.base_url,
        )
        return

    if args.telegram_llm:
        assert args.model, "--model is required with --telegram-llm"
        telegram_bot_token = _required_env(args.telegram_bot_token_env)
        tools = [PULSE_TOOL_DEFINITION] if args.telegram_llm_pulse_tool else None
        run_telegram_llm_session(
            model=args.model,
            api_key_env=args.api_key_env,
            base_url=args.base_url,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=args.telegram_chat_id or _optional_env("TELEGRAM_CHAT_ID"),
            telegram_poll_timeout_seconds=args.telegram_poll_timeout_seconds,
            max_user_turns=args.telegram_llm_max_user_turns,
            merge_telegram_batches=not args.telegram_llm_no_merge_batches,
            tools=tools,
        )
        return

    default_user_messages = [
        "I feel lonely tonight. Can you text me?",
        "Please call me and help me think through tomorrow's priorities.",
        "Email me a reflective summary of what we discussed.",
    ]
    user_messages = args.user_message or default_user_messages
    run_living_companion_demo(
        companion_name=args.companion_name,
        user_name=args.user_name,
        user_contact=args.user_contact,
        initial_virtual_age_years=args.initial_virtual_age_years,
        clock_rate=args.clock_rate,
        proactive_interval_seconds=args.proactive_interval_seconds,
        tick_seconds=args.tick_seconds,
        user_messages=user_messages,
    )


if __name__ == "__main__":
    main()
