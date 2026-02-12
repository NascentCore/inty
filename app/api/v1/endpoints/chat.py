import asyncio
import json
import queue
import threading
import time
import uuid
from typing import Optional, TypeAlias, Union

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.api import deps
from app.api.tags import ANDROID_APP_TAG, INTY_EVAL_TAG, WEB_APP_TAG
from app.api.utils.logger_route import LoggerRoute
from app.core.agent.agent import agent_manager
from app.core.config import global_config_loaded_from_config_yaml
from app.core.model_selection import select_chat_model
from app.models.user import AuthType
from app.schemas.chat import ChatCompletionRequest
from app.schemas.response import (
    BizError,
    BusinessErrorCode,
    UsageLimitExceeded,
    create_business_error_response,
)
from app.services import agent_service, chat_history_service, chat_service
from app.services.chat_service import generate_session_id
from app.services.global_services import subscription_service
from app.services.push_notification_service import mark_user_push_notifications_as_read
from app.services.voice_service import voice_service
from app.utils.timing import Timer, log_time

router = APIRouter(prefix="/chat", route_class=LoggerRoute)


def _handle_subscription_limit_error(
    session_id: str,
    last_user_message: str,
    current_user: schemas.User,
    used_count: int,
    daily_limit: int,
) -> schemas.APIResponse:
    """处理订阅限制错误"""
    try:
        chat_history_service.add_user_message(session_id, last_user_message)
        logger.debug(f"用户消息已保存到历史记录: {session_id}")
    except Exception as e:
        logger.warning(f"保存用户消息失败: {str(e)}")

    if current_user.auth_type == AuthType.GUEST:
        return create_business_error_response(
            error_info=BusinessErrorCode.GUEST_LOGIN_REQUIRED,
            extra_data={"used_count": used_count, "daily_limit": daily_limit},
        )
    else:
        return create_business_error_response(
            error_info=BusinessErrorCode.SUBSCRIPTION_REQUIRED,
            extra_data={"used_count": used_count, "daily_limit": daily_limit},
        )


def _build_chat_response(
    response_content: str,
    last_user_message: str,
    latest_message_info: Optional[dict],
    audio_url: Optional[str],
    request: ChatCompletionRequest,
    user_message_id: Optional[int] = None,
) -> dict:
    """构建聊天响应数据"""
    message = {"role": "assistant", "content": response_content}

    if latest_message_info:
        message["id"] = latest_message_info["id"]
        message["meta_data"] = latest_message_info["meta_data"]
        message["timestamp"] = latest_message_info["timestamp"]
        message["audio_url"] = latest_message_info["audio_url"] or audio_url
    elif audio_url:
        message["audio_url"] = audio_url

    if message.get("audio_url"):
        logger.debug(f"响应包含语音URL: {message['audio_url']}")

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "user_message_id": user_message_id,
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": len(last_user_message.split()),
            "completion_tokens": len(response_content.split()),
            "total_tokens": len(last_user_message.split())
            + len(response_content.split()),
        },
    }


def _run_sync_stream_worker(
    stream_iterator,
    output_queue: queue.Queue[tuple[str, object]],
) -> None:
    """在独立线程中拉取同步流式输出并写入线程安全队列。"""
    try:
        for chunk in stream_iterator:
            output_queue.put(("chunk", chunk))
    except Exception as exc:
        output_queue.put(("error", exc))
    finally:
        output_queue.put(("done", None))


