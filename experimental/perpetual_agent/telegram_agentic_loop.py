"""Telegram + OpenAI: drain inbound channel before each LLM completion (agentic sub-loop)."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Callable

from .channel_inbox import TelegramInbox
from .telegram_channel import TelegramBotApi

logger = logging.getLogger(__name__)

# Inside ``run_telegram_agentic_completion_loop``, user turns are already collected by the
# outer ``run_telegram_llm_session`` wait loop. Drains before each completion only need to
# pick up *queued* updates (e.g. during tool rounds); long-polling here duplicated the outer
# wait and added up to ``poll_timeout_seconds`` per user message before the LLM call.
_TELEGRAM_COMPLETION_LOOP_DRAIN_POLL_S = 0

DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant talking to the user over Telegram.
Reply concisely. The user messages may be prefixed with Telegram metadata lines."""


def _monotonic_elapsed_ms(start: float) -> float:
    return (time.monotonic() - start) * 1000


def _log_telegram_llm_phase_timing(
    *,
    completion_step: int,
    drain_wall_ms: float,
    openai_completion_ms: float,
    send_message_ms: float | None,
) -> None:
    if send_message_ms is None:
        logger.info(
            "telegram_llm phase_timing step=%d drain_wall_ms=%.1f "
            "openai_completion_ms=%.1f send_message_ms=n/a (tool_round)",
            completion_step,
            drain_wall_ms,
            openai_completion_ms,
        )
    else:
        logger.info(
            "telegram_llm phase_timing step=%d drain_wall_ms=%.1f "
            "openai_completion_ms=%.1f send_message_ms=%.1f",
            completion_step,
            drain_wall_ms,
            openai_completion_ms,
            send_message_ms,
        )


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


def _execute_pulse_tool(seconds: int) -> dict[str, Any]:
    time.sleep(seconds)
    return {"slept_seconds": seconds, "note": "pulse complete"}


PULSE_TOOL_DEFINITION: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "pulse",
        "description": "Sleep for the provided seconds then return.",
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


def _run_tool(name: str, arguments_json: str) -> dict[str, Any]:
    if name == "pulse":
        args = json.loads(arguments_json)
        return _execute_pulse_tool(int(args["seconds"]))
    raise ValueError(f"unsupported tool: {name}")


def _tool_names_from_definitions(
    tools: list[dict[str, Any]] | None,
) -> list[str]:
    if not tools:
        return []
    names: list[str] = []
    for t in tools:
        fn = t.get("function")
        if isinstance(fn, dict) and fn.get("name"):
            names.append(str(fn["name"]))
    return names


def _usage_one_liner(response: Any) -> str:
    usage = getattr(response, "usage", None)
    if usage is None:
        return "n/a"
    if hasattr(usage, "model_dump"):
        d = usage.model_dump()
        return (
            f"prompt_tokens={d.get('prompt_tokens')} "
            f"completion_tokens={d.get('completion_tokens')} "
            f"total_tokens={d.get('total_tokens')}"
        )
    return str(usage)


def _truncate_for_info_log(text: str | None, limit: int = 2000) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...(truncated, len={len(text)})"


