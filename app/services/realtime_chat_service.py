"""
CREATED_BY_AGENT

聊天实时会话（WebSocket）支持：
- 双向长连接（接收用户消息 / 抢话事件；推送 AI 流式输出）
- 抢话：取消当前生成，并将“被打断”上下文注入下一轮提示词（不落库到聊天历史，避免前端展示）
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from fastapi import WebSocket
from langchain_core.messages import HumanMessage
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.core.agent.agent import agent_manager
from app.services import agent_service, chat_history_service, chat_service
from app.services.cache_service import cache_service
from app.services.global_services import subscription_service


INTERRUPTION_CACHE_TTL_SECONDS = 5 * 60
INTERRUPTION_MAX_QUOTE_CHARS = 600


def _interrupt_cache_key(session_id: str) -> str:
    return f"chat_interrupt:{session_id}"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _build_interruption_system_prompt(partial_assistant_text: str) -> str:
    clipped = (partial_assistant_text or "")[:INTERRUPTION_MAX_QUOTE_CHARS]
    # 这里的提示词是“下一轮”用的：既不续写被打断的话，也不提及系统机制。
    return (
        "你刚才在输出时被用户打断了。不要继续刚才未说完的话，也不要提及你被打断/系统/提示词等实现细节。"
        "先自然地承接用户最新一句话并继续对话。"
        + (f"\n（你刚才已输出的未完成片段：{clipped}）" if clipped else "")
    )


@dataclass
class _ConnectionState:
    websocket: WebSocket
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


@dataclass
class _SessionRuntime:
    connections: Dict[str, _ConnectionState] = field(default_factory=dict)
    active_generation_task: Optional[asyncio.Task] = None
    interrupt_event: asyncio.Event = field(default_factory=asyncio.Event)
    active_generation_id: Optional[str] = None
    active_partial_text: str = ""


class RealtimeChatService:
    def __init__(self) -> None:
        self._sessions: Dict[str, _SessionRuntime] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket) -> str:
        connection_id = uuid.uuid4().hex
        async with self._lock:
            runtime = self._sessions.setdefault(session_id, _SessionRuntime())
            runtime.connections[connection_id] = _ConnectionState(websocket=websocket)
        return connection_id

    async def disconnect(self, session_id: str, connection_id: str) -> None:
        async with self._lock:
            runtime = self._sessions.get(session_id)
            if not runtime:
                return
            runtime.connections.pop(connection_id, None)
            if runtime.connections:
                return
            self._sessions.pop(session_id, None)

    async def interrupt(self, session_id: str, reason: str = "barge_in") -> None:
        async with self._lock:
            runtime = self._sessions.get(session_id)
            if not runtime or not runtime.active_generation_task:
                return
            runtime.interrupt_event.set()
            task = runtime.active_generation_task
            runtime.active_generation_task.cancel()

        await self._broadcast(
            session_id,
            {
                "type": "assistant_interrupted",
                "reason": reason,
                "generation_id": runtime.active_generation_id,
                "ts_ms": _now_ms(),
            },
        )

        # 尽量等待取消收尾，以确保中断上下文能被写入缓存供下一轮提示词使用。
        try:
            await asyncio.wait_for(task, timeout=1.5)
        except asyncio.TimeoutError:
            return
        except Exception:
            return

    async def handle_user_message(
        self,
        *,
        db: AsyncSession,
        current_user: schemas.User,
        agent_id: str,
        message: str,
        client_message_id: Optional[str] = None,
    ) -> None:
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )
        session_id = generate_session_id(chat.id)

        # 忙碌时的新消息视为“抢话”：先中断上一轮。
        await self.interrupt(session_id, reason="implicit_barge_in")

        is_allowed, used_count, daily_limit = (
            await subscription_service.check_chat_limit(db, current_user)
        )
        if not is_allowed:
            await self._broadcast(
                session_id,
                {
                    "type": "error",
                    "error": "usage_limit",
                    "message": "聊天次数已达上限",
                    "extra": {"used_count": used_count, "daily_limit": daily_limit},
                },
            )
            return

        try:
            chat_history_service.add_user_message(session_id, message)
        except Exception as e:
            logger.warning(f"保存用户消息失败（不中断实时对话）: {str(e)}")

        generation_id = f"gen_{uuid.uuid4().hex}"

        await self._broadcast(
            session_id,
            {
                "type": "ack",
                "event": "user_message",
                "client_message_id": client_message_id,
                "generation_id": generation_id,
                "ts_ms": _now_ms(),
            },
        )

        await self._start_generation(
            db=db,
            current_user=current_user,
            agent_id=agent_id,
            chat_id=chat.id,
            session_id=session_id,
            user_message=message,
            generation_id=generation_id,
        )

    async def _start_generation(
        self,
        *,
        db: AsyncSession,
        current_user: schemas.User,
        agent_id: str,
        chat_id: str,
        session_id: str,
        user_message: str,
        generation_id: str,
    ) -> None:
        async with self._lock:
            runtime = self._sessions.setdefault(session_id, _SessionRuntime())
            runtime.interrupt_event.clear()
            runtime.active_generation_id = generation_id
            runtime.active_partial_text = ""

            task = asyncio.create_task(
                self._run_generation(
                    db=db,
                    current_user=current_user,
                    agent_id=agent_id,
                    chat_id=chat_id,
                    session_id=session_id,
                    user_message=user_message,
                    generation_id=generation_id,
                )
            )
            runtime.active_generation_task = task

    async def _run_generation(
        self,
        *,
        db: AsyncSession,
        current_user: schemas.User,
        agent_id: str,
        chat_id: str,
        session_id: str,
        user_message: str,
        generation_id: str,
    ) -> None:
        interruption_prompt = self._pop_interruption_prompt(session_id)

        try:
            agent_data = await agent_service.get_agent_for_chat(db, agent_id=agent_id)
            if not agent_data:
                raise ValueError("Agent not found")
            agent = await agent_manager.get_agent(agent_data)
            chat_settings = await chat_service.get_or_create_chat_settings(
                db,
                chat_id=chat_id,
                user_id=current_user.id,
                agent_id=agent_id,
            )

            messages = [HumanMessage(content=user_message)]
            async for msg_chunk, _metadata in agent.chat_stream(
                user_id=current_user.id,
                session_id=session_id,
                messages=messages,
                db_session=db,
                chat_settings=chat_settings,
                interruption_prompt=interruption_prompt,
            ):
                delta = getattr(msg_chunk, "content", "") or ""
                if not delta:
                    continue
                await self._append_partial(session_id, delta)
                await self._broadcast(
                    session_id,
                    {
                        "type": "assistant_delta",
                        "generation_id": generation_id,
                        "content": delta,
                        "ts_ms": _now_ms(),
                    },
                )

            full_text = await self._get_partial(session_id)
            if full_text:
                message_id = await chat_history_service.add_ai_message(
                    db=db,
                    session_id=session_id,
                    message=full_text,
                    agent_id=agent_id,
                )
            else:
                message_id = None

            await self._broadcast(
                session_id,
                {
                    "type": "assistant_end",
                    "generation_id": generation_id,
                    "finish_reason": "stop",
                    "message_id": message_id,
                    "ts_ms": _now_ms(),
                },
            )

        except asyncio.CancelledError:
            partial = await self._get_partial(session_id)
            if partial:
                self._store_interruption(session_id, partial)
                await chat_history_service.add_ai_message(
                    db=db,
                    session_id=session_id,
                    message=partial,
                    agent_id=agent_id,
                    meta_data={"interrupted": True, "interrupted_at_ms": _now_ms()},
                )
            raise
        except Exception as e:
            logger.error(f"实时生成失败: session_id={session_id}, err={str(e)}")
            await self._broadcast(
                session_id, {"type": "error", "error": "server_error", "message": str(e)}
            )
        finally:
            async with self._lock:
                runtime = self._sessions.get(session_id)
                if runtime and runtime.active_generation_id == generation_id:
                    runtime.active_generation_task = None
                    runtime.active_generation_id = None
                    runtime.interrupt_event.clear()

    def _store_interruption(self, session_id: str, partial_text: str) -> None:
        cache_service.session_cache.set(
            _interrupt_cache_key(session_id),
            {"partial": partial_text, "ts_ms": _now_ms()},
            ttl=INTERRUPTION_CACHE_TTL_SECONDS,
        )

    def _pop_interruption_prompt(self, session_id: str) -> Optional[str]:
        key = _interrupt_cache_key(session_id)
        value = cache_service.session_cache.get(key)
        if not value:
            return None
        cache_service.session_cache.delete(key)
        partial = ""
        if isinstance(value, dict):
            partial = str(value.get("partial") or "")
        return _build_interruption_system_prompt(partial)

    async def _append_partial(self, session_id: str, delta: str) -> None:
        async with self._lock:
            runtime = self._sessions.setdefault(session_id, _SessionRuntime())
            runtime.active_partial_text += delta

    async def _get_partial(self, session_id: str) -> str:
        async with self._lock:
            runtime = self._sessions.get(session_id)
            return runtime.active_partial_text if runtime else ""

    async def _broadcast(self, session_id: str, payload: Dict[str, Any]) -> None:
        async with self._lock:
            runtime = self._sessions.get(session_id)
            if not runtime:
                return
            connections = list(runtime.connections.items())

        for connection_id, conn_state in connections:
            try:
                async with conn_state.send_lock:
                    await conn_state.websocket.send_json(payload)
            except Exception:
                # 发送失败就移除连接，避免拖慢广播
                await self.disconnect(session_id, connection_id)


realtime_chat_service = RealtimeChatService()

