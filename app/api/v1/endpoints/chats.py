import uuid
from typing import Any, List, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.core.agent.agent import agent_manager
from app.core.chat import generate_chat_stream
from app.core.config import global_config_loaded_from_config_yaml
from app.core.user_privilege.premium_check import is_eligible_for_premium
from app.schemas.chat import ChatCompletionRequest
from app.schemas.response import (
    APIResponse,
    BusinessErrorCode,
    UsageLimitExceeded,
    create_business_error_response,
)
from app.services import agent_service, chat_history_service, chat_service
from app.services.chat_service import generate_session_id
from app.services.global_services import subscription_service
from app.services.voice_service import voice_service

# TODO: Prefix should be /chat instead of /chats.
router = APIRouter(prefix="/chats", route_class=LoggerRoute)


@router.get(
    "/",
    response_model=List[schemas.Chat],
    summary="Get current user's chat list",
    description="Get current user's chat list",
    tags=["android-app"],
)
async def list_chats(
    db: AsyncSession = Depends(deps.get_async_db),
    # Start index of the query, 0-based
    skip: int = 0,
    # Upper limit of the number of chats to return
    limit: int = 100,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user's chat list
    """
    chats = await chat_service.get_chats(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return chats


@router.post(
    "/",
    response_model=schemas.Chat,
    summary="Create new chat",
    description="Create new chat",
    tags=["android-app"],
)
async def create_chat(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    chat_in: schemas.ChatCreate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new chat
    """
    chat = await chat_service.create_chat(db, chat_in=chat_in, user_id=current_user.id)
    return chat


@router.delete(
    "/{chat_id}",
    response_model=schemas.Chat,
    summary="Delete chat",
    description="Delete chat",
    tags=["android-app"],
)
async def delete_chat(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    chat_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete chat
    """
    chat = await chat_service.get_chat(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    chat = await chat_service.delete_chat(db, db_chat=chat)
    return chat


@router.get(
    "/agents/status",
    deprecated=True,
    include_in_schema=False,
    description="No record of who is using this",
)
async def get_agent_status(
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Get Agent manager status
    """
    return {
        "active_agents": agent_manager.get_agent_count(),
        "max_agents": agent_manager.max_agents,
        "cleanup_interval": agent_manager.cleanup_interval,
        "max_idle_time": agent_manager.max_idle_time,
    }


@router.post(
    "/agents/initialize",
    deprecated=True,
    include_in_schema=False,
    description="No record of who is using this",
)
async def initialize_agents(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Manually initialize commonly used Agents (admin function)
    """
    try:
        await agent_manager.initialize_popular_agents(db)
        return {
            "status": "success",
            "message": "Common Agents initialization completed",
            "active_agents": agent_manager.get_agent_count(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")


@router.delete(
    "/agents/cleanup",
    deprecated=True,
    include_in_schema=False,
    description="No record of who is using this",
)
async def cleanup_idle_agents(
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    Manually cleanup idle Agents (admin function)
    """
    try:
        old_count = agent_manager.get_agent_count()
        agent_manager._cleanup_idle_agents()
        new_count = agent_manager.get_agent_count()
        return {
            "status": "success",
            "message": "Idle Agents cleanup completed",
            "cleaned_count": old_count - new_count,
            "remaining_agents": new_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get(
    "/{chat_id}/detail",
    deprecated=True,
    include_in_schema=False,
    tags=["unknown"],
    summary="Get Chat Detail",
    description="Get chat details with paginated message records",
)
async def get_chat_detail(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    chat_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    limit: int = Query(20, ge=1, le=100, description="Number of messages per page"),
    offset: int = Query(0, ge=0, description="Offset (number of messages to skip)"),
) -> Any:
    """
    Get chat details with paginated message records
    Support scrolling to load earlier conversations
    """
    # Verify if chat exists
    chat = await chat_service.get_chat(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Verify if chat belongs to current user
    if chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        # Use unified session_id generation rule
        session_id = generate_session_id(chat_id)

        # Get paginated messages
        messages_data = chat_history_service.get_messages_paginated(
            session_id=session_id, limit=limit, offset=offset
        )

        # Assemble return data
        return {
            "chat_info": {
                "id": chat.id,
                "agent_id": chat.agent_id,
                "agent_name": chat.agent_name,
                "agent_avatar": chat.agent_avatar,
                "user_id": chat.user_id,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
            },
            "messages": messages_data["messages"],
            "pagination": {
                "total": messages_data["total"],
                "limit": messages_data["limit"],
                "offset": messages_data["offset"],
                "page": messages_data["page"],
                "has_more": messages_data["has_more"],
                "total_pages": (
                    (messages_data["total"] + limit - 1) // limit if limit > 0 else 1
                ),
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get chat details: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/detail",
    tags=["unknown", "inty-eval"],
    include_in_schema=False,
    deprecated=True,
    summary="Get Chat Detail for agent identified by agent_id",
    description="Return the chat details by Agent ID with paginated message records",
)
async def get_agent_chat_detail(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    limit: int = Query(20, ge=1, le=100, description="Number of messages per page"),
    offset: int = Query(0, ge=0, description="Offset (number of messages to skip)"),
) -> Any:
    """
    Get chat details by Agent ID with paginated message records
    If user hasn't created a session with this Agent, automatically create one
    Support scrolling to load earlier conversations
    """
    try:
        logger.debug(f"Getting Agent chat details - Agent ID: {agent_id}")

        # Get or create unique session with this Agent
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )

        # Verify if the agent_id in returned chat matches the input
        if chat.agent_id != agent_id:
            logger.error(f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}",
            )

        # Use unified session_id generation rule
        session_id = generate_session_id(chat.id)

        # Get paginated messages
        messages_data = chat_history_service.get_messages_paginated(
            session_id=session_id, limit=limit, offset=offset
        )

        # Assemble return data
        data = {
            "chat_info": {
                "id": chat.id,
                "agent_id": chat.agent_id,
                "agent_name": chat.agent_name,
                "agent_avatar": chat.agent_avatar,
                "user_id": chat.user_id,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
            },
            "messages": messages_data["messages"],
            "pagination": {
                "total": messages_data["total"],
                "limit": messages_data["limit"],
                "offset": messages_data["offset"],
                "page": messages_data["page"],
                "has_more": messages_data["has_more"],
                "total_pages": (
                    (messages_data["total"] + limit - 1) // limit if limit > 0 else 1
                ),
            },
        }
        return data

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get chat details: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/messages",
    tags=["inty-eval", "android-app"],
    summary="Get Agent Chat Messages",
    description="Get only chat message records by Agent ID (lighter interface)",
)
async def get_agent_chat_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
    limit: int = Query(20, ge=1, le=100, description="Number of messages per page"),
    offset: int = Query(0, ge=0, description="Offset"),
    order: str = Query(
        "desc",
        regex="^(asc|desc)$",
        description="Sort order: asc=old messages first, desc=new messages first",
    ),
) -> Any:
    """
    Get only chat message records by Agent ID (lighter interface)
    If user hasn't created a session with this Agent, automatically create one
    Specifically for scrolling load
    """
    try:
        logger.debug(f"Getting Agent chat messages - Agent ID: {agent_id}")

        # Get or create unique session with this Agent
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )

        # Verify if the agent_id in returned chat matches the input
        if chat.agent_id != agent_id:
            logger.error(f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}",
            )

        # Use unified session_id generation rule
        session_id = generate_session_id(chat.id)

        # ??????
        messages_data = chat_history_service.get_messages_paginated(
            session_id=session_id, limit=limit, offset=offset
        )

        # ??????????????????
        # ?????????????????????
        if order == "desc":
            messages_data["messages"].reverse()

        return messages_data

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get message records: {str(e)}"
        )


