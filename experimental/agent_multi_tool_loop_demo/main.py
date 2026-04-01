from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from cyclopts import App

SYSTEM_PROMPT = (
    "你是头像助手。用户要求更新头像时，必须在同一轮先调用 z_image_generate，"
    "再调用 update_profile_picture。"
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
class ToolCall:
    id: str
    name: str
    arguments: dict[str, str]


@dataclass
class AgentStep:
    content: str
    tool_calls: list[ToolCall]


@dataclass
class ExecutedToolCall:
    step: int
    name: str
    input_arguments: dict[str, str]
    resolved_arguments: dict[str, str]
    output: dict[str, str]


@dataclass
class DemoRunResult:
    loop_steps: int
    executed_tools: list[ExecutedToolCall]
    final_profile_image_url: str | None
    final_assistant_message: str


def _scripted_agent_step(messages: list[dict], step: int) -> AgentStep:
    has_tool_result = any(m["role"] == "tool" for m in messages)
    if step == 1 and not has_tool_result:
        return AgentStep(
            content="我将先生成头像，再更新你的 profile picture。",
            tool_calls=[
                ToolCall(
                    id="call_z_image_generate_1",
                    name="z_image_generate",
                    arguments={
                        "prompt": "professional male portrait, warm lighting, clean background",
                        "style": "photorealistic",
                    },
                ),
                ToolCall(
                    id="call_update_profile_picture_1",
                    name="update_profile_picture",
                    arguments={"image_url": "$tool:z_image_generate.image_url"},
                ),
            ],
        )

    return AgentStep(
        content="头像已更新完成。新头像来自 z-image 生成结果。",
        tool_calls=[],
    )


def _run_z_image_generate_tool(arguments: dict[str, str]) -> dict[str, str]:
    prompt_slug = arguments["prompt"].replace(" ", "-")[:24]
    generated_url = f"https://z-image.local/generated/{prompt_slug}.png"
    return {
        "image_url": generated_url,
        "provider": "z-image",
        "style": arguments["style"],
    }


def _run_update_profile_picture_tool(
    profile_state: dict[str, str | None],
    arguments: dict[str, str],
) -> dict[str, str]:
    profile_state["profile_image_url"] = arguments["image_url"]
    return {
        "status": "updated",
        "profile_image_url": arguments["image_url"],
    }


def _resolve_argument_placeholders(
    arguments: dict[str, str],
    tool_outputs: dict[str, dict[str, str]],
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for key, value in arguments.items():
        if isinstance(value, str) and value.startswith("$tool:"):
            _, ref = value.split(":", maxsplit=1)
            tool_name, output_key = ref.split(".", maxsplit=1)
            resolved[key] = tool_outputs[tool_name][output_key]
            continue
        resolved[key] = value
    return resolved


def run_demo(user_request: str, max_steps: int = 4) -> DemoRunResult:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_request},
    ]
    profile_state: dict[str, str | None] = {"profile_image_url": None}
    executed_tools: list[ExecutedToolCall] = []
    latest_tool_outputs: dict[str, dict[str, str]] = {}

    final_assistant_message = ""
    loop_steps = 0
    for step in range(1, max_steps + 1):
        loop_steps = step
        agent_step = _scripted_agent_step(messages=messages, step=step)
        messages.append(
            {
                "role": "assistant",
                "content": agent_step.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments, ensure_ascii=False),
                        },
                    }
                    for call in agent_step.tool_calls
                ],
            }
        )

        if not agent_step.tool_calls:
            final_assistant_message = agent_step.content
            break

        for call in agent_step.tool_calls:
            resolved_arguments = _resolve_argument_placeholders(
                arguments=call.arguments,
                tool_outputs=latest_tool_outputs,
            )
            if call.name == "z_image_generate":
                output = _run_z_image_generate_tool(arguments=resolved_arguments)
            elif call.name == "update_profile_picture":
                output = _run_update_profile_picture_tool(
                    profile_state=profile_state,
                    arguments=resolved_arguments,
                )
            else:
                raise ValueError(f"unknown tool: {call.name}")

            latest_tool_outputs[call.name] = output
            executed_tools.append(
                ExecutedToolCall(
                    step=step,
                    name=call.name,
                    input_arguments=call.arguments,
                    resolved_arguments=resolved_arguments,
                    output=output,
                )
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.name,
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
    max_steps: int = 4,
) -> None:
    print("tool_definitions:")
    print(json.dumps(TOOL_DEFINITIONS, ensure_ascii=False, indent=2))
    result = run_demo(user_request=user_request, max_steps=max_steps)
    _print_run_result(result)


if __name__ == "__main__":
    app()
