"""
实时语音通话 WebSocket 端点

CREATED_BY_AGENT
"""

import asyncio
import base64
import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.api.tags import INTY_EVAL_TAG
from app.schemas.live_chat import (
    LiveChatAudioResponseMessage,
    LiveChatConfig,
    LiveChatErrorMessage,
    LiveChatLatencyMessage,
    LiveChatMessageType,
    LiveChatSessionInfoMessage,
    LiveChatStatus,
    LiveChatStatusMessage,
    LiveChatTranscriptMessage,
)
from app.schemas.response import BusinessErrorCode
from app.services.global_services import subscription_service
from app.services.live_chat_service import live_chat_service

router = APIRouter(prefix="/live-chat")


@router.get("/status", tags=[INTY_EVAL_TAG])
async def get_live_chat_status(
    current_user: schemas.User = Depends(deps.get_current_user),
):
    """
    获取实时语音通话服务状态

    返回 Live Chat 服务的启用状态和配置信息。
    """
    config = live_chat_service._config
    return schemas.APIResponse.success(
        data={
            "enabled": config.enabled,
            "model": config.model,
            "default_voice": config.default_voice,
            "send_sample_rate": config.send_sample_rate,
            "receive_sample_rate": config.receive_sample_rate,
            "default_speech_language_code": config.speech_language_code,
            "default_response_language_name": config.response_language_name,
        }
    )


async def get_current_user_ws(
    websocket: WebSocket,
    db: AsyncSession,
) -> Optional[schemas.User]:
    """
    从 WebSocket 连接中获取当前用户

    支持三种认证方式（按优先级）：
    1. Header: Authorization: Bearer <token>（与其他 HTTP 接口一致，推荐）
    2. 子协议: Sec-WebSocket-Protocol: Bearer, <token>
    3. URL 查询参数: ?token=xxx（兼容旧用法）
    """
    token = None

    auth = websocket.headers.get("authorization")
    if auth:
        parts = auth.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()

    if not token:
        protocols = websocket.headers.get("sec-websocket-protocol", "")
        if "Bearer" in protocols:
            parts = protocols.split(",")
            for i, part in enumerate(parts):
                if part.strip() == "Bearer" and i + 1 < len(parts):
                    token = parts[i + 1].strip()
                    break

    if not token:
        token = websocket.query_params.get("token")

    if not token:
        logger.warning("WebSocket 连接缺少 token")
        return None

    user = await deps.get_user_from_token(token, db)
    if user is None:
        logger.warning("WebSocket 认证失败: invalid or expired token")
        return None
    logger.info(f"WebSocket 用户认证成功: {user.id}")
    return user


