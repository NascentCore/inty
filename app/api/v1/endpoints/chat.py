import time
import uuid
from typing import Optional, TypeAlias, Union

from fastapi import APIRouter, Depends, Header, HTTPException
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
from app.services.memory_service import deliver_festival_memories_for_user_agent
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


def _build_festival_prompt_choice_message(item: dict, info: Optional[dict]) -> dict:
    """构建单条节日提醒 choice 的 message 字典，与普通 AI 消息结构一致（含 id、meta_data、timestamp、audio_url）。

    同一条 message 中可能同时出现顶层的 festival_memory_id（snake_case）与 meta_data 内的
    festivalMemoryId（camelCase）：前者为本接口显式提供、供客户端优先使用；后者来自写入
    chat_history 时存储的 meta_data，透传未改。客户端应以顶层 festival_memory_id 为准。
    """
    if info:
        return {
            "role": None,
            "content": item["content"],
            "type": "festival_memory_prompt",
            "festival_memory_id": item["memory_id"],
            "id": info["id"],
            "meta_data": info["meta_data"],
            "timestamp": info["timestamp"],
            "audio_url": info["audio_url"],
        }
    msg_id = item.get("message_id")
    return {
        "role": None,
        "content": item["content"],
        "type": "festival_memory_prompt",
        "festival_memory_id": item["memory_id"],
        "id": msg_id,
        "meta_data": None,
        "timestamp": None,
        "audio_url": None,
    }


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
    app_version_code: Optional[int] = Header(None, alias="appVersionCode"),
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
    if request.stream:
        raise HTTPException(status_code=400, detail="Stream is not supported")

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

            with log_time(f"AI聊天处理: session_id={session_id}"):
                subscription = await subscription_service.get_user_current_subscription(
                    db, current_user.id
                )
                model_override = select_chat_model(
                    user=current_user, is_subscribed=bool(subscription)
                )
                logger.debug(
                    f"chat completions model_override: agent_id={agent_id}, model_override={model_override}, is_subscribed={bool(subscription)}"
                )
                chat_result = await agent.chat(
                    user_id=current_user.id,
                    session_id=session_id,
                    messages=messages,
                    chat_settings=chat_settings,
                    user_time_context=user_time_context,
                    model_override=model_override,
                )
                response_content, ai_message_id = (
                    (chat_result[0], chat_result[1])
                    if isinstance(chat_result, tuple)
                    else (chat_result, None)
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

        # 获取 AI 消息完整信息：插入时已拿到 message id 则按 id 查，否则查最新一条
        latest_message_info = None
        try:
            if ai_message_id is not None:
                with log_time(f"获取AI消息信息: message_id={ai_message_id}"):
                    latest_message_info = (
                        await chat_history_service.get_ai_message_info_by_id(
                            db, ai_message_id
                        )
                    )
            if latest_message_info is None:
                with log_time(f"获取最新消息: session_id={session_id}"):
                    latest_message_info = (
                        await chat_history_service.get_latest_ai_message_info(
                            db, session_id
                        )
                    )
        except Exception as e:
            logger.warning(f"获取最新消息信息失败: {str(e)}")

        user_message_id = None
        try:
            with log_time(f"获取最新用户消息ID: session_id={session_id}"):
                user_message_id = await chat_history_service.get_latest_user_message_id(
                    db, session_id
                )
        except Exception as e:
            logger.warning(f"获取最新用户消息ID失败: {str(e)}")

        # 按需投递节日记忆提示：写入 chat_history、更新 delivery_at，并收集本次投递项用于 choices
        try:
            with log_time(
                f"投递节日记忆提示: user_id={current_user.id}, agent_id={agent_id}"
            ):
                delivered_prompts = await deliver_festival_memories_for_user_agent(
                    db, current_user.id, agent_id
                )
        except Exception as e:
            logger.warning(f"投递节日记忆提示失败: {e}")
            delivered_prompts = []

        # 构建响应
        data = _build_chat_response(
            response_content,
            last_user_message,
            latest_message_info,
            audio_url,
            request,
            user_message_id=user_message_id,
        )

        # 若有本次投递的节日提醒且客户端版本满足要求，追加到 choices（与 GET messages / GET agent 一致的版本门控）
        min_ver = (
            global_config_loaded_from_config_yaml.app.min_app_version_code_for_festival_memory
        )
        if delivered_prompts and (
            app_version_code is None or app_version_code >= min_ver
        ):
            msg_ids = [
                item["message_id"]
                for item in delivered_prompts
                if item.get("message_id") is not None
            ]
            infos_map = await chat_history_service.get_ai_message_infos_by_ids(
                db, msg_ids
            )
            for idx, item in enumerate(delivered_prompts, start=1):
                msg_id = item.get("message_id")
                info = infos_map.get(msg_id) if msg_id is not None else None
                message = _build_festival_prompt_choice_message(item, info)
                data["choices"].append(
                    {"index": idx, "message": message, "finish_reason": "stop"}
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
            subscription_service=subscription_service,
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
