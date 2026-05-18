"""异步事件驱动 REPL：支持用户输入 + Heartbeat 双事件源。

替代 repl.run_repl 的同步阻塞模式，使用 asyncio + aioconsole 实现
非阻塞 stdin 读取，并行运行心跳定时器。两种事件共用 repl 模块中的
_execute_turn 和 _handle_api_response 处理逻辑。
"""

from __future__ import annotations

import asyncio

from aioconsole import ainput
from langsmith.run_helpers import trace

from .experimental_bridge import (
    ExperimentalTurnBridgeInput,
    message_snapshots_to_dicts,
    run_experimental_turn,
)
from app.core.companion_harness.contracts.turn import TurnInput, TurnOutput

from .heartbeat import (
    HeartbeatConfig,
    HeartbeatState,
    build_heartbeat_signal,
    is_heartbeat_response_silent,
)
from .repl import EMPTY_RESPONSE, _handle_api_response


def _execute_heartbeat_turn(
    messages: list,
    signal: str,
    turn: int,
    char_name: str,
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
    user_name: str | None = None,
) -> tuple[list, bool]:
    """执行一次心跳 turn：注入信号 -> LLM 决策 -> 输出或静默。

    返回 (更新后的 messages, 是否静默)。
    心跳消息以 user role 注入，保持与 OpenAI API 兼容。
    """
    messages.append({"role": "user", "content": signal})

    with trace(
        "AgenticAICompanion_heartbeat_turn",
        run_type="chain",
        inputs={"signal": signal[:200], "messages_count": len(messages)},
    ):
        logger.info(
            "Heartbeat API 请求 turn=%d，messages 条数=%d",
            turn,
            len(messages),
        )
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            parallel_tool_calls=False,
        )
        msg = resp.choices[0].message
        has_tc = bool(getattr(msg, "tool_calls", None))

        if has_tc:
            # 心跳 turn 中 LLM 也可以调用工具（如主动发图）
            logger.info("Heartbeat turn %d 触发了工具调用", turn)
            _, messages, _ = _handle_api_response(
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
            return messages, False

        raw = getattr(msg, "content", None)
        content = (raw if isinstance(raw, str) else "").strip()

        if is_heartbeat_response_silent(content):
            # 静默：不输出任何内容，但保留 assistant 消息维持上下文完整
            messages.append({"role": "assistant", "content": content})
            logger.info("Heartbeat turn %d 静默（SILENT）", turn)
            return messages, True

        # 有内容：作为主动消息输出
        messages.append({"role": "assistant", "content": content})
        display = content or EMPTY_RESPONSE
        logger.info("Heartbeat turn %d 主动消息，长度=%d", turn, len(content))
        print(f"\n{char_name}> {display}\n")
        return messages, False


async def run_async_repl(
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
    heartbeat_config: HeartbeatConfig,
) -> None:
    """异步 REPL 主循环：用户输入与心跳定时器并行运行。"""
    from . import tools as tools_module
    from .repl import _execute_turn

    logger.info(
        "Async REPL 启动 char_name=%s user_name=%s model=%s heartbeat_interval=%.1fs",
        char_name,
        user_name,
        model,
        heartbeat_config.interval_seconds,
    )
    tools_module.reset_sent_image_paths()
    system_messages = build_system_messages(char_name, user_name)
    client = create_openai_client()
    messages: list = [*system_messages]
    state = HeartbeatState()
    state.record_user_activity()
    turn = 0

    async def do_user_turn(msgs: list, line: str, t: int) -> list:
        payload = ExperimentalTurnBridgeInput(
            user_id=user_name,
            session_id=f"agentic_ai_companion:{char_name}:{user_name}",
            agent_id=char_name,
            user_text=line,
            history=msgs,
            metadata={
                "turn": t,
                "source": "agentic_ai_companion_async_repl_user",
            },
        )

        async def _prepare(turn_input: TurnInput) -> TurnInput:
            return turn_input

        def _invoke(turn_input: TurnInput) -> list:
            invocation_messages = message_snapshots_to_dicts(turn_input.history)
            return _execute_turn(
                invocation_messages,
                turn_input.user_text,
                t,
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
            )

        def _handle(_: TurnInput, updated_messages: list) -> TurnOutput:
            return TurnOutput(
                assistant_text="",
                metadata={"messages": updated_messages},
            )

        result = await run_experimental_turn(
            payload=payload,
            prepare_turn=_prepare,
            invoke_model=_invoke,
            handle_response=_handle,
        )
        return result.output.metadata["messages"]

    async def do_heartbeat_turn(
        msgs: list, signal: str, t: int
    ) -> tuple[list, bool]:
        payload = ExperimentalTurnBridgeInput(
            user_id=user_name,
            session_id=f"agentic_ai_companion:{char_name}:{user_name}",
            agent_id=char_name,
            user_text=signal,
            history=msgs,
            metadata={
                "turn": t,
                "source": "agentic_ai_companion_async_repl_heartbeat",
            },
        )

        async def _prepare(turn_input: TurnInput) -> TurnInput:
            return turn_input

        def _invoke(turn_input: TurnInput) -> tuple[list, bool]:
            invocation_messages = message_snapshots_to_dicts(turn_input.history)
            return _execute_heartbeat_turn(
                invocation_messages,
                turn_input.user_text,
                t,
                char_name,
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
                user_name=user_name,
            )

        def _handle(
            _: TurnInput, heartbeat_result: tuple[list, bool]
        ) -> TurnOutput:
            updated_messages, was_silent = heartbeat_result
            return TurnOutput(
                assistant_text="",
                metadata={
                    "messages": updated_messages,
                    "was_silent": was_silent,
                },
            )

        result = await run_experimental_turn(
            payload=payload,
            prepare_turn=_prepare,
            invoke_model=_invoke,
            handle_response=_handle,
        )
        metadata = result.output.metadata
        return metadata["messages"], metadata["was_silent"]

    print(f"角色: {char_name} | 用户: {user_name} | 模型: {model}")
    print(
        f"Heartbeat 模式已开启，间隔: {heartbeat_config.interval_seconds:.0f}s"
    )
    print("输入内容后回车发送，空行跳过，Ctrl+C 退出。\n")

    with trace(
        "AgenticAICompanion_async_session",
        run_type="chain",
        inputs={
            "char_name": char_name,
            "user_name": user_name,
            "model": model,
            "heartbeat_interval": heartbeat_config.interval_seconds,
        },
    ):
        while True:
            interval = state.compute_next_interval(
                heartbeat_config.interval_seconds
            )

            # 同时等待用户输入和心跳超时
            input_task = asyncio.ensure_future(ainput(f"{user_name}> "))

            try:
                done, _ = await asyncio.wait(
                    [input_task],
                    timeout=interval,
                )
            except asyncio.CancelledError:
                input_task.cancel()
                logger.info("Async REPL 被取消")
                break

            if input_task in done:
                try:
                    line = input_task.result().strip()
                except (KeyboardInterrupt, EOFError):
                    logger.info("用户中断或 EOF，退出 Async REPL")
                    break

                if not line:
                    logger.debug("空行跳过")
                    continue

                turn += 1
                state.record_user_activity()
                logger.info(
                    "第 %d 轮对话（用户输入），长度=%d: %s",
                    turn,
                    len(line),
                    line[:80] + ("..." if len(line) > 80 else ""),
                )
                messages = await do_user_turn(messages, line, turn)
            else:
                # 心跳超时：用户在此间隔内没有输入
                input_task.cancel()
                try:
                    await input_task
                except (asyncio.CancelledError, EOFError):
                    pass

                turn += 1
                logger.info(
                    "Heartbeat 触发 turn=%d（连续静默=%d，当前间隔=%.1fs）",
                    turn,
                    state.consecutive_silent_count,
                    interval,
                )
                signal = build_heartbeat_signal(state, messages)
                messages, was_silent = await do_heartbeat_turn(
                    messages, signal, turn
                )
                state.record_heartbeat(was_silent)

                if (
                    state.consecutive_silent_count
                    >= heartbeat_config.max_consecutive_silent
                ):
                    logger.info(
                        "连续静默达到上限 %d 次，暂停心跳（等待用户下一次输入后恢复）",
                        heartbeat_config.max_consecutive_silent,
                    )
                    try:
                        line = (await ainput(f"{user_name}> ")).strip()
                    except (KeyboardInterrupt, EOFError):
                        logger.info("用户中断或 EOF，退出 Async REPL")
                        break
                    if line:
                        turn += 1
                        state.record_user_activity()
                        messages = await do_user_turn(messages, line, turn)