@router.post(
    "/agents/{agent_id}/chat/completions",
    deprecated=True,
    include_in_schema=False,
    summary="???? v1.0.3 app ?? app ????? API",
    description="??Agent ID?OpenAI?????????????? /chat/completions/{agent_id} ??",
)
async def agent_chat_completions(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: ChatCompletionRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    ??Agent ID?OpenAI??????
    ?????????Agent??????????
    The following code is copied from tag:v1.0.3
    """
    try:
        import time

        request_start_time = time.time()
        logger.info(
            f"???????? - Agent ID: {agent_id}, User ID: {current_user.id}"
        )
        logger.debug(f"????: {request.dict()}")
        logger.debug(f"request.messages??: {request.messages}")
        logger.debug(
            f"request.messages??: {len(request.messages) if request.messages else 0}"
        )

        # ??????????
        # is_allowed, used_count, daily_limit = await subscription_service.check_chat_limit(
        #     db, current_user.id
        # )

        # if not is_allowed:
        #     raise HTTPException(
        #         status_code=429,  # Too Many Requests
        #         detail={
        #             "message": "??????????",
        #             "used_count": used_count,
        #             "daily_limit": daily_limit,
        #             "error_code": "CHAT_LIMIT_EXCEEDED"
        #         }
        #     )

        # ?????Agent??????Agent?????
        agent_query_start = time.time()
        logger.debug(f"??Agent??: {agent_id}")

        # ????????????
        from sqlalchemy import select

        result = await db.execute(
            select(models.Agent.id, models.Agent.name).where(
                models.Agent.id == agent_id
            )
        )
        agent_basic = result.first()
        if not agent_basic:
            logger.error(f"Agent???: {agent_id}")
            raise HTTPException(status_code=404, detail="Agent not found")

        agent_query_time = time.time() - agent_query_start
        logger.info(f"Agent????: {agent_basic[1]}, ??: {agent_query_time:.3f}?")
        # ?????????agent_id
        logger.info(f"???Agent ID: {agent_id}")

        # ???????Agent?????
        chat_session_start = time.time()
        logger.debug(
            f"?????????: user_id={current_user.id}, agent_id={agent_id}"
        )
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )
        chat_session_time = time.time() - chat_session_start
        logger.info(
            f"????????: chat_id={chat.id}, agent_id={chat.agent_id}, ??: {chat_session_time:.3f}?"
        )

        # ?????chat??agent_id????????
        if chat.agent_id != agent_id:
            logger.error(f"Agent ID???: ??={agent_id}, ??={chat.agent_id}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent ID mismatch: expected={agent_id}, actual={chat.agent_id}",
            )

        # ???????agent_id
        logger.info(f"?????Agent ID: {chat.agent_id}")

        # ??????????
        msg_process_start = time.time()
        logger.debug(
            f"??messages: {[f'{msg.role}: {msg.content[:50]}...' for msg in request.messages]}"
        )
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        logger.debug(f"?????????: {len(user_messages)}")
        if not user_messages:
            logger.error("?????????")
            logger.error(f"?????role: {[msg.role for msg in request.messages]}")
            raise HTTPException(status_code=400, detail="No user message found")

        last_user_message = user_messages[-1].content
        logger.debug(f"????: {last_user_message[:100]}...")

        # ??LangChain????
        messages = {"messages": [HumanMessage(content=last_user_message)]}
        msg_process_time = time.time() - msg_process_start
        logger.info(f"??????: {msg_process_time:.3f}?")

        # ?????Agent?? - ????????
        agent_get_start = time.time()
        logger.debug(f"????Agent??: {chat.agent_id}")

        # ??????????Agent????
        agent_data = await agent_service.get_agent_for_chat(db, agent_id=chat.agent_id)
        if not agent_data:
            logger.error(f"Agent?????: {chat.agent_id}")
            raise HTTPException(status_code=404, detail="Agent not found")

        # ?AgentManager????Agent??
        agent = await agent_manager.get_agent(agent_data)
        agent_get_time = time.time() - agent_get_start
        logger.info(
            f"Agent??????: {agent_data['name']}, ??: {agent_get_time:.3f}?"
        )

        # ?????session_id????
        session_id_start = time.time()
        session_id = generate_session_id(chat.id)
        session_id_time = time.time() - session_id_start
        logger.info(f"Session ID????: {session_id_time:.3f}?")

        if request.stream:
            return StreamingResponse(
                generate_chat_stream(
                    agent=agent,
                    messages=messages,
                    user_id=current_user.id,
                    session_id=session_id,
                    chat_id=chat.id,
                    model_name=request.model,
                    db_session=db,
                    agent_id=agent_id,
                    last_user_message=last_user_message,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        else:
            # ?????????
            chat_processing_start = time.time()
            logger.debug(f"??Agent????: session_id={session_id}")

            # ???????????AI??
            try:

                # ??????????
                chat_settings = await chat_service.get_or_create_chat_settings(
                    db, chat.id, current_user.id, agent_id
                )

                # ????AI??
                response_content = await agent.chat(
                    user_id=current_user.id,
                    session_id=session_id,
                    messages=messages,
                )
                chat_processing_time = time.time() - chat_processing_start
                logger.info(
                    f"Agent??????: {response_content[:100]}..., ??: {chat_processing_time:.3f}?"
                )
                logger.debug(
                    f"????????: voice_enabled={chat_settings.voice_enabled}"
                )

            except Exception as e:
                logger.error(f"Agent??????: {str(e)}")
                raise

            # ?????? - ??chat_settings.voice_enabled????????
            audio_url = None
            try:
                # ?????????chat_settings.voice_enabled = true ???????
                if chat_settings.voice_enabled:
                    # ??Agent?voice_id??
                    agent_voice_id = agent_data.get("voice_id")
                    logger.info(
                        f"??????: voice_id={agent_voice_id}, text_length={len(response_content)}, language={request.language}"
                    )

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
                        logger.info(
                            f"????????: {audio_url}, ??: {audio_duration:.2f}?"
                        )
                    else:
                        audio_url, audio_duration = None, None
                else:
                    logger.debug("????????????")

            except Exception as e:
                logger.error(f"??????: {str(e)}")
                logger.exception("??????????:")
                # ?????????????

            # ????????
            try:
                logger.debug(f"????????: user_id={current_user.id}")
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
                logger.debug("??????????")
            except Exception as e:
                logger.warning(f"??????????: {str(e)}")

            # ??????
            message = {"role": "assistant", "content": response_content}

            # ??????????????
            if audio_url:
                message["audio_url"] = audio_url
                logger.info(f"??????URL: {audio_url}")

            # ????AI???????
            try:
                latest_message_info = (
                    await chat_history_service.get_latest_ai_message_info(
                        db, session_id
                    )
                )
            except Exception as e:
                logger.warning(f"??????????: {str(e)}")
                latest_message_info = None

            # ??????????id, meta_data, timestamp??
            if latest_message_info:
                message["id"] = latest_message_info["id"]
                message["meta_data"] = latest_message_info["meta_data"]
                message["timestamp"] = latest_message_info["timestamp"]
                # ???????audio_url????????????????
                if latest_message_info["audio_url"]:
                    message["audio_url"] = latest_message_info["audio_url"]

            total_request_time = time.time() - request_start_time

            # ?????????????? (HttpResult<SendMsgResponse>)
            response_data = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",  # ?????????ID
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": len(last_user_message.split()),
                    "completion_tokens": len(response_content.split()),
                    "total_tokens": len(last_user_message.split())
                    + len(response_content.split()),
                },
            }

            logger.info(
                f"????????: agent_id={agent_id}, ???: {total_request_time:.3f}?"
            )

            return response_data

    except Exception as e:
        logger.error(f"????????: {str(e)}")
        logger.exception("??????????:")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post(
    "/agents/{agent_id}/messages/{message_id}/voice",
    tags=["inty", "voice", "android-app"],
    summary="Generate Message Voice",
    description="Generate voice for a message",
)
async def generate_message_voice(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    message_id: str,
    language: str = Query("zh", description="????"),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    ?????????
    ??????????????????
    """
    try:
        # ??????????Agent????
        agent_data = await agent_service.get_agent_for_chat(db, agent_id=agent_id)
        if not agent_data:
            raise HTTPException(status_code=404, detail="Agent not found")

        # ??????Agent???
        chat = await chat_service.get_chat_by_user_and_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        # ????????????
        session_id = generate_session_id(chat.id)
        message_content = await chat_history_service.get_message_content(
            db=db, session_id=session_id, message_id=message_id
        )

        if not message_content:
            raise HTTPException(status_code=404, detail="Message not found")

        # ??Agent?voice_id????
        agent_voice_id = agent_data.get("voice_id")
        voice_result = await voice_service.generate_voice(
            text=message_content,
            voice_id=agent_voice_id,
            language=language,
            db=db,
            agent_gender=agent_data.get("gender"),
            user=current_user,
        )

        if not voice_result:
            # ???????????
            from app.services.global_services import subscription_service

            (
                is_allowed,
                used_count,
                limit,
            ) = await subscription_service.check_voice_generation_limit(
                db, current_user
            )
            if not is_allowed:
                from app.models.user import AuthType

                if current_user.auth_type == AuthType.GUEST:
                    # ?????????
                    return create_business_error_response(
                        error_info=BusinessErrorCode.GUEST_LOGIN_REQUIRED,
                        extra_data={"used_count": used_count, "limit": limit},
                    )
                else:
                    # ????????????
                    return create_business_error_response(
                        error_info=BusinessErrorCode.VOICE_GENERATION_LIMIT_REACHED,
                        extra_data={"used_count": used_count, "limit": limit},
                    )
            raise HTTPException(status_code=500, detail="Voice generation failed")

        audio_url, audio_duration = voice_result
        logger.debug(f"????????: {audio_url}, ??: {audio_duration:.2f}?")

        # ??chat_history??????audio_url
        # ??try-except?????????API??
        try:
            update_success = await chat_history_service.update_message_audio_url(
                db=db,
                session_id=session_id,
                message_id=message_id,
                audio_url=audio_url,
                audio_duration=audio_duration,
            )
            if update_success:
                logger.debug(f"??????{message_id}?audio_url?chat_history")
            else:
                logger.warning(f"????{message_id}?audio_url?chat_history??")
        except Exception as e:
            logger.error(f"??chat_history?audio_url?????: {str(e)}")
            # ????????API??

        return APIResponse.success(
            data={
                "audio_url": audio_url,
                "message_id": message_id,
                "voice_id": agent_voice_id
                or global_config_loaded_from_config_yaml.elevenlabs.voice_id,
                "language": language,
                "audio_duration": audio_duration,  # ???????
                "cached": False,  # ????????????
                "generation_time": None,  # ????????
            }
        )

    except Exception as e:
        logger.error(f"????????: {str(e)}")
        return APIResponse.error(message=f"Voice generation failed: {str(e)}", code=500)


@router.get(
    "/voices/{voice_id}",
    deprecated=True,
    include_in_schema=True,
    tags=["inty", "voice"],
    summary="Get Voice Info",
    description="Get voice info by voice_id",
)
async def get_voice_info(
    voice_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    ?????????
    """
    try:
        voice_info = await voice_service.get_voice_info(voice_id)
        if not voice_info:
            raise HTTPException(status_code=404, detail="Voice not found")

        return voice_info
    except Exception as e:
        logger.error(f"????????: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get voice info: {str(e)}"
        )


@router.put(
    "/agents/{agent_id}/settings",
    tags=["inty", "android-app"],
    summary="Update Chat Settings by Agent ID",
    description=(
        "We do not use chat_id to get settings, because we only support 1 chat per agent."
        "TODO: We should switch to /chats/{chat_id}/settings"
    ),
    response_model=Union[
        # TODO: Why do we use union here?
        schemas.APIResponse[schemas.ChatSettings],
        schemas.APIResponse[dict],
    ],
)
async def update_agent_chat_settings(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    settings_update: schemas.ChatSettingsUpdate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update chat settings by Agent ID
    Input agent_id, find user's unique chat session with that Agent, update chat settings
    If chat session doesn't exist, automatically create one
    """
    try:
        logger.info(
            f"Updating Agent chat settings - Agent ID: {agent_id}, User ID: {current_user.id}"
        )

        # First verify if Agent exists
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Get or create unique session with this Agent
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )

        # Verify if the agent_id in returned chat matches the input
        if chat.agent_id != agent_id:
            logger.error(f"Agent ID mismatch: input={agent_id}, actual={chat.agent_id}")
            raise HTTPException(status_code=500, detail=f"Agent ID mismatch")

        # Get or create chat settings, then update
        # First ensure settings exist
        settings = await chat_service.get_or_create_chat_settings(
            db=db, chat_id=chat.id, user_id=current_user.id, agent_id=agent_id
        )

        subscription_status = await subscription_service.get_user_subscription_status(
            db, current_user.id
        )

        # Check if trying to update style_prompt and if user has subscription
        # style_prompt is only available for subscribed users or superusers
        if settings_update.style_prompt and not is_eligible_for_premium(
            current_user, subscription_status
        ):
            return create_business_error_response(
                error_info=BusinessErrorCode.SUBSCRIPTION_REQUIRED
            )

        # Check if trying to update premium_mode and if user has subscription
        if settings_update.premium_mode and not is_eligible_for_premium(
            current_user, subscription_status
        ):
            return create_business_error_response(
                error_info=BusinessErrorCode.SUBSCRIPTION_REQUIRED
            )

        # Then update settings
        settings = await chat_service.update_chat_settings(
            db=db, chat_id=chat.id, settings_update=settings_update
        )

        logger.info(
            f"Successfully updated Agent chat settings - Agent ID: {agent_id}, Settings ID: {settings.id}"
        )

        return schemas.APIResponse.success(data=settings)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update Agent chat settings - Agent ID: {agent_id}, Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to update chat settings: {str(e)}"
        )


