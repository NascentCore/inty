#!/usr/bin/env python3
"""
Demo: call LLM with high thinking mode and print:
1) thinking token usage
2) final model response
"""

import json
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion

PROMPT = "Solve this briefly: If x + y = 10 and x - y = 4, what are x and y?"
DEFAULT_PROVIDER = "openrouter"


def _read_api_key_from_config() -> str:
    config_path = Path(__file__).resolve().parents[2] / "config.yaml"
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    api_key = config["agent"]["api_key"]
    if not isinstance(api_key, str) or api_key == "":
        raise RuntimeError(
            "config.yaml has no valid agent.api_key. "
            "Set OPENROUTER_API_KEY or update config.yaml."
        )
    return api_key


def _resolve_openrouter_api_key() -> str:
    env_key = os.getenv("OPENROUTER_API_KEY")
    if env_key:
        return env_key
    return _read_api_key_from_config()


def _read_reasoning_tokens(response: ChatCompletion) -> int:
    usage = response.usage
    if usage is None or usage.completion_tokens_details is None:
        return 0
    return usage.completion_tokens_details.reasoning_tokens or 0


def _read_final_text(response: ChatCompletion) -> str:
    message = response.choices[0].message
    if message.content:
        return message.content
    return "(No final response text returned.)"


def _read_optional_reasoning_text(response: ChatCompletion) -> str:
    message_dict: dict[str, Any] = response.choices[0].message.model_dump()
    reasoning_text = message_dict.get("reasoning")
    if isinstance(reasoning_text, str) and reasoning_text.strip():
        return reasoning_text
    return "(Reasoning text is not exposed by this provider/model response.)"


def _run_openrouter_demo() -> None:
    api_key = _resolve_openrouter_api_key()
    model = os.getenv("THINKING_DEMO_MODEL", "google/gemini-2.5-pro")
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    response = client.chat.completions.create(
        model=model,
        reasoning_effort="high",
        max_completion_tokens=2048,
        messages=[
            {"role": "system", "content": "You are a concise math tutor."},
            {"role": "user", "content": PROMPT},
        ],
    )

    usage_dict = response.usage.model_dump() if response.usage else {}
    reasoning_tokens = _read_reasoning_tokens(response)
    response_text = _read_final_text(response)
    reasoning_text = _read_optional_reasoning_text(response)

    print("=== Provider ===")
    print("openrouter")
    print()

    print("=== Prompt ===")
    print(PROMPT)
    print()

    print("=== Thinking Mode ===")
    print("reasoning_effort=high")
    print()

    print("=== Thinking Tokens ===")
    print(reasoning_tokens)
    print()

    print("=== Raw Usage (for verification) ===")
    print(json.dumps(usage_dict, ensure_ascii=False, indent=2))
    print()

    print("=== Thinking Content (if available) ===")
    print(reasoning_text)
    print()

    print("=== Final Response ===")
    print(response_text)


def main() -> None:
    load_dotenv()
    provider = os.getenv("THINKING_DEMO_PROVIDER", DEFAULT_PROVIDER).lower()
    if provider != "openrouter":
        raise RuntimeError(
            "Only THINKING_DEMO_PROVIDER=openrouter is supported in this demo."
        )
    _run_openrouter_demo()


if __name__ == "__main__":
    main()