@router.post(
    "/completions/{agent_id}",
    response_model=schemas.APIResponse[dict],
    summary="返回与指定 Agent 聊天的下一条消息",
    description="可以处理包括图片在内的各种消息类型，媒体类型应该先上传，然后将 URL 作为索引发送到此 API",
    tags=[ANDROID_APP_TAG, WEB_APP_TAG, INTY_EVAL_TAG],
)
async def agent_chat_completions(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: ChatCompletionRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    基于Agent ID的OpenAI风格聊天接口
    如果用户还没有和该Agent创建会话，则自动创建
    """
    if (
        global_config_loaded_from_config_yaml.app.api_endpoints.disable_api_v1_chat_completions
    ):
        raise HTTPException(
            status_code=404, detail="API v1 chat completions is disabled"
        )
    try:
        request_handling_timer = Timer("请求处理")
        logger.debug(
            f"聊天请求 - agent_id={agent_id}, user_id={current_user.id}, messages={len(request.messages)}"
        )

        # 获取或创建与该Agent的唯一会话
        with log_time(
            f"获取或创建聊天会话: user_id={current_user.id}, agent_id={agent_id}"
        ):
            chat = await chat_service.get_or_create_chat_by_agent(
                db=db, user_id=current_user.id, agent_id=agent_id
            )

        # 验证返回的chat中的agent_id是否与传入的一致
        if chat.agent_id != agent_id:
            logger.error(f"Agent ID不匹配: 传入={agent_id}, 实际={chat.agent_id}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent ID mismatch: expected={agent_id}, actual={chat.agent_id}",
            )

        # 获取最后一条用户消息
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")

        last_user_message = user_messages[-1].content
        messages = [HumanMessage(content=last_user_message)]
        user_time_context = (
            request.user_time_context.model_dump(exclude_none=True)
            if request.user_time_context
            else None
        )
        if user_time_context == {}:
            user_time_context = None

        # 使用高性能的聊天专用Agent获取方法
        with log_time(f"查询 Agent 数据: {chat.agent_id}"):
            agent_data = await agent_service.get_agent_for_chat(
                db, agent_id=chat.agent_id
            )

        if not agent_data:
            logger.error(f"Agent数据未找到: {chat.agent_id}")
            raise HTTPException(status_code=404, detail="Agent not found")

        with log_time(f"获取 Agent 实例: {chat.agent_id}"):
            agent = await agent_manager.get_agent(agent_data)

        session_id = generate_session_id(chat.id)

        with log_time(f"订阅检查: user_id={current_user.id}"):
            is_allowed, used_count, daily_limit = (
                await subscription_service.check_chat_limit(db, current_user)
            )

        if not is_allowed:
            return _handle_subscription_limit_error(
                session_id, last_user_message, current_user, used_count, daily_limit
            )

        # 获取聊天设置和AI回复
        try:
            with log_time(f"获取聊天设置: chat_id={chat.id}"):
                chat_settings = await chat_service.get_or_create_chat_settings(
                    db, chat.id, current_user.id, agent_id
                )

            subscription = await subscription_service.get_user_current_subscription(
                db, current_user.id
            )
            model_override = select_chat_model(
                user=current_user, is_subscribed=bool(subscription)
            )

            if request.stream:
                completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
                created_ts = int(time.time())
                stream_queue: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=128)

                stream_iterator = agent.chat_stream(
                    user_id=current_user.id,
                    session_id=session_id,
                    messages=messages,
                    chat_settings=chat_settings,
                    user_time_context=user_time_context,
                    model_override=model_override,
                )
                stream_worker = threading.Thread(
                    target=_run_sync_stream_worker,
                    args=(stream_iterator, stream_queue),
                    daemon=True,
                    name=f"chat-stream-{session_id}",
                )
                stream_worker.start()

                async def stream_events():
                    sent_role = False
                    try:
                        while True:
                            event_type, event_payload = await asyncio.to_thread(
                                stream_queue.get
                            )

                            if event_type == "chunk":
                                chunk_text = str(event_payload)
                                delta: dict[str, str] = {"content": chunk_text}
                                if not sent_role:
                                    delta["role"] = "assistant"
                                    sent_role = True

                                chunk_data = {
                                    "id": completion_id,
                                    "object": "chat.completion.chunk",
                                    "created": created_ts,
                                    "model": request.model,
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": delta,
                                            "finish_reason": None,
                                        }
                                    ],
                                }
                                yield (
                                    f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                                ).encode("utf-8")
                                continue

                            if event_type == "error":
                                if isinstance(event_payload, BaseException):
                                    raise event_payload
                                raise RuntimeError(
                                    f"Unexpected streaming error payload: {event_payload}"
                                )

                            if event_type == "done":
                                break

                        # 流式消息结束后，执行与非流式一致的后处理（不影响 SSE 协议输出）
                        try:
                            read_count = await mark_user_push_notifications_as_read(
                                db, current_user.id
                            )
                            if read_count > 0:
                                logger.debug(
                                    f"标记用户推送为已读: user_id={current_user.id}, count={read_count}"
                                )
                        except Exception as push_read_error:
                            logger.warning(
                                f"标记用户推送为已读失败: user_id={current_user.id}, error={str(push_read_error)}"
                            )

                        try:
                            await subscription_service.record_usage(
                                db,
                                current_user.id,
                                "chat",
                                1,
                                extra_data={
                                    "agent_id": agent_id,
                                    "message_length": len(last_user_message),
                                },
                            )
                            logger.debug("聊天使用情况记录成功")
                        except Exception as usage_error:
                            logger.warning(f"记录聊天使用情况失败: {str(usage_error)}")

                        end_chunk = {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "created": created_ts,
                            "model": request.model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {},
                                    "finish_reason": "stop",
                                }
                            ],
                        }
                        yield (
                            f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n"
                        ).encode("utf-8")
                        yield b"data: [DONE]\n\n"

                    except asyncio.CancelledError:
                        logger.info(
                            f"流式连接被客户端取消: user_id={current_user.id}, session_id={session_id}"
                        )
                        raise
                    except Exception as stream_error:
                        logger.error(f"流式聊天处理失败: {str(stream_error)}")
                        error_chunk = {
                            "error": {
                                "message": f"Chat failed: {str(stream_error)}",
                                "type": "server_error",
                            }
                        }
                        yield (
                            f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                        ).encode("utf-8")
                    finally:
                        await asyncio.to_thread(stream_worker.join, 1.0)
                        timing_message = request_handling_timer.stop()
                        logger.debug(f"流式聊天请求完成: agent_id={agent_id}, {timing_message}")

                return StreamingResponse(
                    stream_events(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    },
                )

            with log_time(f"AI聊天处理: session_id={session_id}"):
                response_content = await agent.chat(
                    user_id=current_user.id,
                    session_id=session_id,
                    messages=messages,
                    chat_settings=chat_settings,
                    user_time_context=user_time_context,
                    model_override=model_override,
                )

            logger.debug(f"Agent聊天响应成功: {response_content[:100]}...")

            # 用户发送消息后，标记该用户的所有未读推送为已读
            try:
                read_count = await mark_user_push_notifications_as_read(
                    db, current_user.id
                )
                if read_count > 0:
                    logger.debug(
                        f"标记用户推送为已读: user_id={current_user.id}, count={read_count}"
                    )
            except Exception as e:
                # 标记已读失败不应该影响聊天流程，只记录日志
                logger.warning(
                    f"标记用户推送为已读失败: user_id={current_user.id}, error={str(e)}"
                )

        except Exception as e:
            logger.error(f"Agent聊天处理失败: {str(e)}")
            raise

        # 语音生成逻辑 - 根据chat_settings.voice_enabled决定是否自动播放
        audio_url = None
        audio_duration = None
        try:
            # 语音自动播放逻辑：chat_settings.voice_enabled = true 时自动生成语音
            if chat_settings.voice_enabled:
                # TODO: 添加一个默认语音 ID
                agent_voice_id = agent_data.get("voice_id")

                with log_time(
                    f"语音生成: voice_id={agent_voice_id}, text_length={len(response_content)}, language={request.language}"
                ):
                    voice_result = await voice_service.generate_voice(
                        text=response_content,
                        voice_id=agent_voice_id,
                        language=request.language,
                        db=db,
                        agent_gender=agent_data.get("gender"),
                        user=current_user,
                    )
                if voice_result:
                    audio_url, audio_duration = voice_result
                else:
                    logger.warning(
                        f"用户 {current_user.id} 语音生成失败或达到限制，聊天文本正常返回"
                    )
            else:
                logger.debug("语音未启用，跳过语音生成")

        except Exception as e:
            logger.error(f"语音生成失败: {str(e)}")
            logger.exception("语音生成异常详细信息:")
            # 语音生成失败不影响聊天功能

        # 记录聊天使用情况
        try:
            with log_time(f"记录使用情况: user_id={current_user.id}"):
                await subscription_service.record_usage(
                    db,
                    current_user.id,
                    "chat",
                    1,
                    extra_data={
                        "agent_id": agent_id,
                        "message_length": len(last_user_message),
                    },
                )
            logger.debug("聊天使用情况记录成功")
        except Exception as e:
            logger.warning(f"记录聊天使用情况失败: {str(e)}")

        # 获取最新AI消息的完整信息
        try:
            with log_time(f"获取最新消息: session_id={session_id}"):
                latest_message_info = (
                    await chat_history_service.get_latest_ai_message_info(
                        db, session_id
                    )
                )
        except Exception as e:
            logger.warning(f"获取最新消息信息失败: {str(e)}")
            latest_message_info = None

        user_message_id = None
        try:
            with log_time(f"获取最新用户消息ID: session_id={session_id}"):
                user_message_id = await chat_history_service.get_latest_user_message_id(
                    db, session_id
                )
        except Exception as e:
            logger.warning(f"获取最新用户消息ID失败: {str(e)}")

        # 构建响应
        data = _build_chat_response(
            response_content,
            last_user_message,
            latest_message_info,
            audio_url,
            request,
            user_message_id=user_message_id,
        )

        timing_message = request_handling_timer.stop()
        logger.debug(f"聊天请求完成: agent_id={agent_id}, {timing_message}")

        return schemas.APIResponse.success(data=data)

    except Exception as e:
        logger.error(f"聊天请求处理失败: {str(e)}")
        logger.exception("聊天请求异常详细信息:")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


ChatImageGenerationAPIResponse: TypeAlias = schemas.APIResponse[
    Union[schemas.ChatImageGenerationResponse, UsageLimitExceeded, BizError]
]


@router.post(
    "/images/{agent_id}",
    response_model=ChatImageGenerationAPIResponse,
    summary="基于聊天消息及历史消息和其他相关信息（角色背景、用户 profile 等）生成图片",
    description=(
        "根据Agent角色、聊天历史和用户消息生成图片，并保存到聊天历史中。"
        "注意：路径参数 `agent_id` 仅作为目前的名称，实际应为 `chat_id`。未来如需扩展可直接重命名。"
        "agent id 则代表与该 agent 的*当前*会话的 id"
    ),
    tags=[INTY_EVAL_TAG],
)
async def generate_chat_image(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: schemas.ChatImageGenerationRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> ChatImageGenerationAPIResponse:
    """
    基于聊天上下文生成图片

    流程：
    1. 验证用户和Agent
    2. 获取或创建聊天会话
    3. 检查图片生成限额
    4. 调用图片生成服务
    5. 记录用量
    6. 返回图片信息

    注意：
    - 路径参数 `agent_id` 仅作为目前的名称，实际应为 `chat_id`
    - 本 API 拷贝自 `app/api/v1/endpoints/chats.py::generate_chat_image`（第1170-1325行）
    - 核心逻辑已提取到 `chat_service.generate_chat_image`
    """
    try:
        # 返回值：
        # 1. 成功时返回 ChatImageGenerationResponse
        # 2. 业务限制错误时返回 UsageLimitExceeded 或 BizError
        # 3. 其他错误时返回 HTTPException
        # 1，2 均显示为应用正常返回值、3 为 fastapi 返回值
        result = await chat_service.generate_chat_image(
            db=db,
            agent_id=agent_id,
            user_id=current_user.id,
            message_id=request.message_id,
            history_count=request.history_count,
            model=request.model,
        )

        if isinstance(result, UsageLimitExceeded):
            return schemas.APIResponse.error(
                message=result.message, code=result.code, data=result
            )

        if isinstance(result, BizError):
            # 返回业务错误响应，包含额外的错误信息
            return create_business_error_response(
                error_info={
                    "code": result.code,
                    "error_code": result.error_code,
                    "message": result.message,
                },
                extra_data={
                    "suggestion": "Please modify your prompt and try again.",
                },
            )

        return schemas.APIResponse.success(data=result)

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"生成聊天图片失败 - Agent ID: {agent_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate image: {str(e)}"
        )