def _request_payload_for_debug_log(
    *,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    tool_choice: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": model, "messages": messages}
    if tools is not None:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    return payload


def _response_payload_for_debug_log(response: Any) -> dict[str, Any]:
    choice = response.choices[0]
    msg = choice.message
    tool_calls = getattr(msg, "tool_calls", None) or []
    payload: dict[str, Any] = {
        "id": getattr(response, "id", None),
        "model": getattr(response, "model", None),
        "finish_reason": getattr(choice, "finish_reason", None),
        "message": {
            "role": getattr(msg, "role", None),
            "content": msg.content,
            "tool_calls": (
                _serialize_tool_calls(tool_calls) if tool_calls else None
            ),
        },
    }
    usage = getattr(response, "usage", None)
    if usage is not None:
        if hasattr(usage, "model_dump"):
            payload["usage"] = usage.model_dump()
        else:
            payload["usage"] = repr(usage)
    return payload


def run_telegram_agentic_completion_loop(
    *,
    client: Any,
    model: str,
    messages: list[dict[str, Any]],
    inbox: TelegramInbox,
    bot_api: TelegramBotApi,
    merge_batches: bool,
    tools: list[dict[str, Any]] | None,
) -> str:
    """Drain Telegram before **each** `chat.completions.create` call; return final assistant text."""
    chat_id = inbox.bound_chat_id
    if chat_id is None:
        raise ValueError(
            "TelegramInbox.bound_chat_id must be set (drain user messages first)"
        )

    completion_step = 0
    while True:
        t_d0 = time.monotonic()
        inbox.drain_into_llm_messages(
            messages,
            merge_batches=merge_batches,
            poll_timeout_override=_TELEGRAM_COMPLETION_LOOP_DRAIN_POLL_S,
        )
        drain_wall_ms = _monotonic_elapsed_ms(t_d0)

        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        tool_choice: str | None = None
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
            tool_choice = "auto"

        completion_step += 1
        logger.info(
            "telegram_llm completion_request step=%d model=%s transcript_messages=%d tool_names=%s",
            completion_step,
            model,
            len(messages),
            _tool_names_from_definitions(tools),
        )
        logger.debug(
            "telegram_llm completion_request_payload step=%d %s",
            completion_step,
            json.dumps(
                _request_payload_for_debug_log(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                ),
                ensure_ascii=False,
                default=str,
            ),
        )

        t_llm0 = time.monotonic()
        response = client.chat.completions.create(**kwargs)
        openai_completion_ms = _monotonic_elapsed_ms(t_llm0)
        assistant_message = response.choices[0].message
        tool_calls = assistant_message.tool_calls or []
        content = assistant_message.content or ""

        finish_reason = getattr(response.choices[0], "finish_reason", None)
        tc_summary = [getattr(tc.function, "name", "?") for tc in tool_calls]
        logger.info(
            "telegram_llm completion_response step=%d finish_reason=%s "
            "assistant_content_chars=%d tool_calls=%s usage=%s assistant_content=%r",
            completion_step,
            finish_reason,
            len(content or ""),
            tc_summary,
            _usage_one_liner(response),
            _truncate_for_info_log(content),
        )
        logger.debug(
            "telegram_llm completion_response_payload step=%d %s",
            completion_step,
            json.dumps(
                _response_payload_for_debug_log(response),
                ensure_ascii=False,
                default=str,
            ),
        )

        if not tool_calls:
            messages.append({"role": "assistant", "content": content})
            t_send0 = time.monotonic()
            bot_api.send_message(chat_id=chat_id, text=content)
            send_message_ms = _monotonic_elapsed_ms(t_send0)
            _log_telegram_llm_phase_timing(
                completion_step=completion_step,
                drain_wall_ms=drain_wall_ms,
                openai_completion_ms=openai_completion_ms,
                send_message_ms=send_message_ms,
            )
            return content

        _log_telegram_llm_phase_timing(
            completion_step=completion_step,
            drain_wall_ms=drain_wall_ms,
            openai_completion_ms=openai_completion_ms,
            send_message_ms=None,
        )
        messages.append(
            {
                "role": "assistant",
                "content": content,
                "tool_calls": _serialize_tool_calls(tool_calls),
            }
        )
        for tool_call in tool_calls:
            name = tool_call.function.name
            result = _run_tool(name, tool_call.function.arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )


def run_telegram_llm_session(
    *,
    model: str,
    api_key_env: str,
    base_url: str,
    telegram_bot_token: str,
    telegram_chat_id: str | None,
    telegram_poll_timeout_seconds: int,
    max_user_turns: int,
    merge_telegram_batches: bool = True,
    client: Any | None = None,
    tools: list[dict[str, Any]] | None = None,
    system_prompt: str | None = None,
    bot_api: TelegramBotApi | None = None,
    inbox_factory: Callable[[TelegramBotApi], TelegramInbox] | None = None,
) -> None:
    """Block on Telegram user turns, run agentic LLM loop (drain-before-each-completion), reply via Telegram."""
    active_bot = bot_api or TelegramBotApi(bot_token=telegram_bot_token)
    active_client = client or _create_openai_client(api_key_env, base_url)

    def _default_inbox(api: TelegramBotApi) -> TelegramInbox:
        return TelegramInbox(
            bot_api=api,
            poll_timeout_seconds=telegram_poll_timeout_seconds,
            bound_chat_id=telegram_chat_id,
        )

    inbox = (inbox_factory or _default_inbox)(active_bot)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT}
    ]

    handled_user_batches = 0
    while handled_user_batches < max_user_turns:
        while True:
            n = inbox.drain_into_llm_messages(
                messages, merge_batches=merge_telegram_batches
            )
            if n > 0:
                handled_user_batches += 1
                break

        logger.info(
            "telegram_llm user_batch=%s/%s message_count=%d",
            handled_user_batches,
            max_user_turns,
            len(messages),
        )
        run_telegram_agentic_completion_loop(
            client=active_client,
            model=model,
            messages=messages,
            inbox=inbox,
            bot_api=active_bot,
            merge_batches=merge_telegram_batches,
            tools=tools,
        )