# TODO: Should we switch to /chats/{chat_id}/settings?
@router.get(
    "/agents/{agent_id}/settings",
    response_model=schemas.ChatSettings,
    tags=["inty", "android-app"],
    summary="Get Agent Chat Settings",
    description=(
        "[Deprecated, use /chats/{chat_id}/settings instead] Get chat settings by Agent ID, bause we only support 1 chat per agent, "
        "so we do not use chat_id to get settings"
    ),
)
async def get_agent_chat_settings(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get chat settings by Agent ID
    If chat session or settings don't exist, automatically create them
    """
    try:
        logger.info(
            f"Getting Agent chat settings - Agent ID: {agent_id}, User ID: {current_user.id}"
        )

        # First verify if Agent exists
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Get or create unique session with this Agent
        chat = await chat_service.get_or_create_chat_by_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )

        # Get or create chat settings
        settings = await chat_service.get_or_create_chat_settings(
            db=db, chat_id=chat.id, user_id=current_user.id, agent_id=agent_id
        )

        logger.info(
            f"Successfully got Agent chat settings - Agent ID: {agent_id}, Settings ID: {settings.id}"
        )

        return settings

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get Agent chat settings - Agent ID: {agent_id}, Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get chat settings: {str(e)}"
        )


# TODO: Should we switch to /chats/{chat_id}?
@router.delete(
    "/agents/{agent_id}/chats",
    response_model=schemas.ChatDeletionResponse,
    deprecated=True,
    include_in_schema=False,
    tags=["inty"],
    summary="Delete Agent Chats",
    description="[Deprecated, use /chats/{chat_id} instead] Delete all chats by Agent ID",
)
async def delete_agent_chats(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    ???????Agent???????
    ????????????????
    """
    try:
        logger.info(
            f"??Agent???? - Agent ID: {agent_id}, User ID: {current_user.id}"
        )

        # ????Agent????
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")

        # ??service???????
        result = await chat_service.delete_chats_by_agent_id(
            db=db, agent_id=agent_id, user_id=current_user.id
        )

        logger.info(
            f"Agent???????? - Agent ID: {agent_id}, User ID: {current_user.id}, "
            f"????: {result}"
        )

        return {"success": True, "message": "????????", "data": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"??Agent?????? - Agent ID: {agent_id}, User ID: {current_user.id}, Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to delete chat record: {str(e)}"
        )


@router.get(
    "/agents/{agent_id}/debug-messages",
    deprecated=True,
    include_in_schema=False,
    tags=["inty-eval"],
    summary="Get Agent Debug Messages",
    description="Get Agent Debug Messages by Agent ID",
)
async def get_agent_debug_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    ??Agent???????
    ??Agent ID??????Agent???????debug_messages??
    """
    try:
        logger.debug(
            f"??Agent???? - Agent ID: {agent_id}, User ID: {current_user.id}"
        )

        # ????Agent????
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")

        # ??????Agent?????
        chat = await chat_service.get_chat_by_agent_and_user(
            db=db, agent_id=agent_id, user_id=current_user.id
        )

        if not chat:
            # ?????????????????
            return {
                "chat_id": None,
                "agent_id": agent_id,
                "agent_name": agent_db.name,
                "debug_messages": None,
                "message": "No chat session found with this agent",
            }

        # ??????
        return {
            "chat_id": chat.id,
            "agent_id": chat.agent_id,
            "agent_name": chat.agent_name or agent_db.name,
            "debug_messages": chat.debug_messages,
            "last_updated": chat.updated_at.isoformat() if chat.updated_at else None,
            "message": (
                "Debug messages retrieved successfully"
                if chat.debug_messages
                else "No debug messages available"
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"??Agent?????? - Agent ID: {agent_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get debug messages: {str(e)}"
        )


@router.post(
    "/agents/{agent_id}/clear-messages",
    response_model=schemas.ClearMessagesResponse,
    include_in_schema=False,
    tags=["inty-eval"],
    summary="Clear Agent Chat Messages",
    description="Clear chat messages by Agent ID, currently used by inty-eval, probably will be used by inty app as well.",
)
async def clear_agent_chat_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: schemas.ClearMessagesRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    ????Agent????????????
    ???????
    1. ????ID???ID???????
    2. ?????????????????
    """
    try:
        logger.info(
            f"??Agent???? - Agent ID: {agent_id}, User ID: {current_user.id}"
        )

        # ??????
        if not request.message_id and not request.timestamp:
            raise HTTPException(
                status_code=400, detail="???? message_id ? timestamp ??????"
            )

        if request.message_id and request.timestamp:
            raise HTTPException(
                status_code=400,
                detail="???? message_id ? timestamp ?????????????",
            )

        # ??Agent????
        agent_db = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent_db:
            raise HTTPException(status_code=404, detail="Agent not found")

        # ??????Agent?????
        chat = await chat_service.get_chat_by_user_and_agent(
            db=db, user_id=current_user.id, agent_id=agent_id
        )

        if not chat:
            raise HTTPException(status_code=404, detail="?????Agent?????")

        # ??session_id
        session_id = generate_session_id(chat.id)

        # ??????
        if request.message_id is not None:
            # ???ID??
            result = chat_history_service.clear_messages_after_id(
                session_id=session_id, message_id=request.message_id
            )
        else:
            # ??????
            result = chat_history_service.clear_messages_after_timestamp(
                session_id=session_id, timestamp=request.timestamp
            )

        # ????????????? debug_messages ??
        if result.get("success", False):
            chat.debug_messages = None
            await db.commit()
            logger.debug(f"??? debug_messages ?? - Chat ID: {chat.id}")

        logger.info(f"???????? - Agent ID: {agent_id}, ??: {result}")

        return schemas.ClearMessagesResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"??Agent?????? - Agent ID: {agent_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to clear messages: {str(e)}"
        )


