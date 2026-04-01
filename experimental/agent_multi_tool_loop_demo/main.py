from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

from cyclopts import App
from dotenv import load_dotenv
from openai import OpenAI

SYSTEM_PROMPT = (
    "你是头像助手。用户要求更新头像时，必须先调用 z_image_generate 生成图片，"
    "拿到工具返回 image_url 后，再调用 update_profile_picture。"
)

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "z_image_generate",
            "description": "使用 z-image 生成新的头像图片。",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "style": {"type": "string"},
                },
                "required": ["prompt", "style"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_profile_picture",
            "description": "把新图片 URL 设置成用户头像。",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_url": {"type": "string"},
                },
                "required": ["image_url"],
                "additionalProperties": False,
            },
        },
    },
]


@dataclass
class ExecutedToolCall:
    step: int
    tool_call_id: str
    name: str
    input_arguments: dict[str, str | int | float | bool]
    output: dict[str, str | int | float | bool]


@dataclass
class DemoRunResult:
    loop_steps: int
    executed_tools: list[ExecutedToolCall]
    final_profile_image_url: str | None
    final_assistant_message: str


def _run_z_image_generate_tool(
    arguments: dict[str, str | int | float | bool],
) -> dict[str, str]:
    prompt_slug = arguments["prompt"].replace(" ", "-")[:24]
    generated_url = f"https://z-image.local/generated/{prompt_slug}.png"
    return {
        "image_url": generated_url,
        "provider": "z-image",
        "style": arguments["style"],
    }


def _run_update_profile_picture_tool(
    profile_state: dict[str, str | None],
    arguments: dict[str, str | int | float | bool],
) -> dict[str, str]:
    profile_state["profile_image_url"] = arguments["image_url"]
    return {
        "status": "updated",
        "profile_image_url": arguments["image_url"],
    }


def _serialize_tool_calls(tool_calls) -> list[dict]:
    return [
        {
            "id": call.id,
            "type": call.type,
            "function": {
                "name": call.function.name,
                "arguments": call.function.arguments,
            },
        }
        for call in tool_calls
    ]


def run_demo(
    user_request: str,
    model: str = "google/gemini-2.5-flash-lite",
    max_steps: int = 6,
    api_key_env: str = "OPENROUTER_API_KEY",
    base_url: str = "https://openrouter.ai/api/v1",
    client: OpenAI | None = None,
) -> DemoRunResult:
    load_dotenv()
    runtime_client = client or OpenAI(
        api_key=os.environ[api_key_env],
        base_url=base_url,
    )
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_request},
    ]
    profile_state: dict[str, str | None] = {"profile_image_url": None}
    executed_tools: list[ExecutedToolCall] = []
    final_assistant_message = ""
    loop_steps = 0
    for step in range(1, max_steps + 1):
        loop_steps = step
        response = runtime_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )
        assistant_message = response.choices[0].message
        assistant_content = assistant_message.content or ""
        tool_calls = assistant_message.tool_calls or []

        messages.append(
            {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": _serialize_tool_calls(tool_calls),
            }
        )

        if not tool_calls:
            final_assistant_message = assistant_content
            break

        for call in tool_calls:
            tool_name = call.function.name
            call_arguments = json.loads(call.function.arguments)
            if tool_name == "z_image_generate":
                output = _run_z_image_generate_tool(arguments=call_arguments)
            elif tool_name == "update_profile_picture":
                output = _run_update_profile_picture_tool(
                    profile_state=profile_state,
                    arguments=call_arguments,
                )
            else:
                raise ValueError(f"unknown tool: {tool_name}")

            executed_tools.append(
                ExecutedToolCall(
                    step=step,
                    tool_call_id=call.id,
                    name=tool_name,
                    input_arguments=call_arguments,
                    output=output,
                )
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": tool_name,
                    "content": json.dumps(output, ensure_ascii=False),
                }
            )

    return DemoRunResult(
        loop_steps=loop_steps,
        executed_tools=executed_tools,
        final_profile_image_url=profile_state["profile_image_url"],
        final_assistant_message=final_assistant_message,
    )


def _print_run_result(result: DemoRunResult) -> None:
    print("=" * 80)
    print("Demo result")
    print("=" * 80)
    print(f"loop_steps: {result.loop_steps}")
    print(f"final_profile_image_url: {result.final_profile_image_url}")
    print(f"final_assistant_message: {result.final_assistant_message}")
    print("executed_tools:")
    for item in result.executed_tools:
        print(json.dumps(asdict(item), ensure_ascii=False))


app = App(help="多工具单轮 agent loop demo: z-image 生成后更新头像")


@app.default
def main(
    user_request: str = "I want to update my profile image",
    model: str = "google/gemini-2.5-flash-lite",
    max_steps: int = 6,
    api_key_env: str = "OPENROUTER_API_KEY",
    base_url: str = "https://openrouter.ai/api/v1",
) -> None:
    print("tool_definitions:")
    print(json.dumps(TOOL_DEFINITIONS, ensure_ascii=False, indent=2))
    result = run_demo(
        user_request=user_request,
        model=model,
        max_steps=max_steps,
        api_key_env=api_key_env,
        base_url=base_url,
    )
    _print_run_result(result)


if __name__ == "__main__":
    app()
