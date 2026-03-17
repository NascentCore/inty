"""Minimal perpetual agent demo with one tool: pulse."""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Perpetual agent demo with pulse tool")
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
