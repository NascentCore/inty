"""Minimal perpetual agent demo with pulse + phone-call tools."""

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

SYSTEM_PROMPT_TEMPLATE = """
You are a perpetual demo agent.
Current pulse counter: {pulse_count}

You can call exactly two tools:
- pulse(seconds: integer)
- call_user(phone_number: string, reason: string)

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
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _render_system_prompt(pulse_count=pulse_count)},
        {"role": "user", "content": user_prompt},
    ]
    forced_tool_choice = _tool_choice_for_user_prompt(user_prompt=user_prompt)

    for step in range(1, max_steps + 1):
        messages[0]["content"] = _render_system_prompt(pulse_count=pulse_count)

        response = active_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[PULSE_TOOL_DEFINITION, CALL_USER_TOOL_DEFINITION],
            tool_choice=forced_tool_choice if step == 1 else "auto",
        )
        assistant_message = response.choices[0].message
        assistant_content = assistant_message.content or ""
        tool_calls = assistant_message.tool_calls or []

        if not tool_calls:
            messages.append({"role": "assistant", "content": assistant_content})
            print(f"[step={step}] assistant: {assistant_content}")
            continue

        messages.append(
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
            else:
                raise ValueError(f"Unsupported tool call: {tool_call.function.name}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": json.dumps(tool_output),
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Perpetual agent demo with pulse + call_user tools"
    )
    parser.add_argument("--user-prompt", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    args = parser.parse_args()

    run_perpetual_agent(
        user_prompt=args.user_prompt,
        model=args.model,
        max_steps=args.max_steps,
        client=None,
        api_key_env=args.api_key_env,
        base_url=args.base_url,
    )


if __name__ == "__main__":
    main()
