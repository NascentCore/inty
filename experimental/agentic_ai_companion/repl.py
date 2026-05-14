"""REPL 主循环与单轮处理。"""

from __future__ import annotations

import json

from langsmith.run_helpers import trace

EMPTY_RESPONSE = "(E.M.P.T.Y.)"


def _handle_api_response(
    messages: list,
    msg,
    char_name: str,
    turn: int,
    tool_types: dict,
    tool_context_types: dict,
    process_response_with_tools,
    tool_executors: dict,
    get_gemini_client,
    logger,
    *,
    build_system_messages=None,
    user_name: str | None = None,
) -> tuple[bool, list, str | None]:
    """
    处理单次 API 响应。返回 (是否结束本轮, 更新后的 messages, 新的 pending_image_path)。
    """
    has_tool_calls = bool(getattr(msg, "tool_calls", None))
    if not has_tool_calls:
        raw = getattr(msg, "content", None)
        content = (raw if isinstance(raw, str) else "").strip()
        messages.append({"role": "assistant", "content": content})
        display = content or EMPTY_RESPONSE
        logger.info("第 %d 轮对话结束，assistant content 长度=%d", turn, len(content))
        print(f"{char_name}> {display}\n")
        return True, messages, None

    tool_name = msg.tool_calls[0].function.name

    logger.info(
        "执行 TERMINAL 工具 %s，msg: %s",
        tool_name,
        json.dumps(msg.model_dump(), indent=2),
    )
    assistant_text = (msg.content or "").strip()
    if assistant_text:
        print(f"{char_name}> {assistant_text}\n")
    out = process_response_with_tools(
        messages,
        msg,
        tool_executors=tool_executors,
        tool_types=tool_types,
        tool_context_types=tool_context_types,
        get_gemini_client=get_gemini_client,
        _logger=logger,
        build_system_messages=build_system_messages,
        char_name=char_name,
        user_name=user_name,
    )
    messages = out.messages
    new_pending = out.image_path
    # if messages[-1]["role"] == "user":
    messages.append({"role": "assistant", "content": out.content})
    # 第 2 块：工具结果
    tool_display = (out.tool_result or "") + " " + (new_pending or "")
    if tool_display:
        print(f"{char_name}> {tool_display}\n")
    logger.info(
        "第 %d 轮对话结束，assistant content 长度=%d，附带图片路径=%s",
        turn,
        len(out.content or ""),
        new_pending is not None,
    )
    return True, messages, new_pending


def _execute_turn(
    messages: list,
    line: str,
    turn: int,
    char_name: str,
    user_name: str,
    model: str,
    client,
    tools: list,
    tool_types: dict,
    tool_context_types: dict,
    process_response_with_tools,
    tool_executors: dict,
    get_gemini_client,
    logger,
    *,
    build_system_messages=None,
    memory_compactor=None,
) -> list:
    """执行单轮对话：用户输入 -> API 调用 -> 可能多轮 tool 循环 -> 输出。"""
    messages.append({"role": "user", "content": line})
    if memory_compactor is not None:
        outcome = memory_compactor.maybe_compact(messages=messages, turn=turn)
        messages = outcome.messages
        logger.info(
            "memory_compaction did_compact=%s reason=%s chars_before=%d chars_after=%d",
            outcome.did_compact,
            outcome.reason,
            outcome.approx_chars_before,
            outcome.approx_chars_after,
        )

    with trace(
        "AgenticAICompanion_turn",
        run_type="chain",
        inputs={"user_input": line, "messages_count": len(messages)},
    ):
        round_num = 0
        while True:
            round_num += 1
            logger.info(
                "API 请求 第 %d 轮 turn=%d，messages 条数=%d",
                round_num,
                turn,
                len(messages),
            )
            tool_msg_count = sum(1 for m in messages if m.get("role") == "tool")
            logger.info("本次 API 请求 messages 中 tool 消息数量: %d", tool_msg_count)
            logger.info("Current messages: %s", json.dumps(messages, indent=2))
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                parallel_tool_calls=False,
            )
            _raw = resp.model_dump() if hasattr(resp, "model_dump") else repr(resp)
            if isinstance(_raw, dict):
                logger.info("API raw response: %s", json.dumps(_raw, indent=2))
            else:
                logger.info("API raw response: %s", _raw)
            msg = resp.choices[0].message
            has_tc = bool(getattr(msg, "tool_calls", None))
            logger.info("API 响应 第 %d 轮，has_tool_calls=%s", round_num, has_tc)

            done, messages, _ = _handle_api_response(
                messages,
                msg,
                char_name,
                turn,
                tool_types,
                tool_context_types,
                process_response_with_tools,
                tool_executors,
                get_gemini_client,
                logger,
                build_system_messages=build_system_messages,
                user_name=user_name,
            )
            if done:
                break
    return messages


def run_repl(
    char_name: str,
    user_name: str,
    model: str,
    *,
    build_system_messages,
    create_openai_client,
    get_gemini_client,
    tools: list,
    tool_executors: dict,
    tool_types: dict,
    tool_context_types: dict,
    process_response_with_tools,
    logger,
    memory_compactor=None,
) -> None:
    logger.info(
        "REPL 启动 char_name=%s user_name=%s model=%s", char_name, user_name, model
    )
    from . import tools as tools_module

    tools_module.reset_sent_image_paths()
    system_messages = build_system_messages(char_name, user_name)
    client = create_openai_client()
    messages: list = [*system_messages]
    print(f"角色: {char_name} | 用户: {user_name} | 模型: {model}")
    print("输入内容后回车发送，空行跳过，Ctrl+C 退出。\n")
    turn = 0

    with trace(
        "AgenticAICompanion_session",
        run_type="chain",
        inputs={"char_name": char_name, "user_name": user_name, "model": model},
    ):
        while True:
            try:
                line = input(f"{user_name}> ").strip()
            except (KeyboardInterrupt, EOFError):
                logger.info("用户中断或 EOF，退出 REPL")
                break
            if not line:
                logger.debug("空行跳过")
                continue

            turn += 1
            logger.info(
                "第 %d 轮对话，用户输入长度=%d: %s",
                turn,
                len(line),
                line[:80] + ("..." if len(line) > 80 else ""),
            )

            messages = _execute_turn(
                messages,
                line,
                turn,
                char_name,
                user_name,
                model,
                client,
                tools,
                tool_types,
                tool_context_types,
                process_response_with_tools,
                tool_executors,
                get_gemini_client,
                logger,
                build_system_messages=build_system_messages,
                memory_compactor=memory_compactor,
            )