@router.post(
    "/agents/{agent_id}/generate-image",
    deprecated=True,
    include_in_schema=False,
    response_model=schemas.APIResponse[schemas.ChatImageGenerationResponse],
    summary="[Deprecated, use /api/v1/chat/images/{agent_id} instead] ???????????",
    description="[Deprecated, use /api/v1/chat/images/{agent_id} instead] ??Agent??????????????????????????",
    tags=["inty-eval"],
)
async def generate_chat_image(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    request: schemas.ChatImageGenerationRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    ???????????

    ???
    1. ?????Agent
    2. ?????????
    3. ????????
    4. ????????
    5. ????
    6. ??????

    ???
    - ???????? `chat_service.generate_chat_image`
    """
    try:
        result = await chat_service.generate_chat_image(
            db=db,
            agent_id=agent_id,
            user_id=current_user.id,
            message_id=request.message_id,
            history_count=request.history_count,
        )

        # 检查是否返回了业务限制错误
        if isinstance(result, UsageLimitExceeded):
            # 转换为兼容现有客户端的业务错误响应格式
            return create_business_error_response(
                error_info={
                    "code": result.code,
                    "error_code": result.error_code,
                    "message": result.message,
                },
                extra_data={
                    "used_count": result.used_count,
                    "daily_limit": result.daily_limit,
                },
            )

        return schemas.APIResponse.success(data=result)

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"???????? - Agent ID: {agent_id}, Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate image: {str(e)}"
        )