@router.websocket("/{agent_id}")
async def live_chat_session(
    websocket: WebSocket,
    agent_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
):
    """
    实时语音通话 WebSocket 端点

    流程：
    1. 验证用户认证
    2. 检查用量限制（agent 数量 + 时长）
    3. 获取 Agent 配置 + 对话历史
    4. 创建 Gemini Live 会话
    5. 双向音频流桥接
    6. 可选：保存语音对话到聊天历史
    7. 会话结束时记录用量

    消息协议：
    - 上行 audio: {"type": "audio", "data": "<base64_pcm>"}
    - 上行 text: {"type": "text", "data": "<text>"}
    - 上行 activity_start: {"type": "activity_start"}
    - 上行 activity_end: {"type": "activity_end"}
    - 上行 end: {"type": "end"}
    - 下行 audio_response: {"type": "audio_response", "data": "<base64_pcm>", "sample_rate": 24000}
    - 下行 transcript: {"type": "transcript", "text": "...", "is_final": true}
    - 下行 user_transcript: {"type": "user_transcript", "text": "...", "is_final": true}
    - 下行 status: {"type": "status", "status": "...", "message": "..."}
    - 下行 error: {"type": "error", "code": 10001008, "error_code": "...", "message": "..."}

    Optional query params (per-session language for SDK clients):
    - speech_language_code: BCP-47 tag for SpeechConfig.language_code (e.g. ar-SA, en-US)
    - response_language_name: human-readable reply language for system instruction (e.g. Arabic)

    WebSocket 关闭码与错误信息：
    - 4000: Invalid language query parameters
    - 4001: 认证失败
    - 4003: 功能未启用
    - 4010: Agent 数量限制（reason 为 JSON 格式的业务错误）
    - 4011: 时长限制（reason 为 JSON 格式的业务错误）

    用量超限时 reason 格式：{"type": "error", "code": 10001001, "error_code": "...", "message": "..."}
    - 未订阅用户: SUBSCRIPTION_REQUIRED (10001001)
    - 订阅用户 Agent 限制: LIVE_CHAT_AGENT_LIMIT_REACHED (10001007)
    - 订阅用户时长限制: LIVE_CHAT_DURATION_LIMIT_REACHED (10001008)
    """
    logger.info(f"收到 WebSocket 连接请求 - agent_id: {agent_id}")

    current_user = await get_current_user_ws(websocket, db)
    if not current_user:
        logger.warning(f"WebSocket 认证失败，拒绝连接 - agent_id: {agent_id}")
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Evaluation: superuser can pass assume_user_id query param to act as another user (load their history)
    assume_user_id = websocket.query_params.get("assume_user_id")
    if assume_user_id and assume_user_id.strip() and current_user.is_superuser:
        from sqlalchemy import select
        from app.models.user import User

        row = await db.execute(select(User).where(User.id == assume_user_id.strip()))
        assumed_user = row.scalar_one_or_none()
        if assumed_user and not assumed_user.deleted_at:
            logger.info(
                f"Live chat assuming user: operator={current_user.id}, assumed={assumed_user.id}, agent_id={agent_id}"
            )
            current_user = assumed_user
        else:
            logger.warning(f"assume_user_id not found or deleted: {assume_user_id}")

    if not live_chat_service.is_enabled():
        logger.warning("Live chat 功能未启用，拒绝连接")
        await websocket.close(code=4003, reason="Live chat is disabled")
        return

    is_allowed, reject_reason, limit_info = (
        await subscription_service.check_live_chat_limit(db, current_user, agent_id)
    )

    if not is_allowed:
        error_info = limit_info.get("error_info", {})
        error_code = error_info.get("error_code", reject_reason)
        error_message = error_info.get("message", reject_reason)
        logger.warning(
            f"Live chat 限制检查未通过 - user_id: {current_user.id}, "
            f"agent_id: {agent_id}, error_code: {error_code}, "
            f"error_message: {error_message}, info: {limit_info}"
        )

        # 先建立连接，再发送错误消息，最后关闭
        # 这样 Android 端才能正确接收到 error_code
        await websocket.accept()

        error_msg = LiveChatErrorMessage(
            code=error_info.get("code"),
            error_code=error_code,
            message=error_message,
        )
        await websocket.send_json(error_msg.model_dump())
        await websocket.close()
        return

    speech_q = websocket.query_params.get("speech_language_code")
    response_q = websocket.query_params.get("response_language_name")
    live_cfg_kwargs = {}
    if speech_q is not None and speech_q.strip():
        live_cfg_kwargs["speech_language_code"] = speech_q.strip()
    if response_q is not None and response_q.strip():
        live_cfg_kwargs["response_language_name"] = response_q.strip()
    try:
        live_overrides = LiveChatConfig(**live_cfg_kwargs) if live_cfg_kwargs else None
    except ValidationError as e:
        logger.warning(f"Live chat invalid language query: {e}")
        await websocket.close(code=4000, reason="Invalid language parameters")
        return

    remaining_duration = limit_info.get("remaining_duration", 300)
    agent_limit = limit_info.get("agent_limit", 0)
    agent_count = limit_info.get("agent_count", 0)

    await websocket.accept()
    logger.info(
        f"WebSocket 连接已建立 - user_id: {current_user.id}, agent_id: {agent_id}, "
        f"remaining_duration: {remaining_duration}s"
    )

    session_info_msg = LiveChatSessionInfoMessage(
        remaining_duration=remaining_duration,
        agent_limit=agent_limit,
        agent_count=agent_count,
    )
    await websocket.send_json(session_info_msg.model_dump())

    session = None
    session_start_time = time.time()
    timeout_task: Optional[asyncio.Task] = None
    session_ended_by_timeout = False

    try:
        session = await live_chat_service.create_session(
            db=db,
            agent_id=agent_id,
            user_id=current_user.id,
            config=live_overrides,
        )

        input_queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()

        async def on_audio(data: bytes):
            """处理下行音频"""
            if session_ended_by_timeout:
                return
            try:
                msg = LiveChatAudioResponseMessage(
                    data=base64.b64encode(data).decode("utf-8"),
                    sample_rate=live_chat_service._config.receive_sample_rate,
                )
                await websocket.send_json(msg.model_dump())
            except Exception as e:
                logger.debug(f"发送音频失败（连接可能已关闭）: {str(e)}")

        async def on_transcript(
            text: str,
            role: str,
            message_id: Optional[int] = None,
            timestamp: Optional[float] = None,
        ):
            """处理转录文本；落库后的最终转录会带 message_id 与 timestamp（毫秒）。"""
            if session_ended_by_timeout:
                return
            try:
                msg_type = (
                    LiveChatMessageType.TRANSCRIPT
                    if role == "assistant"
                    else LiveChatMessageType.USER_TRANSCRIPT
                )
                msg = LiveChatTranscriptMessage(
                    type=msg_type,
                    text=text,
                    is_final=True,
                    message_id=message_id,
                    timestamp=timestamp,
                )
                await websocket.send_json(msg.model_dump())
            except Exception as e:
                logger.debug(f"发送转录失败（连接可能已关闭）: {str(e)}")

        async def on_status(status: LiveChatStatus, message: Optional[str]):
            """处理状态更新"""
            if session_ended_by_timeout:
                return
            try:
                msg = LiveChatStatusMessage(
                    status=status,
                    message=message,
                )
                await websocket.send_json(msg.model_dump())
            except Exception as e:
                logger.debug(f"发送状态失败（连接可能已关闭）: {str(e)}")

        async def on_error(error_code: str, message: str, code: Optional[int] = None):
            """处理错误"""
            try:
                msg = LiveChatErrorMessage(
                    code=code,
                    error_code=error_code,
                    message=message,
                )
                await websocket.send_json(msg.model_dump())
            except Exception as e:
                logger.debug(f"发送错误失败（连接可能已关闭）: {str(e)}")

        async def on_latency(latency_data: dict):
            """处理延迟指标更新"""
            if session_ended_by_timeout:
                return
            try:
                msg = LiveChatLatencyMessage(**latency_data)
                await websocket.send_json(msg.model_dump(exclude_none=True))
            except Exception as e:
                logger.debug(f"发送延迟指标失败（连接可能已关闭）: {str(e)}")

        async def duration_timeout_handler():
            """时长到达限制时结束会话"""
            nonlocal session_ended_by_timeout
            await asyncio.sleep(remaining_duration)
            session_ended_by_timeout = True
            logger.info(
                f"Live chat 时长到达限制 - user_id: {current_user.id}, "
                f"agent_id: {agent_id}, duration: {remaining_duration}s"
            )
            try:
                # 根据用户订阅状态返回不同的错误码
                subscription_status = (
                    await subscription_service.get_user_subscription_status(
                        db, current_user.id
                    )
                )
                if subscription_status.is_subscribed:
                    error_info = BusinessErrorCode.LIVE_CHAT_DURATION_LIMIT_REACHED
                else:
                    error_info = BusinessErrorCode.SUBSCRIPTION_REQUIRED
                await on_error(
                    error_code=error_info["error_code"],
                    message=error_info["message"],
                    code=error_info["code"],
                )
                await input_queue.put(None)
            except Exception as e:
                logger.error(f"发送时长限制错误失败: {str(e)}")

        timeout_task = asyncio.create_task(duration_timeout_handler())

        live_gen = live_chat_service.start_live_session(
            session=session,
            db=db,
            on_audio=on_audio,
            on_transcript=on_transcript,
            on_status=on_status,
            on_error=on_error,
            on_latency=on_latency,
        )

        async def send_audio_loop():
            """发送音频到 Gemini Live 的循环（统一通过 async generator）"""
            try:
                await live_gen.asend(None)

                while True:
                    item = await input_queue.get()
                    if item is None:
                        break
                    try:
                        item_type = item.get("type")
                        if item_type == "audio":
                            await live_gen.asend(item)
                        elif item_type == "activity_start":
                            await live_gen.asend({"type": "activity_start"})
                        elif item_type == "activity_end":
                            await live_gen.asend({"type": "activity_end"})
                        else:
                            logger.warning(f"未知输入队列消息类型: {item_type}")
                    except StopAsyncIteration:
                        break
            except Exception as e:
                logger.error(f"发送音频循环错误: {str(e)}")
            finally:
                try:
                    await live_gen.aclose()
                except Exception:
                    pass

        send_task = asyncio.create_task(send_audio_loop())

        try:
            while True:
                try:
                    raw_data = await websocket.receive_text()
                    data = json.loads(raw_data)
                    msg_type = data.get("type")

                    if msg_type == "audio":
                        audio_bytes = base64.b64decode(data.get("data", ""))
                        await input_queue.put({"type": "audio", "data": audio_bytes})

                    elif msg_type == "text":
                        text = data.get("data", "")
                        if text and session:
                            await live_chat_service.send_text(session.session_id, text)

                    elif msg_type == "activity_start":
                        await input_queue.put({"type": "activity_start"})

                    elif msg_type == "activity_end":
                        await input_queue.put({"type": "activity_end"})

                    elif msg_type == "end":
                        await input_queue.put(None)
                        break

                except json.JSONDecodeError as e:
                    logger.warning(f"无效的 JSON 消息: {str(e)}")
                    await on_error("INVALID_JSON", "Invalid message format")

        except WebSocketDisconnect:
            logger.info(f"WebSocket 断开连接 - user_id: {current_user.id}")
        finally:
            await input_queue.put(None)
            send_task.cancel()
            try:
                await send_task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.error(f"Live chat 会话错误: {str(e)}")
        try:
            msg = LiveChatErrorMessage(
                code="SESSION_ERROR",
                message=str(e),
            )
            await websocket.send_json(msg.model_dump())
        except Exception:
            pass

    finally:
        if timeout_task and not timeout_task.done():
            timeout_task.cancel()
            try:
                await timeout_task
            except asyncio.CancelledError:
                pass

        session_duration = int(time.time() - session_start_time)

        if session and session_duration > 0:
            await live_chat_service.end_session(session.session_id)
            try:
                # 构建 extra_data，包含 Gemini Live API 返回的 token 用量统计
                extra_data = {
                    "agent_id": agent_id,
                    "duration_seconds": session_duration,
                    "ended_by_timeout": session_ended_by_timeout,
                }
                if session.total_token_count > 0:
                    extra_data["total_token_count"] = session.total_token_count
                if session.response_token_details:
                    extra_data["response_token_details"] = (
                        session.response_token_details
                    )
                latency_metrics = session.get_latency_metrics()
                if latency_metrics:
                    extra_data["latency_metrics"] = latency_metrics

                # 使用独立会话记录用量，避免复用当前 WS 链路中的事务状态导致 prepared/rollback 错误。
                usage_record = await subscription_service.record_usage(
                    db=None,
                    user_id=current_user.id,
                    usage_type="live_chat",
                    usage_count=1,
                    extra_data=extra_data,
                )
                if usage_record:
                    token_info = (
                        f", tokens: {session.total_token_count}"
                        if session.total_token_count > 0
                        else ""
                    )
                    logger.info(
                        f"Live chat 用量已记录 - user_id: {current_user.id}, "
                        f"agent_id: {agent_id}, duration: {session_duration}s{token_info}, "
                        f"record_id: {usage_record.id}"
                    )
                else:
                    logger.error(
                        f"Live chat 用量记录失败（返回 None）- user_id: {current_user.id}, "
                        f"agent_id: {agent_id}, duration: {session_duration}s"
                    )
            except Exception as e:
                logger.error(f"记录 Live chat 用量失败: {str(e)}")
        elif session:
            await live_chat_service.end_session(session.session_id)

        try:
            await websocket.close()
        except Exception:
            pass

        logger.info(
            f"Live chat 会话结束 - user_id: {current_user.id}, agent_id: {agent_id}, "
            f"duration: {session_duration}s"
        )
