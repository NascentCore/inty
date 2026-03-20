"""Perpetual agent demos.

1) pulse mode: perpetual loop with pulse + call_user tools
2) living mode: model-orchestrated virtual companion with proactive outreach
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from xml.sax.saxutils import escape as xml_escape
from typing import Any

from .living_companion import (
    ChannelType,
    CompanionState,
    InMemoryChannelTransport,
    ModelCatalog,
    PerpetualCompanionAgent,
    ScriptedModelExecutor,
)
from .telegram_channel import TelegramBotApi, TelegramChannelTransport

SYSTEM_PROMPT_TEMPLATE = """
You are a perpetual demo agent.
Current pulse counter: {pulse_count}

You can call core tools:
- pulse(seconds: integer)
- call_user(phone_number: string, reason: string)
- compact_recent_conversation_into_layer(layer_name, layer_content, recent_message_count)
- per-layer tools named like update_layer_<layer_name> for non-conversation layers

When pulse is called:
1) sleep for the given seconds
2) increment the pulse counter
3) continue the loop

When the user asks "call me at <number>":
1) call call_user immediately with that number
2) provide a short reason for the call
3) do not ask for extra confirmation if a number is already present
""".strip()

PULSE_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "pulse",
        "description": "Sleep for the provided seconds and resume loop.",
        "parameters": {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "integer",
                    "description": "How many seconds to sleep.",
                }
            },
            "required": ["seconds"],
            "additionalProperties": False,
        },
    },
}


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


@dataclass
class CharacterLayer:
    name: str
    content: str
    is_conversation_layer: bool = False


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


def _build_default_character_layers() -> list[CharacterLayer]:
    return [
        CharacterLayer(
            name="fundamental_identity",
            content=(
                "Fundamental aspect: stable identity, mission, and non-negotiable values "
                "for the agent."
            ),
        ),
        CharacterLayer(
            name="interaction_style",
            content=(
                "Interactive aspect: preferred dialogue style, empathy strategy, and tone "
                "for user-facing responses."
            ),
        ),
        CharacterLayer(
            name="conversation",
            content=(
                "Shallowest layer. Represents current live conversation context and should "
                "remain append-only through normal dialogue."
            ),
            is_conversation_layer=True,
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


def _render_layer_message(layer: CharacterLayer) -> str:
    layer_kind = "conversation" if layer.is_conversation_layer else "character"
    return (
        f"[character_layer name={layer.name} type={layer_kind}]\n"
        f"{layer.content}"
    )


def _build_layer_messages(layers: list[CharacterLayer]) -> list[dict[str, str]]:
    _validate_character_layers(layers)
    return [{"role": "system", "content": _render_layer_message(layer)} for layer in layers]


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
    updated_name = layer.name
    if rename_to is not None:
        updated_name = _normalize_layer_name(rename_to)
        if updated_name == "conversation":
            raise ValueError("Only the shallow conversation layer may be named conversation.")
        layer.name = updated_name
    layer.content = content
    return {
        "updated_layer_name": layer.name,
        "updated_layer_tool_name": _layer_update_tool_name(layer.name),
        "layer_content": layer.content,
    }


def _extract_message_preview(message: dict[str, Any]) -> str:
    role = str(message.get("role", "unknown"))
    content = str(message.get("content", ""))
    flattened = re.sub(r"\s+", " ", content).strip()
    if not flattened:
        flattened = "<empty>"
    return f"{role}: {flattened}"


def _execute_compact_conversation_layer_tool(
    *,
    layers: list[CharacterLayer],
    conversation_messages: list[dict[str, Any]],
    layer_name: str,
    layer_content: str,
    recent_message_count: int,
) -> dict[str, Any]:
    _validate_character_layers(layers)
    if recent_message_count <= 0:
        raise ValueError("recent_message_count must be > 0")
    if recent_message_count > len(conversation_messages):
        raise ValueError(
            "recent_message_count cannot exceed current conversation message count"
        )
    normalized_name = _normalize_layer_name(layer_name)
    if normalized_name == "conversation":
        raise ValueError("Compacted layer name cannot be conversation.")
    compacted_slice = conversation_messages[-recent_message_count:]
    del conversation_messages[-recent_message_count:]

    compacted_transcript = "\n".join(
        f"- {_extract_message_preview(message)}" for message in compacted_slice
    )
    compacted_layer = CharacterLayer(
        name=normalized_name,
        content=f"{layer_content}\n\nCompacted transcript:\n{compacted_transcript}",
    )
    conversation_layer_index = len(layers) - 1
    layers.insert(conversation_layer_index, compacted_layer)
    return {
        "created_layer_name": compacted_layer.name,
        "created_layer_tool_name": _layer_update_tool_name(compacted_layer.name),
        "compacted_message_count": recent_message_count,
        "remaining_conversation_messages": len(conversation_messages),
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
    conversation_messages: list[dict[str, Any]] = [{"role": "user", "content": user_prompt}]
    forced_tool_choice = _tool_choice_for_user_prompt(user_prompt=user_prompt)

    for step in range(1, max_steps + 1):
        request_messages: list[dict[str, Any]] = [
            {"role": "system", "content": _render_system_prompt(pulse_count=pulse_count)}
        ]
        request_messages.extend(_build_layer_messages(character_layers))
        request_messages.extend(conversation_messages)
        request_tools = [
            PULSE_TOOL_DEFINITION,
            CALL_USER_TOOL_DEFINITION,
            COMPACT_CONVERSATION_TOOL_DEFINITION,
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
            conversation_messages.append({"role": "assistant", "content": assistant_content})
            print(f"[step={step}] assistant: {assistant_content}")
            continue

        conversation_messages.append(
            {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": _serialize_tool_calls(tool_calls),
            }
        )

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
                        if "rename_to" in tool_args and tool_args["rename_to"] is not None
                        else None
                    ),
                )
            else:
                raise ValueError(f"Unsupported tool call: {tool_call.function.name}")
            conversation_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": json.dumps(tool_output),
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


def run_living_companion_telegram_loop(
    *,
    companion_name: str,
    user_name: str,
    initial_virtual_age_years: float,
    clock_rate: float,
    proactive_interval_seconds: float,
    telegram_bot_token: str,
    telegram_chat_id: str | None,
    telegram_poll_timeout_seconds: int,
    telegram_max_user_turns: int,
    now_provider: Any = time.time,
    bot_api: TelegramBotApi | None = None,
) -> None:
    model_catalog = ModelCatalog.default()
    active_bot_api = bot_api or TelegramBotApi(bot_token=telegram_bot_token)
    offset: int | None = None
    current_chat_id = telegram_chat_id
    state = CompanionState(
        companion_name=companion_name,
        user_name=user_name,
        user_contact=current_chat_id or "pending_telegram_chat_id",
        initial_virtual_age_years=initial_virtual_age_years,
        clock_rate=clock_rate,
        now=0.0,
        default_channel=ChannelType.TELEGRAM,
    )
    agent = PerpetualCompanionAgent(
        state=state,
        model_catalog=model_catalog,
        model_executor=ScriptedModelExecutor(),
        channel_transport=TelegramChannelTransport(bot_api=active_bot_api),
        proactive_interval_seconds=proactive_interval_seconds,
    )
    started_at = float(now_provider())
    handled_user_turns = 0

    while handled_user_turns < telegram_max_user_turns:
        incoming_messages, offset = active_bot_api.get_text_messages(
            offset=offset,
            timeout_seconds=telegram_poll_timeout_seconds,
        )
        now = float(now_provider()) - started_at
        processed_user_turn = False

        for incoming in incoming_messages:
            if current_chat_id is None:
                current_chat_id = incoming.chat_id
                agent.state.user_contact = current_chat_id
            if incoming.chat_id != current_chat_id:
                continue

            events = agent.tick(now=now, user_message=incoming.text)
            processed_user_turn = True
            handled_user_turns += 1
            for event in events:
                _print_event(
                    step=handled_user_turns,
                    event_type="telegram_user_turn",
                    content=(
                        f"channel={event.channel.value} model={event.metadata['model_name']} "
                        f"emotion={event.metadata['emotion']} expression={event.metadata['expression']} "
                        f"age={agent.state.virtual_age_years:.4f} msg={event.content}"
                    ),
                )
            if handled_user_turns >= telegram_max_user_turns:
                break

        if processed_user_turn:
            continue
        if current_chat_id is None:
            continue
        proactive_events = agent.tick(now=now)
        for idx, event in enumerate(proactive_events, start=1):
            _print_event(
                step=idx,
                event_type="telegram_heartbeat",
                content=(
                    f"channel={event.channel.value} model={event.metadata['model_name']} "
                    f"proactive={event.metadata['proactive']} age={agent.state.virtual_age_years:.4f} "
                    f"msg={event.content}"
                ),
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
        "--telegram",
        action="store_true",
        help="Use Telegram poll/send loop for living mode communication.",
    )
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
        help="Long-poll timeout for Telegram getUpdates.",
    )
    parser.add_argument(
        "--telegram-max-user-turns",
        type=int,
        default=20,
        help="Safety cap for user turns handled in Telegram loop.",
    )
    parser.add_argument(
        "--user-message",
        action="append",
        default=[],
        help="Repeat this flag to feed multiple user turns in living mode.",
    )
    args = parser.parse_args()

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

    if args.telegram:
        telegram_bot_token = _required_env(args.telegram_bot_token_env)
        run_living_companion_telegram_loop(
            companion_name=args.companion_name,
            user_name=args.user_name,
            initial_virtual_age_years=args.initial_virtual_age_years,
            clock_rate=args.clock_rate,
            proactive_interval_seconds=args.proactive_interval_seconds,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=args.telegram_chat_id
            or _optional_env("TELEGRAM_CHAT_ID"),
            telegram_poll_timeout_seconds=args.telegram_poll_timeout_seconds,
            telegram_max_user_turns=args.telegram_max_user_turns,
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
