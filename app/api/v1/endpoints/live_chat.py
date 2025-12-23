"""
实时语音通话 WebSocket 端点

CREATED_BY_AGENT
"""

import asyncio
import base64
import json
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.api.tags import INTY_EVAL_TAG
from app.schemas.live_chat import (
    LiveChatAudioResponseMessage,
    LiveChatConfig,
    LiveChatErrorMessage,
    LiveChatMessageType,
    LiveChatStatus,
    LiveChatStatusMessage,
    LiveChatTranscriptMessage,
)
from app.services.live_chat_service import live_chat_service

router = APIRouter(prefix="/live-chat")


async def get_current_user_ws(
    websocket: WebSocket,
    db: AsyncSession,
) -> Optional[schemas.User]:
    """
    从 WebSocket 连接中获取当前用户

    支持两种认证方式：
    1. URL 查询参数: ?token=xxx
    2. 子协议: Sec-WebSocket-Protocol: Bearer, <token>
    """
    token = websocket.query_params.get("token")

    if not token:
        protocols = websocket.headers.get("sec-websocket-protocol", "")
        if "Bearer" in protocols:
            parts = protocols.split(",")
            for i, part in enumerate(parts):
                if part.strip() == "Bearer" and i + 1 < len(parts):
                    token = parts[i + 1].strip()
                    break

    if not token:
        logger.warning("WebSocket 连接缺少 token")
        return None

    try:
        user = await deps.get_user_from_token(token, db)
        logger.info(f"WebSocket 用户认证成功: {user.id}")
        return user
    except Exception as e:
        logger.warning(f"WebSocket 认证失败: {str(e)}")
        return None


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
    2. 获取 Agent 配置 + 对话历史
    3. 创建 Gemini Live 会话
    4. 双向音频流桥接
    5. 可选：保存语音对话到聊天历史

    消息协议：
    - 上行 audio: {"type": "audio", "data": "<base64_pcm>"}
    - 上行 text: {"type": "text", "data": "<text>"}
    - 上行 config: {"type": "config", "config": {...}}
    - 上行 activity_start: {"type": "activity_start"}
    - 上行 activity_end: {"type": "activity_end"}
    - 上行 end: {"type": "end"}
    - 下行 audio_response: {"type": "audio_response", "data": "<base64_pcm>", "sample_rate": 24000}
    - 下行 transcript: {"type": "transcript", "text": "...", "is_final": true}
    - 下行 user_transcript: {"type": "user_transcript", "text": "...", "is_final": true}
    - 下行 status: {"type": "status", "status": "...", "message": "..."}
    - 下行 error: {"type": "error", "code": "...", "message": "..."}
    """
    logger.info(f"收到 WebSocket 连接请求 - agent_id: {agent_id}")

    current_user = await get_current_user_ws(websocket, db)
    if not current_user:
        logger.warning(f"WebSocket 认证失败，拒绝连接 - agent_id: {agent_id}")
        await websocket.close(code=4001, reason="Unauthorized")
        return

    if not live_chat_service.is_enabled():
        logger.warning("Live chat 功能未启用，拒绝连接")
        await websocket.close(code=4003, reason="Live chat is disabled")
        return

    await websocket.accept()
    logger.info(
        f"WebSocket 连接已建立 - user_id: {current_user.id}, agent_id: {agent_id}"
    )

    session = None
    config = LiveChatConfig()

    try:
        session = await live_chat_service.create_session(
            db=db,
            agent_id=agent_id,
            user_id=current_user.id,
            config=config,
        )

        input_queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()

        async def on_audio(data: bytes):
            """处理下行音频"""
            try:
                msg = LiveChatAudioResponseMessage(
                    data=base64.b64encode(data).decode("utf-8"),
                    sample_rate=live_chat_service._config.receive_sample_rate,
                )
                await websocket.send_json(msg.model_dump())
            except Exception as e:
                logger.error(f"发送音频失败: {str(e)}")

        async def on_transcript(text: str, role: str):
            """处理转录文本"""
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
                )
                await websocket.send_json(msg.model_dump())
            except Exception as e:
                logger.error(f"发送转录失败: {str(e)}")

        async def on_status(status: LiveChatStatus, message: Optional[str]):
            """处理状态更新"""
            try:
                msg = LiveChatStatusMessage(
                    status=status,
                    message=message,
                )
                await websocket.send_json(msg.model_dump())
            except Exception as e:
                logger.error(f"发送状态失败: {str(e)}")

        async def on_error(code: str, message: str):
            """处理错误"""
            try:
                msg = LiveChatErrorMessage(
                    code=code,
                    message=message,
                )
                await websocket.send_json(msg.model_dump())
            except Exception as e:
                logger.error(f"发送错误失败: {str(e)}")

        live_gen = live_chat_service.start_live_session(
            session=session,
            db=db,
            on_audio=on_audio,
            on_transcript=on_transcript,
            on_status=on_status,
            on_error=on_error,
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

                    elif msg_type == "config":
                        new_config = data.get("config", {})
                        if session:
                            session.config = LiveChatConfig(**new_config)

                    elif msg_type == "activity_start":
                        await input_queue.put({"type": "activity_start"})

                    elif msg_type == "activity_end":
                        await input_queue.put({"type": "activity_end"})

                    elif msg_type == "end":
                        await input_queue.put(None)
                        break

                except json.JSONDecodeError as e:
                    logger.warning(f"无效的 JSON 消息: {str(e)}")
                    await on_error("INVALID_JSON", "无效的消息格式")

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
        if session:
            await live_chat_service.end_session(session.session_id)

        try:
            await websocket.close()
        except Exception:
            pass

        logger.info(
            f"Live chat 会话结束 - user_id: {current_user.id}, agent_id: {agent_id}"
        )


@router.get(
    "/status",
    response_model=schemas.APIResponse[dict],
    summary="获取实时语音通话服务状态",
    tags=[INTY_EVAL_TAG],
)
async def get_live_chat_status():
    """获取实时语音通话服务的启用状态和配置信息"""
    from app.core.config import global_config_loaded_from_config_yaml

    config = global_config_loaded_from_config_yaml.gemini_live

    return schemas.APIResponse.success(
        data={
            "enabled": config.enabled,
            "model": config.model,
            "default_voice": config.default_voice,
            "send_sample_rate": config.send_sample_rate,
            "receive_sample_rate": config.receive_sample_rate,
            "session_resumption": config.session_resumption,
            "input_transcription": config.input_transcription,
            "output_transcription": config.output_transcription,
        }
    )
