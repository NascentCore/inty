"""Perpetual agent demos.

1) pulse mode: original perpetual loop with pulse(seconds) tool
2) living mode: model-orchestrated virtual companion with proactive outreach
"""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any

from .living_companion import (
    CompanionState,
    InMemoryChannelTransport,
    ModelCatalog,
    PerpetualCompanionAgent,
    ScriptedModelExecutor,
)

SYSTEM_PROMPT_TEMPLATE = """
You are a perpetual demo agent.
Current pulse counter: {pulse_count}

You can call exactly one tool:
- pulse(seconds: integer)

When pulse is called:
1) sleep for the given seconds
2) increment the pulse counter
3) continue the loop
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

    for step in range(1, max_steps + 1):
        messages[0]["content"] = _render_system_prompt(pulse_count=pulse_count)

        response = active_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[PULSE_TOOL_DEFINITION],
            tool_choice="auto",
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
            seconds = int(tool_args["seconds"])
            print(f"[step={step}] pulse(seconds={seconds})")
            time.sleep(seconds)
            pulse_count += 1

            tool_output = {
                "slept_seconds": seconds,
                "pulse_count": pulse_count,
                "note": "pulse complete, back to prompt",
            }
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": json.dumps(tool_output),
                }
            )


def _print_event(*, step: int, event_type: str, content: str) -> None:
    print(f"[{event_type} step={step}] {content}")


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Perpetual agent demos")
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
