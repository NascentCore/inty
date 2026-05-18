"""最小可读的 Agentic Loop Demo：LLM 调用 sleep 工具后回到循环继续推理。"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass

from cyclopts import App
from dotenv import load_dotenv
from openai import OpenAI

# 关键中间步骤总结（给读者看机制而不是业务细节）：
# 1) 先把 system + user 放进 messages。
# 2) 每轮调用 LLM，让 LLM 自己决定“直接回答”还是“先调用 sleep 工具”。
# 3) 如果出现 tool_call：执行 sleep，把结果写成 role=tool 消息，再回到下一轮 LLM。
# 4) 当 LLM 不再发 tool_call，输出最终文本并结束。

SYSTEM_PROMPT = """
你是一个讲解 agentic loop 的助教。
当用户要求“等待/sleep/稍后再说”时，你必须先调用 sleep 工具，再给出最终回复。
sleep 工具只负责等待；等待后你再继续回答用户。
"""

SLEEP_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "sleep",
        "description": "按照用户要求暂停一段时间，然后把等待结果返回给 agentic loop。",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "为什么这次要等待（由 LLM 根据上下文填写）。",
                }
            },
            "required": ["reason"],
            "additionalProperties": False,
        },
    },
}


@dataclass
class SleepToolInput:
    reason: str


@dataclass
class SleepToolOutput:
    requested_seconds: int
    real_elapsed_seconds: float
    reason: str
    note: str


def _extract_sleep_seconds_from_context(messages: list[dict]) -> int:
    """
    从上下文中提取“用户要求等待几秒”。
    这里故意做成最简单实现：取最后一条 user 消息里的第一个整数。
    """
    latest_user_text = [m["content"] for m in messages if m["role"] == "user"][
        -1
    ]
    return int(re.search(r"\d+", latest_user_text).group(0))


def _execute_sleep_tool(
    messages: list[dict], tool_input: SleepToolInput
) -> SleepToolOutput:
    """
    工具执行层：根据上下文决定 sleep 秒数，然后真正阻塞等待。
    """
    seconds = _extract_sleep_seconds_from_context(messages)
    started_at = time.time()
    time.sleep(seconds)
    elapsed = time.time() - started_at
    return SleepToolOutput(
        requested_seconds=seconds,
        real_elapsed_seconds=round(elapsed, 3),
        reason=tool_input.reason,
        note="sleep 工具执行完成，控制权返回 agentic loop。",
    )


def _serialize_tool_calls(tool_calls) -> list[dict]:
    """
    把 SDK 的 tool_calls 对象转成普通 dict，写回 messages 供下一轮 LLM 读取。
    """
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


def run_agentic_loop(
    user_request: str,
    model: str,
    max_steps: int,
    api_key_env: str,
    base_url: str,
) -> None:
    """
    最小 agentic loop：
    - 只演示一个工具：sleep
    - 不做任何错误处理（故意保持“裸实现”）
    """
    load_dotenv()
    client = OpenAI(api_key=os.environ[api_key_env], base_url=base_url)

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {"role": "user", "content": user_request},
    ]

    print(f"模型: {model}")
    print(f"用户请求: {user_request}")
    print("=" * 80)

    for step in range(1, max_steps + 1):
        print(f"[Loop Step {step}] 请求 LLM ...")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[SLEEP_TOOL_DEFINITION],
            tool_choice="auto",
        )
        assistant_message = response.choices[0].message
        tool_calls = assistant_message.tool_calls or []
        assistant_content = assistant_message.content or ""

        if not tool_calls:
            messages.append({"role": "assistant", "content": assistant_content})
            print(f"[Loop Step {step}] LLM 最终回复: {assistant_content}")
            print("=" * 80)
            print("Agentic loop 结束：本轮没有 tool call。")
            return

        print(f"[Loop Step {step}] LLM 触发了 {len(tool_calls)} 个工具调用。")
        messages.append(
            {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": _serialize_tool_calls(tool_calls),
            }
        )

        for tool_call in tool_calls:
            print(
                f"[Loop Step {step}] 执行工具: {tool_call.function.name} "
                f"args={tool_call.function.arguments}"
            )
            tool_args = json.loads(tool_call.function.arguments)
            tool_input = SleepToolInput(reason=tool_args["reason"])
            tool_output = _execute_sleep_tool(
                messages=messages, tool_input=tool_input
            )
            tool_output_json = json.dumps(
                asdict(tool_output), ensure_ascii=False
            )
            print(f"[Loop Step {step}] 工具返回: {tool_output_json}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": tool_output_json,
                }
            )

    print("=" * 80)
    print(f"达到 max_steps={max_steps}，停止循环。")


app = App(help="Agentic loop sleep demo（无错误处理教学版）")


@app.default
def main(
    user_request: str,
    model: str,
    max_steps: int = 8,
    api_key_env: str = "OPENROUTER_API_KEY",
    base_url: str = "https://openrouter.ai/api/v1",
) -> None:
    """
    运行示例：
    python -m experimental.agentic_loop_sleep_demo.main \
      --user-request "请先 sleep 3 秒，然后告诉我你回来了" \
      --model "z-ai/glm-4.5-air:free"
    """
    run_agentic_loop(
        user_request=user_request,
        model=model,
        max_steps=max_steps,
        api_key_env=api_key_env,
        base_url=base_url,
    )


if __name__ == "__main__":
    app()
