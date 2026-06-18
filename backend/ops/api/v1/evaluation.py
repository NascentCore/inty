"""评测系统API端点 - 专门用于评测聊天系统效果"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ops.schemas.evaluation import (
    BatchEvaluationRequest,
    EvaluationComparison,
    EvaluationExportRequest,
    EvaluationResultResponse,
    EvaluationSessionCreate,
    EvaluationSessionDetail,
    EvaluationSessionResponse,
    EvaluationStats,
    EvaluationTemplateCreate,
    EvaluationTemplateResponse,
    QuestionFileUpload,
    ScoringModelInfo,
)
from app.api import deps
from app.api.tags import INTY_EVAL_TAG, NOT_USED_TAG
from app.api.utils.logger_route import LoggerRoute
from backend.ops.schemas.user_analytics import (
    AgentAnalyticsResponse,
    ConversationRoundsResponse,
    ConversationsDetailResponse,
    DailyNewUsersResponse,
    DailyVoiceAudiosResponse,
    ImageGenerationFailureAnalyticsResponse,
    ImageGenerationLatencyResponse,
    LiveChatBasicStatsResponse,
    LiveChatLatencyResponse,
    LLMLatencyResponse,
    PaginatedUserAgentConversationsResponse,
    PopularAgentsResponse,
    SessionMessagesResponse,
    UserAnalyticsReportCharts,
    UserAnalyticsReportItem,
    UserAnalyticsReportsResponse,
    UserAnalyticsStatsResponse,
    UserChatActivityItem,
    UserDailyMessagesResponse,
    UserGeneratedImagesResponse,
    UserRoundsDistributionItem,
    UserSessionsDetailResponse,
    UserSessionsResponse,
    UserTodayStatsResponse,
    UsersHittingLimitResponse,
    VoiceAudioGroupByUserAgent,
    VoiceAudioItem,
)
from app.services.evaluation_service import EvaluationService
from app.services.question_parser_service import QuestionParserService
from app.services.scoring_service import ScoringService

from loguru import logger
from app.schemas.agent import Agent as AgentSchema
from app.schemas.agent import AgentCreate
from app.schemas.agent import AgentUpdate
from app.schemas.response import APIResponse
from app.schemas.user import User as UserSchema

router = APIRouter(prefix="/evaluation", route_class=LoggerRoute)


@router.get(
    "/sessions",
    response_model=List[EvaluationSessionResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_evaluation_sessions(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
    status: Optional[str] = Query(None, description="按状态过滤"),
) -> Any:
    """
    获取评测会话列表

    返回当前用户创建的评测会话列表
    """
    try:
        evaluation_service = EvaluationService(db)

        sessions = await evaluation_service.get_user_sessions(
            user_id=current_user.id, skip=skip, limit=limit, status=status
        )

        return sessions

    except Exception as e:
        logger.error(f"获取评测会话列表失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch evaluation sessions"
        )


@router.post(
    "/sessions",
    response_model=EvaluationSessionResponse,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def create_evaluation_session(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    session_in: EvaluationSessionCreate,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    创建评测会话

    用于评测当前聊天系统的智能体对话效果
    """
    try:
        evaluation_service = EvaluationService(db)

        session = await evaluation_service.create_session(
            creator_id=current_user.id,
            name=session_in.name,
            questions=session_in.questions,
            selected_agents=session_in.selected_agents,
            scoring_model=session_in.scoring_model,
            scoring_criteria=session_in.scoring_criteria,
            use_new_user_identity=session_in.use_new_user_identity,
            config=session_in.config,
        )

        logger.info(f"用户 {current_user.id} 创建评测会话: {session.id}")
        return session

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建评测会话失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to create evaluation session"
        )


@router.post(
    "/sessions/{session_id}/start",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def start_evaluation_session(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    session_id: str,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    启动评测会话

    开始执行对智能体的批量测试和评分
    """
    try:
        evaluation_service = EvaluationService(db)

        # 验证会话所有权
        session = await evaluation_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404, detail="Evaluation session not found"
            )

        if session.creator_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to operate this evaluation session",
            )

        success = await evaluation_service.start_session(session_id)

        logger.info(f"用户 {current_user.id} 启动评测会话: {session_id}")
        return {"success": success, "message": "评测会话已启动"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"启动评测会话失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to start evaluation session"
        )


@router.get(
    "/sessions/{session_id}",
    response_model=EvaluationSessionDetail,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_evaluation_session(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    session_id: str,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    获取评测会话详情

    包含完整的测试结果和交互记录
    """
    try:
        evaluation_service = EvaluationService(db)

        session = await evaluation_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404, detail="Evaluation session not found"
            )

        if session.creator_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this evaluation session",
            )

        return session

    except Exception as e:
        logger.error(f"获取评测会话详情失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch session details"
        )


@router.get(
    "/sessions/{session_id}/results",
    response_model=List[EvaluationResultResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_evaluation_results(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    session_id: str,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    获取评测结果

    返回指定会话的所有测试结果
    """
    try:
        evaluation_service = EvaluationService(db)

        # 验证权限
        session = await evaluation_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404, detail="Evaluation session not found"
            )

        if session.creator_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this evaluation session",
            )

        results = await evaluation_service.get_session_results(session_id)
        return results

    except Exception as e:
        logger.error(f"获取评测结果失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch evaluation results"
        )


@router.post(
    "/sessions/{session_id}/cancel",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def cancel_evaluation_session(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    session_id: str,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    取消评测会话

    停止正在进行的评测任务
    """
    try:
        evaluation_service = EvaluationService(db)

        # 验证权限
        session = await evaluation_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404, detail="Evaluation session not found"
            )

        if session.creator_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to operate this evaluation session",
            )

        success = await evaluation_service.cancel_session(session_id)

        logger.info(f"用户 {current_user.id} 取消评测会话: {session_id}")
        return {"success": success, "message": "评测会话已取消"}

    except Exception as e:
        logger.error(f"取消评测会话失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to cancel evaluation session"
        )


@router.post(
    "/questions/parse",
    response_model=QuestionFileUpload,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def parse_questions_file(
    *,
    file: UploadFile = File(...),
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    解析问题文件

    支持txt、csv、json格式的问题文件上传和解析
    """
    try:
        # 验证文件大小（最大10MB）
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400, detail="File size cannot exceed 10MB"
            )

        # 验证文件类型
        allowed_types = [".json"]
        if not any(
            file.filename.lower().endswith(ext) for ext in allowed_types
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported file type. Only supported: "
                    f"{', '.join(allowed_types)}"
                ),
            )

        questions = await QuestionParserService.parse_questions_file(file)

        # 验证问题质量
        validation = QuestionParserService.validate_questions(questions)

        logger.info(
            f"用户 {current_user.id} 上传问题文件: {file.filename}, 解析出 {len(questions)} 个问题"
        )

        return {
            "questions": questions,
            "total_count": validation["stats"]["total"],
            "valid_count": validation["stats"]["valid"],
            "duplicates_removed": validation["stats"]["duplicates"],
            "warnings": validation.get("warnings", []),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解析问题文件失败: {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Failed to parse file: {str(e)}"
        )


@router.get(
    "/models",
    response_model=List[ScoringModelInfo],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_scoring_models(
    *,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    获取可用模型列表
    """
    try:
        scoring_service = ScoringService()
        models = await scoring_service.get_available_models()
        return models

    except Exception as e:
        logger.error(f"获取评分模型失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch scoring models"
        )


@router.post(
    "/scoring-criteria/validate",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def validate_scoring_criteria(
    *,
    criteria: str,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    验证评分标准

    检查评分标准的格式和完整性
    """
    try:
        scoring_service = ScoringService()
        validation = scoring_service.validate_scoring_criteria(criteria)
        return validation

    except Exception as e:
        logger.error(f"验证评分标准失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to validate scoring criteria"
        )


@router.get(
    "/stats",
    response_model=EvaluationStats,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_evaluation_stats(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
) -> Any:
    """
    获取评测统计信息

    显示用户的评测历史和统计数据
    """
    try:
        # 这里可以实现统计逻辑
        # 暂时返回模拟数据
        return {
            "total_sessions": 0,
            "completed_sessions": 0,
            "running_sessions": 0,
            "failed_sessions": 0,
            "average_score": None,
            "success_rate": None,
            "total_tests": 0,
            "total_agents_tested": 0,
        }

    except Exception as e:
        logger.error(f"获取评测统计失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch statistics"
        )


# WebSocket端点用于实时监控评测进度
@router.websocket("/sessions/{session_id}/monitor")
async def monitor_evaluation_session(
    websocket,
    session_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
):
    """
    实时监控评测会话进度

    通过WebSocket推送评测进度和结果
    """
    await websocket.accept()

    try:
        evaluation_service = EvaluationService(db)

        # 添加WebSocket连接
        evaluation_service.add_websocket_connection(session_id, websocket)

        # 发送初始状态
        session = await evaluation_service.get_session(session_id)
        if session:
            await websocket.send_json(
                {
                    "type": "session_status",
                    "data": {
                        "session_id": session_id,
                        "status": session.status.value,
                        "progress": (
                            session.completed_tests / session.total_tests * 100
                            if session.total_tests > 0
                            else 0
                        ),
                    },
                }
            )

        # 保持连接
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                logger.exception(
                    "evaluation monitor websocket receive failed session_id={}",
                    session_id,
                )
                break

    except Exception as e:
        logger.error(f"WebSocket连接错误: {str(e)}")
    finally:
        # 移除连接
        evaluation_service = EvaluationService(db)
        evaluation_service.remove_websocket_connection(session_id, websocket)


# =============================================================================
# 智能体管理相关API（用于评测系统的智能体CRUD操作）
# =============================================================================


@router.get(
    "/agents",
    response_model=List[AgentSchema],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_evaluation_agents(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    type: str = Query(
        "public", pattern="^(public|private)$", description="智能体类型"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> Any:
    """
    获取用于评测的智能体列表

    支持获取公开和私有智能体，用于评测系统选择测试对象
    """
    try:
        from app.services import agent_service

        if type == "private":
            # 获取用户创建的私有智能体
            agents = await agent_service.get_agents_by_creator(
                db, creator_id=current_user.id, skip=skip, limit=limit
            )
        else:
            # 获取公开智能体
            agents = await agent_service.get_public_agents(
                db, skip=skip, limit=limit
            )

        logger.info(
            f"用户 {current_user.id} 获取评测智能体列表: {type}, 数量: {len(agents)}"
        )
        return agents

    except Exception as e:
        logger.error(f"获取智能体列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch agents")


@router.post(
    "/agents",
    response_model=AgentSchema,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def create_evaluation_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_in: AgentCreate,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    创建用于评测的智能体

    在评测系统中创建新的智能体用于测试
    """
    try:
        from app.services import agent_service

        agent = await agent_service.create_agent(
            db=db, agent_in=agent_in, creator_id=current_user.id
        )

        logger.info(f"用户 {current_user.id} 创建评测智能体: {agent.id}")
        return agent

    except Exception as e:
        logger.error(f"创建智能体失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create agent")


@router.put(
    "/agents/{agent_id}",
    response_model=AgentSchema,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def update_evaluation_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    agent_in: AgentUpdate,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    更新评测智能体

    修改智能体的配置和提示词等信息
    """
    try:
        from app.services import agent_service

        # 验证权限
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        if agent.creator_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to update this agent"
            )

        updated_agent = await agent_service.update_agent(
            db=db, agent_id=agent_id, agent_in=agent_in
        )

        logger.info(f"用户 {current_user.id} 更新智能体: {agent_id}")
        return updated_agent

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新智能体失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update agent")


@router.delete(
    "/agents/{agent_id}",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def delete_evaluation_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    删除评测智能体

    删除用户创建的私有智能体
    """
    try:
        from app.services import agent_service

        # 验证权限
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        if agent.creator_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to delete this agent"
            )

        await agent_service.delete_agent(db=db, agent_id=agent_id)

        logger.info(f"用户 {current_user.id} 删除智能体: {agent_id}")
        return {"message": "智能体已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除智能体失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete agent")


@router.get(
    "/agents/{agent_id}/check-background-aspect-ratio",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def check_background_aspect_ratio(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    检查背景图是否为 9:16 比例

    用于生成背景动图前验证背景图比例
    """
    try:
        import io

        import PIL.Image

        from app.external_services.gcs import download_from_gcs
        from app.services import agent_service
        from app.services.image_transform_service import image_transform_service
        from app.utils.image import check_aspect_ratio_9_16

        # 验证 Agent 存在且用户有权限
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        if agent.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

        # 验证背景图是否存在
        if not agent.background:
            raise HTTPException(
                status_code=400, detail="Please upload a background image first"
            )

        # 将背景图 URL 转换为 GCS URI 格式
        background_url = agent.background
        background_gcs_uri = None

        # 如果是 CDN URL，先转换为 GCS URL
        if image_transform_service.is_cloudflare_url(background_url):
            gcs_url = image_transform_service.cloudflare_to_gcs(background_url)
            if gcs_url:
                gcs_path = image_transform_service.extract_gcs_path(gcs_url)
                if gcs_path:
                    background_gcs_uri = f"gs://{gcs_path}"
        elif image_transform_service.is_gcs_url(background_url):
            gcs_path = image_transform_service.extract_gcs_path(background_url)
            if gcs_path:
                background_gcs_uri = f"gs://{gcs_path}"
        else:
            background_gcs_uri = background_url

        if not background_gcs_uri:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Unable to get background image URL. Please upload the image "
                    "again"
                ),
            )

        # 下载图片并检查尺寸
        image_bytes = download_from_gcs(background_gcs_uri)
        pil_image = PIL.Image.open(io.BytesIO(image_bytes))
        width, height = pil_image.size
        aspect_ratio = width / height
        is_9_16 = check_aspect_ratio_9_16((width, height))

        return {
            "is_9_16": is_9_16,
            "width": width,
            "height": height,
            "aspect_ratio": round(aspect_ratio, 4),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查背景图宽高比失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to validate background image aspect ratio",
        )


@router.post(
    "/agents/{agent_id}/upload-cropped-background",
    response_model=APIResponse[AgentSchema],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def upload_cropped_background(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    file: UploadFile = File(...),
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    上传裁剪后的背景图

    替换智能体的背景图为裁剪后的 9:16 比例图片
    """
    try:
        from app.schemas.agent import AgentUpdate
        from app.services import agent_service
        from app.utils.image_upload import process_image_upload

        # 验证 Agent 存在且用户有权限
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        if agent.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

        # 上传裁剪后的图片
        result = await process_image_upload(
            file=file,
            user_id=current_user.id,
            async_db=db,
            base_path="backgrounds",
            cropping_avatar=False,
        )

        if not result.data:
            raise HTTPException(
                status_code=400, detail=result.message or "Image upload failed"
            )

        # 更新 Agent 的背景图
        agent_update = AgentUpdate(background=result.data.url)
        updated_agent = await agent_service.update_agent(
            db, db_agent=agent, agent_in=agent_update
        )

        logger.info(
            f"用户 {current_user.id} 为智能体 {agent_id} 上传裁剪后的背景图: {result.data.url}"
        )
        return APIResponse.success(data=updated_agent)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传裁剪后的背景图失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to upload cropped background image"
        )


@router.post(
    "/agents/{agent_id}/deploy",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def deploy_agent_to_production(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    admin_password: str,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    将智能体部署到生产环境

    需要管理员权限，将测试智能体上线到生产环境
    """
    try:
        # 这里应该实现实际的部署逻辑
        # 暂时返回模拟响应
        logger.info(
            f"用户 {current_user.id} 请求部署智能体 {agent_id} 到生产环境"
        )

        return {
            "success": True,
            "message": "智能体部署成功",
            "agent_id": agent_id,
            "deploy_time": "2025-07-26T00:00:00Z",
        }

    except Exception as e:
        logger.error(f"部署智能体失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to deploy agent")


# =============================================================================
# 模板管理API
# =============================================================================


@router.post(
    "/templates",
    response_model=EvaluationTemplateResponse,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def create_evaluation_template(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    template_in: EvaluationTemplateCreate,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    创建评测模板

    保存常用的问题集和评分标准为模板
    """
    try:
        import uuid

        from app.models.evaluation import EvaluationTemplate

        template = EvaluationTemplate(
            id=str(uuid.uuid4()),
            name=template_in.name,
            description=template_in.description,
            creator_id=current_user.id,
            questions=template_in.questions,
            default_scoring_criteria=template_in.default_scoring_criteria,
            recommended_models=template_in.recommended_models,
            config=template_in.config,
            tags=template_in.tags,
            is_public=template_in.is_public,
            usage_count=0,
            is_active=True,
        )

        db.add(template)
        await db.commit()
        await db.refresh(template)

        logger.info(f"用户 {current_user.id} 创建评测模板: {template.id}")
        return template

    except Exception as e:
        logger.error(f"创建评测模板失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to create evaluation template"
        )


@router.get(
    "/templates",
    response_model=List[EvaluationTemplateResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_evaluation_templates(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    include_public: bool = Query(True, description="是否包含公开模板"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """
    获取评测模板列表

    返回用户的模板和公开模板
    """
    try:
        from sqlalchemy import or_, select

        from app.models.evaluation import EvaluationTemplate

        # 构建查询条件
        conditions = [EvaluationTemplate.creator_id == current_user.id]
        if include_public:
            conditions.append(EvaluationTemplate.is_public)

        stmt = (
            select(EvaluationTemplate)
            .where(or_(*conditions))
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        templates = result.scalars().all()

        return templates

    except Exception as e:
        logger.error(f"获取评测模板失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch evaluation templates"
        )


# =============================================================================
# 批量评测和结果导出API
# =============================================================================


@router.post(
    "/sessions/batch",
    response_model=List[EvaluationSessionResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def create_batch_evaluation(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    batch_request: BatchEvaluationRequest,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    批量创建评测会话

    一次性创建多个评测会话
    """
    try:
        evaluation_service = EvaluationService(db)
        sessions = []

        for session_data in batch_request.sessions:
            session = await evaluation_service.create_session(
                creator_id=current_user.id,
                name=session_data.name,
                questions=session_data.questions,
                selected_agents=session_data.selected_agents,
                scoring_model=session_data.scoring_model,
                scoring_criteria=session_data.scoring_criteria,
                use_new_user_identity=session_data.use_new_user_identity,
                config=session_data.config,
            )
            sessions.append(session)

        logger.info(
            f"用户 {current_user.id} 批量创建 {len(sessions)} 个评测会话"
        )
        return sessions

    except Exception as e:
        logger.error(f"批量创建评测失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to create evaluations in batch"
        )


@router.post(
    "/results/export",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def export_evaluation_results(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    export_request: EvaluationExportRequest,
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    导出评测结果

    将评测结果导出为CSV、JSON或Excel格式
    """
    try:
        # 这里应该实现实际的导出逻辑
        # 暂时返回下载链接
        logger.info(
            f"用户 {current_user.id} 导出评测结果: {len(export_request.session_ids)} 个会话"
        )

        return {
            "download_url": f"/evaluation/downloads/{current_user.id}/export.{export_request.format}",
            "format": export_request.format,
            "session_count": len(export_request.session_ids),
        }

    except Exception as e:
        logger.error(f"导出评测结果失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to export evaluation results"
        )


@router.post(
    "/sessions/compare",
    response_model=EvaluationComparison,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def compare_evaluation_sessions(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    session_ids: List[str],
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    对比评测会话结果

    分析多个会话的结果差异
    """
    try:
        # 这里应该实现实际的对比逻辑
        # 暂时返回模拟数据
        logger.info(f"用户 {current_user.id} 对比评测会话: {session_ids}")

        return {
            "agents": [],
            "questions": [],
            "results": {},
            "summary": {
                "best_agent": None,
                "average_score": None,
                "score_variance": None,
            },
        }

    except Exception as e:
        logger.error(f"对比评测会话失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to compare evaluation sessions"
        )


# =============================================================================
# 用户数据分析API
# =============================================================================


def _parse_analytics_date_ranges(
    register_start_date: Optional[str],
    register_end_date: Optional[str],
    register_last_days: Optional[int],
    activity_start_date: Optional[str],
    activity_end_date: Optional[str],
    activity_last_days: Optional[int],
) -> tuple:
    """解析用户分析的双日期范围参数

    返回: (register_start, register_end, activity_start, activity_end)
    如果注册日期范围未提供，则默认查询全部数据（从 2020-01-01 至今）
    如果活跃日期范围未提供，则默认与注册日期范围相同
    """
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)

    # 解析注册日期范围
    if register_last_days:
        reg_end = now
        reg_start = now - timedelta(days=register_last_days)
    elif register_start_date and register_end_date:
        reg_start = datetime.strptime(register_start_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        reg_end = datetime.strptime(register_end_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        ) + timedelta(days=1)
    else:
        # 当没有提供注册日期范围时，默认查询全部数据
        reg_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        reg_end = now

    # 解析活跃日期范围（如果提供）
    act_start = None
    act_end = None
    if activity_last_days:
        act_end = now
        act_start = now - timedelta(days=activity_last_days)
    elif activity_start_date and activity_end_date:
        act_start = datetime.strptime(activity_start_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        act_end = datetime.strptime(activity_end_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        ) + timedelta(days=1)

    return reg_start, reg_end, act_start, act_end


def _normalize_user_lookup_params(
    email: Optional[str], user_id: Optional[str], *, allow_empty: bool = False
) -> tuple[Optional[str], Optional[str]]:
    normalized_email = email.strip() if email else None
    normalized_user_id = user_id.strip() if user_id else None

    # allow_empty=True 时，允许两者都不提供（用于全量日期范围查询）
    if allow_empty and not normalized_email and not normalized_user_id:
        return None, None

    # 默认规则：必须且只能提供其中一个
    if bool(normalized_email) == bool(normalized_user_id):
        raise HTTPException(
            status_code=400,
            detail="Provide either email or user_id, but not both",
        )

    return normalized_email, normalized_user_id


async def _find_user_info_by_identifier(
    service: Any, *, email: Optional[str], user_id: Optional[str]
) -> Dict[str, Any]:
    normalized_email, normalized_user_id = _normalize_user_lookup_params(
        email, user_id
    )

    if normalized_email:
        user_info = await service.find_user_by_email(normalized_email)
        if not user_info:
            raise HTTPException(
                status_code=404,
                detail=f"User with email {normalized_email} not found",
            )
        return user_info

    user_info = await service.find_user_by_id(normalized_user_id)
    if not user_info:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {normalized_user_id} not found",
        )
    return user_info


@router.get(
    "/user-analytics/new-users",
    response_model=List[DailyNewUsersResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_new_users(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    register_start_date: Optional[str] = Query(
        None, description="注册开始日期 (YYYY-MM-DD)"
    ),
    register_end_date: Optional[str] = Query(
        None, description="注册结束日期 (YYYY-MM-DD)"
    ),
    register_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="注册最近N天"
    ),
) -> Any:
    """获取用户注册统计（按注册日期范围）"""
    try:
        from app.services.user_analytics_service import UserAnalyticsService

        reg_start, reg_end, _, _ = _parse_analytics_date_ranges(
            register_start_date,
            register_end_date,
            register_last_days,
            None,
            None,
            None,
        )

        service = UserAnalyticsService(db)
        data = await service.get_new_users(reg_start, reg_end)
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取用户统计失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch user statistics"
        )


@router.get(
    "/user-analytics/user-activity",
    response_model=List[UserChatActivityItem],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_user_activity(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    register_start_date: Optional[str] = Query(
        None, description="注册开始日期 (YYYY-MM-DD)"
    ),
    register_end_date: Optional[str] = Query(
        None, description="注册结束日期 (YYYY-MM-DD)"
    ),
    register_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="注册最近N天"
    ),
) -> Any:
    """获取用户聊天活动原始数据（按注册日期范围筛选用户）"""
    try:
        from app.services.user_analytics_service import UserAnalyticsService

        reg_start, reg_end, _, _ = _parse_analytics_date_ranges(
            register_start_date,
            register_end_date,
            register_last_days,
            None,
            None,
            None,
        )

        service = UserAnalyticsService(db)
        data = await service.get_user_chat_activity(reg_start, reg_end)
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取用户活动失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch user activity"
        )


@router.get(
    "/user-analytics/conversation-rounds",
    response_model=List[ConversationRoundsResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_conversation_rounds(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    register_start_date: Optional[str] = Query(
        None, description="注册开始日期 (YYYY-MM-DD)"
    ),
    register_end_date: Optional[str] = Query(
        None, description="注册结束日期 (YYYY-MM-DD)"
    ),
    register_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="注册最近N天"
    ),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
) -> Any:
    """获取对话轮数分布（按Session）"""
    try:
        from app.services.user_analytics_service import UserAnalyticsService

        reg_start, reg_end, act_start, act_end = _parse_analytics_date_ranges(
            register_start_date,
            register_end_date,
            register_last_days,
            activity_start_date,
            activity_end_date,
            activity_last_days,
        )

        service = UserAnalyticsService(db)
        data = await service.get_conversation_rounds(
            reg_start, reg_end, act_start, act_end
        )
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取对话轮数失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch conversation turns"
        )


@router.get(
    "/user-analytics/user-rounds-distribution",
    response_model=List[UserRoundsDistributionItem],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_user_rounds_distribution(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    register_start_date: Optional[str] = Query(
        None, description="注册开始日期 (YYYY-MM-DD)"
    ),
    register_end_date: Optional[str] = Query(
        None, description="注册结束日期 (YYYY-MM-DD)"
    ),
    register_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="注册最近N天"
    ),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
) -> Any:
    """获取对话轮数分布（按用户）"""
    try:
        from app.services.user_analytics_service import UserAnalyticsService

        reg_start, reg_end, act_start, act_end = _parse_analytics_date_ranges(
            register_start_date,
            register_end_date,
            register_last_days,
            activity_start_date,
            activity_end_date,
            activity_last_days,
        )

        service = UserAnalyticsService(db)
        data = await service.get_user_rounds_distribution(
            reg_start, reg_end, act_start, act_end
        )
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取用户轮数分布失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch user turn distribution"
        )


@router.get(
    "/user-analytics/popular-agents",
    response_model=List[PopularAgentsResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_popular_agents(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    register_start_date: Optional[str] = Query(
        None, description="注册开始日期 (YYYY-MM-DD)"
    ),
    register_end_date: Optional[str] = Query(
        None, description="注册结束日期 (YYYY-MM-DD)"
    ),
    register_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="注册最近N天"
    ),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
) -> Any:
    """获取热门角色排行"""
    try:
        from app.services.user_analytics_service import UserAnalyticsService

        reg_start, reg_end, act_start, act_end = _parse_analytics_date_ranges(
            register_start_date,
            register_end_date,
            register_last_days,
            activity_start_date,
            activity_end_date,
            activity_last_days,
        )

        service = UserAnalyticsService(db)
        return await service.get_popular_agents(
            reg_start, reg_end, act_start, act_end, limit=20
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取热门角色失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch popular agents"
        )


@router.get(
    "/user-analytics/users-hitting-limit",
    response_model=List[UsersHittingLimitResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_users_hitting_limit(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
) -> Any:
    """获取达到聊天限制的用户（使用活跃日期范围）"""
    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        now = datetime.now(timezone.utc)

        if activity_last_days:
            act_end = now
            act_start = now - timedelta(days=activity_last_days)
        elif activity_start_date and activity_end_date:
            act_start = datetime.strptime(
                activity_start_date, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
            act_end = datetime.strptime(activity_end_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ) + timedelta(days=1)
        else:
            # 当没有提供活跃日期范围时，默认查询全部数据
            act_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
            act_end = now

        service = UserAnalyticsService(db)
        data = await service.get_users_hitting_chat_limit(act_start, act_end)
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取达到限制的用户失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch users who hit limits"
        )


@router.get(
    "/user-analytics/agent-analytics",
    response_model=List[AgentAnalyticsResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_agent_analytics(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    register_start_date: Optional[str] = Query(
        None, description="注册开始日期 (YYYY-MM-DD)"
    ),
    register_end_date: Optional[str] = Query(
        None, description="注册结束日期 (YYYY-MM-DD)"
    ),
    register_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="注册最近N天"
    ),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
) -> Any:
    """获取角色数据分析"""
    try:
        from app.services.user_analytics_service import UserAnalyticsService

        reg_start, reg_end, act_start, act_end = _parse_analytics_date_ranges(
            register_start_date,
            register_end_date,
            register_last_days,
            activity_start_date,
            activity_end_date,
            activity_last_days,
        )

        service = UserAnalyticsService(db)
        data = await service.get_agent_analytics(
            reg_start, reg_end, act_start, act_end
        )
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取角色分析失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch agent analysis"
        )


@router.get(
    "/user-analytics/user-sessions-detail",
    response_model=List[UserSessionsDetailResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_user_sessions_detail(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    register_start_date: Optional[str] = Query(
        None, description="注册开始日期 (YYYY-MM-DD)"
    ),
    register_end_date: Optional[str] = Query(
        None, description="注册结束日期 (YYYY-MM-DD)"
    ),
    register_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="注册最近N天"
    ),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
) -> Any:
    """获取用户会话详情"""
    try:
        from app.services.user_analytics_service import UserAnalyticsService

        reg_start, reg_end, act_start, act_end = _parse_analytics_date_ranges(
            register_start_date,
            register_end_date,
            register_last_days,
            activity_start_date,
            activity_end_date,
            activity_last_days,
        )

        service = UserAnalyticsService(db)
        data = await service.get_user_sessions_detail(
            reg_start, reg_end, act_start, act_end
        )
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取用户会话详情失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch user session details"
        )


@router.get(
    "/user-analytics/conversations-detail",
    response_model=List[ConversationsDetailResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_conversations_detail(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    register_start_date: Optional[str] = Query(
        None, description="注册开始日期 (YYYY-MM-DD)"
    ),
    register_end_date: Optional[str] = Query(
        None, description="注册结束日期 (YYYY-MM-DD)"
    ),
    register_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="注册最近N天"
    ),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
) -> Any:
    """获取对话详情（包含消息内容）"""
    try:
        from collections import defaultdict

        from app.services.user_analytics_service import UserAnalyticsService

        reg_start, reg_end, act_start, act_end = _parse_analytics_date_ranges(
            register_start_date,
            register_end_date,
            register_last_days,
            activity_start_date,
            activity_end_date,
            activity_last_days,
        )

        service = UserAnalyticsService(db)
        sessions_detail = await service.get_user_sessions_detail(
            reg_start, reg_end, act_start, act_end
        )

        if not sessions_detail:
            return []

        chat_ids = [item["chat_id"] for item in sessions_detail]
        messages = await service.get_chat_messages(chat_ids)

        chat_to_messages = defaultdict(list)
        for msg in messages:
            chat_to_messages[msg["chat_id"]].append(msg)

        user_to_sessions = defaultdict(list)
        for item in sessions_detail:
            user_id = item["user_id"]
            session_data = {
                "chat_id": item["chat_id"],
                "agent_name": item["agent_name"],
                "message_count": item["message_count"],
                "voice_message_count": item["voice_message_count"],
                "messages": chat_to_messages.get(item["chat_id"], []),
            }
            user_to_sessions[user_id].append(session_data)

        result = []
        for user_id, sessions in user_to_sessions.items():
            first_item = sessions_detail[
                next(
                    i
                    for i, item in enumerate(sessions_detail)
                    if item["user_id"] == user_id
                )
            ]
            result.append(
                {
                    "user_id": user_id,
                    "auth_type": first_item["auth_type"],
                    "user_created_at": first_item["user_created_at"],
                    "nickname": first_item["nickname"],
                    "email": first_item["email"],
                    "sessions": sessions,
                }
            )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取对话详情失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch conversation details"
        )


@router.get(
    "/user-analytics/conversations-detail/user-agent-paginated",
    response_model=PaginatedUserAgentConversationsResponse,
)
async def get_user_agent_conversations_detail_paginated(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    register_start_date: Optional[str] = Query(
        None, description="注册开始日期 (YYYY-MM-DD)"
    ),
    register_end_date: Optional[str] = Query(
        None, description="注册结束日期 (YYYY-MM-DD)"
    ),
    register_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="注册最近N天"
    ),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页分组数量"),
) -> Any:
    """按 user_id + agent_id 分组，分页返回查询范围内聊天详情"""
    try:
        from app.services.user_analytics_service import UserAnalyticsService

        reg_start, reg_end, act_start, act_end = _parse_analytics_date_ranges(
            register_start_date,
            register_end_date,
            register_last_days,
            activity_start_date,
            activity_end_date,
            activity_last_days,
        )

        service = UserAnalyticsService(db)
        result = await service.get_paginated_user_agent_conversations_detail(
            reg_start,
            reg_end,
            act_start,
            act_end,
            page,
            size,
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分页对话详情失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch paginated conversation details",
        )


@router.get(
    "/user-analytics/stats",
    response_model=UserAnalyticsStatsResponse,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_user_analytics_stats(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    register_start_date: Optional[str] = Query(
        None, description="注册开始日期 (YYYY-MM-DD)"
    ),
    register_end_date: Optional[str] = Query(
        None, description="注册结束日期 (YYYY-MM-DD)"
    ),
    register_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="注册最近N天"
    ),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
) -> Any:
    """获取用户数据分析统计概览"""
    try:
        from app.services.user_analytics_service import UserAnalyticsService

        reg_start, reg_end, act_start, act_end = _parse_analytics_date_ranges(
            register_start_date,
            register_end_date,
            register_last_days,
            activity_start_date,
            activity_end_date,
            activity_last_days,
        )

        service = UserAnalyticsService(db)
        data = await service.get_analytics_stats(
            reg_start, reg_end, act_start, act_end
        )
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取统计数据失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch statistics"
        )


@router.get(
    "/user-analytics/reports",
    response_model=UserAnalyticsReportsResponse,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_user_analytics_reports(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    report_type: Optional[str] = Query(
        None, description="daily | weekly，不传则返回全部"
    ),
    limit: int = Query(30, ge=1, le=100, description="返回条数"),
    include_charts: bool = Query(True, description="是否返回图表数据"),
) -> Any:
    """获取用户数据分析预计算报告列表（日报/周报）"""
    try:
        from sqlalchemy import desc, select

        from app.models.user_analytics_report import UserAnalyticsReport

        def _safe_to_int(value: Any) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        def _normalize_daily_top_agent(
            item: Dict[str, Any],
            rank: int,
        ) -> Optional[Dict[str, Any]]:
            agent_name = item.get("agent_name")
            if not isinstance(agent_name, str) or not agent_name:
                return None
            normalized_rank = _safe_to_int(item.get("rank"))
            return {
                "rank": normalized_rank if normalized_rank > 0 else rank,
                "agent_name": agent_name,
                "total_rounds": _safe_to_int(item.get("total_rounds")),
                "user_count": _safe_to_int(item.get("user_count")),
                "total_sessions": _safe_to_int(item.get("total_sessions")),
                "active_sessions": _safe_to_int(item.get("active_sessions")),
            }

        def _build_daily_top_agents_by_rounds(
            charts: Any,
        ) -> List[Dict[str, Any]]:
            if not isinstance(charts, dict):
                return []

            raw_top_agents = charts.get("daily_top_agents_by_rounds")
            if isinstance(raw_top_agents, list) and raw_top_agents:
                normalized_from_daily: List[Dict[str, Any]] = []
                for index, item in enumerate(raw_top_agents, start=1):
                    if not isinstance(item, dict):
                        continue
                    normalized_item = _normalize_daily_top_agent(item, index)
                    if normalized_item is None:
                        continue
                    normalized_from_daily.append(normalized_item)
                normalized_from_daily.sort(key=lambda item: item["rank"])
                return normalized_from_daily[:10]

            raw_popular_agents = charts.get("popular_agents")
            if not isinstance(raw_popular_agents, list):
                return []
            popular_agents = [
                item
                for item in raw_popular_agents
                if isinstance(item, dict) and item.get("agent_name")
            ]
            sorted_by_rounds = sorted(
                popular_agents,
                key=lambda item: (
                    _safe_to_int(item.get("total_rounds")),
                    _safe_to_int(item.get("user_count")),
                ),
                reverse=True,
            )
            fallback_top_agents: List[Dict[str, Any]] = []
            for rank, item in enumerate(sorted_by_rounds[:10], start=1):
                normalized_item = _normalize_daily_top_agent(item, rank)
                if normalized_item is None:
                    continue
                fallback_top_agents.append(normalized_item)
            return fallback_top_agents

        def _build_daily_most_discussed_agent(
            charts: Any,
            daily_top_agents_by_rounds: List[Dict[str, Any]],
        ) -> Optional[Dict[str, Any]]:
            if isinstance(charts, dict):
                raw_most_discussed = charts.get("daily_most_discussed_agent")
                if isinstance(raw_most_discussed, dict):
                    normalized_item = _normalize_daily_top_agent(
                        raw_most_discussed, 1
                    )
                    if normalized_item is not None:
                        return normalized_item
            if daily_top_agents_by_rounds:
                return daily_top_agents_by_rounds[0]
            return None

        stmt = (
            select(UserAnalyticsReport)
            .order_by(desc(UserAnalyticsReport.report_date))
            .limit(limit)
        )
        if report_type in ("daily", "weekly"):
            stmt = stmt.where(UserAnalyticsReport.report_type == report_type)

        result = await db.execute(stmt)
        rows = result.scalars().all()

        reports = []
        for row in rows:
            daily_top_agents_by_rounds = _build_daily_top_agents_by_rounds(
                row.charts
            )
            daily_most_discussed_agent = _build_daily_most_discussed_agent(
                row.charts, daily_top_agents_by_rounds
            )
            charts_data = None
            if include_charts and row.charts:
                charts_data = UserAnalyticsReportCharts(
                    new_users=row.charts.get("new_users", []),
                    conversation_rounds=row.charts.get(
                        "conversation_rounds", []
                    ),
                    user_rounds_distribution=row.charts.get(
                        "user_rounds_distribution", []
                    ),
                    users_hitting_limit=row.charts.get(
                        "users_hitting_limit", []
                    ),
                    popular_agents=row.charts.get("popular_agents", []),
                    generated_images=row.charts.get("generated_images", []),
                    daily_top_agents_by_rounds=daily_top_agents_by_rounds,
                    daily_most_discussed_agent=daily_most_discussed_agent,
                )
            reports.append(
                UserAnalyticsReportItem(
                    id=row.id,
                    report_type=row.report_type,
                    report_date=row.report_date.isoformat(),
                    stats=row.stats,
                    daily_top_agents_by_rounds=daily_top_agents_by_rounds,
                    daily_most_discussed_agent=daily_most_discussed_agent,
                    charts=charts_data,
                    created_at=(
                        row.created_at.isoformat() if row.created_at else None
                    ),
                )
            )

        return UserAnalyticsReportsResponse(reports=reports)

    except Exception as e:
        logger.error(f"获取预计算报告失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch precomputed reports"
        )


@router.get(
    "/user-analytics/daily-voice-audios",
    response_model=DailyVoiceAudiosResponse,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_daily_voice_audios(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    report_date: str = Query(..., description="日报日期 (YYYY-MM-DD)"),
) -> Any:
    """获取指定日期的语音播报与语音通话录音，按用户-角色分组"""
    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        act_start = datetime.strptime(report_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        act_end = act_start + timedelta(days=1)
        service = UserAnalyticsService(db)
        voice_message_groups, voice_call_groups = (
            await service.get_voice_audios_on_date(act_start, act_end)
        )

        def to_group(g: Dict[str, Any]) -> VoiceAudioGroupByUserAgent:
            return VoiceAudioGroupByUserAgent(
                user_id=g["user_id"],
                agent_id=g["agent_id"],
                agent_name=g.get("agent_name") or "",
                audios=[
                    VoiceAudioItem(
                        audio_url=a["audio_url"],
                        message_id=a["message_id"],
                        created_at=a.get("created_at"),
                        duration_seconds=a.get("duration_seconds"),
                    )
                    for a in g.get("audios") or []
                ],
            )

        return DailyVoiceAudiosResponse(
            voice_message_audios=[to_group(g) for g in voice_message_groups],
            voice_call_audios=[to_group(g) for g in voice_call_groups],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取日报语音录音失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch daily voice audios"
        )


@router.get(
    "/user-analytics/llm-latency",
    response_model=LLMLatencyResponse,
    tags=[INTY_EVAL_TAG],
)
async def get_llm_latency_trend(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
) -> Any:
    """获取 LLM 调用延迟趋势（按小时聚合）"""
    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        now = datetime.now(timezone.utc)

        # 直接解析活跃日期范围（不依赖 register 参数）
        if activity_last_days:
            act_end = now
            act_start = now - timedelta(days=activity_last_days)
        elif activity_start_date and activity_end_date:
            act_start = datetime.strptime(
                activity_start_date, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
            act_end = datetime.strptime(activity_end_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ) + timedelta(days=1)
        else:
            # 当没有提供活跃日期范围时，默认查询全部数据
            act_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
            act_end = now

        service = UserAnalyticsService(db)
        data = await service.get_llm_latency_trend(act_start, act_end)
        return {"data": data}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取 LLM 延迟趋势失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch LLM latency trend"
        )


@router.get(
    "/user-analytics/image-generation-latency",
    response_model=ImageGenerationLatencyResponse,
    tags=[INTY_EVAL_TAG],
)
async def get_image_generation_latency_trend(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
) -> Any:
    """获取生图耗时趋势（按小时和模型聚合）"""
    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        now = datetime.now(timezone.utc)

        # 直接解析活跃日期范围
        if activity_last_days:
            act_end = now
            act_start = now - timedelta(days=activity_last_days)
        elif activity_start_date and activity_end_date:
            act_start = datetime.strptime(
                activity_start_date, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
            act_end = datetime.strptime(activity_end_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ) + timedelta(days=1)
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide activity_start_date/activity_end_date or activity_last_days",
            )

        service = UserAnalyticsService(db)
        data = await service.get_image_generation_latency_trend(
            act_start, act_end
        )
        return {"data": data}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取生图耗时趋势失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch image generation duration trend",
        )


@router.get(
    "/user-analytics/image-generation-failures",
    response_model=ImageGenerationFailureAnalyticsResponse,
)
async def get_image_generation_failure_analytics(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
    top_n_reasons: int = Query(20, ge=1, le=100, description="失败原因 Top N"),
) -> Any:
    """获取生图失败与兜底分析（只读 replica：失败类型、失败原因、兜底占比、按 Agent、按日趋势）"""
    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        now = datetime.now(timezone.utc)
        if activity_last_days:
            act_end = now
            act_start = now - timedelta(days=activity_last_days)
        elif activity_start_date and activity_end_date:
            act_start = datetime.strptime(
                activity_start_date, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
            act_end = datetime.strptime(activity_end_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ) + timedelta(days=1)
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide activity_start_date/activity_end_date or activity_last_days",
            )

        service = UserAnalyticsService(db)
        data = await service.get_image_generation_failure_analytics(
            act_start, act_end, top_n_reasons=top_n_reasons
        )
        return {"data": data}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取生图失败分析失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch image generation failure analytics",
        )


@router.get(
    "/user-analytics/live-chat-latency",
    response_model=LiveChatLatencyResponse,
)
async def get_live_chat_latency_trend(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
) -> Any:
    """获取 Live Chat 延迟趋势（按小时聚合）"""
    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        now = datetime.now(timezone.utc)

        # 解析活跃日期范围
        if activity_last_days:
            act_end = now
            act_start = now - timedelta(days=activity_last_days)
        elif activity_start_date and activity_end_date:
            act_start = datetime.strptime(
                activity_start_date, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
            act_end = datetime.strptime(activity_end_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ) + timedelta(days=1)
        else:
            # 默认查询最近7天
            act_end = now
            act_start = now - timedelta(days=7)

        service = UserAnalyticsService(db)
        data = await service.get_live_chat_latency_trend(act_start, act_end)
        return {"data": data}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取 Live Chat 延迟趋势失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch Live Chat latency trend"
        )


@router.get(
    "/user-analytics/live-chat-stats",
    response_model=LiveChatBasicStatsResponse,
)
async def get_live_chat_basic_stats(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    activity_start_date: Optional[str] = Query(
        None, description="活跃开始日期 (YYYY-MM-DD)"
    ),
    activity_end_date: Optional[str] = Query(
        None, description="活跃结束日期 (YYYY-MM-DD)"
    ),
    activity_last_days: Optional[int] = Query(
        None, ge=1, le=365, description="活跃最近N天"
    ),
) -> Any:
    """获取 Live Chat 基础统计"""
    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        now = datetime.now(timezone.utc)

        # 解析活跃日期范围
        if activity_last_days:
            act_end = now
            act_start = now - timedelta(days=activity_last_days)
        elif activity_start_date and activity_end_date:
            act_start = datetime.strptime(
                activity_start_date, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
            act_end = datetime.strptime(activity_end_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ) + timedelta(days=1)
        else:
            # 默认查询最近7天
            act_end = now
            act_start = now - timedelta(days=7)

        service = UserAnalyticsService(db)
        stats = await service.get_live_chat_basic_stats(act_start, act_end)
        return stats

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取 Live Chat 基础统计失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch Live Chat base statistics"
        )


@router.get(
    "/user-analytics/user-daily-messages",
    response_model=UserDailyMessagesResponse,
)
async def get_user_daily_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    email: Optional[str] = Query(None, description="用户邮箱"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    start_date: Optional[str] = Query(
        None, description="开始日期 (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
) -> Any:
    """获取用户每日消息统计"""
    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        service = UserAnalyticsService(db)
        normalized_email, normalized_user_id = _normalize_user_lookup_params(
            email, user_id, allow_empty=True
        )

        # 解析日期范围
        start_date_obj = None
        end_date_obj = None
        if start_date:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        if end_date:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            # 包含结束日期的全天
            end_date_obj = end_date_obj.replace(
                hour=23, minute=59, second=59
            ) + timedelta(seconds=1)

        # 日期范围模式：未提供用户标识时，按全量用户查询
        if not normalized_email and not normalized_user_id:
            if not start_date_obj or not end_date_obj:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Provide start_date and end_date when email and user_id "
                        "are omitted"
                    ),
                )
            daily_messages = await service.get_daily_messages_for_all_users(
                start_date_obj, end_date_obj
            )
            return {
                "user_id": "ALL_USERS",
                "email": None,
                "nickname": "全部用户",
                "auth_type": "ALL_USERS",
                "created_at": None,
                "gender": None,
                "age_group": None,
                "daily_messages": daily_messages,
            }

        # 查找用户
        user_info = await _find_user_info_by_identifier(
            service, email=normalized_email, user_id=normalized_user_id
        )

        # 获取单用户每日消息统计
        daily_messages = await service.get_user_daily_messages(
            user_info["id"], start_date_obj, end_date_obj
        )

        return {
            "user_id": user_info["id"],
            "email": user_info["email"],
            "nickname": user_info.get("nickname"),
            "auth_type": user_info["auth_type"],
            "created_at": user_info.get("created_at"),
            "gender": user_info.get("gender"),
            "age_group": user_info.get("age_group"),
            "daily_messages": daily_messages,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户每日消息统计失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch daily user message stats"
        )


@router.get(
    "/user-analytics/user-today-stats",
    response_model=UserTodayStatsResponse,
)
async def get_user_today_stats(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    email: Optional[str] = Query(None, description="用户邮箱"),
    user_id: Optional[str] = Query(None, description="用户ID"),
) -> Any:
    """获取用户当日统计"""
    try:
        from app.services.user_analytics_service import UserAnalyticsService

        service = UserAnalyticsService(db)

        # 查找用户
        user_info = await _find_user_info_by_identifier(
            service, email=email, user_id=user_id
        )

        # 获取当日统计
        today_stats = await service.get_user_today_stats(user_info["id"])

        return today_stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户当日统计失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch today's user stats"
        )


@router.get(
    "/user-analytics/user-generated-images",
    response_model=UserGeneratedImagesResponse,
)
async def get_user_generated_images(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    email: Optional[str] = Query(None, description="用户邮箱"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(50, ge=1, le=200, description="返回的记录数"),
) -> Any:
    """
    获取指定用户的所有聊天生成图片

    从 resources 表查询带有 generation_prompt 的图片资源
    """
    try:
        from sqlalchemy import select

        from app.models.resource import Resource, ResourceType
        from app.services.image_transform_service import image_transform_service
        from app.services.user_analytics_service import UserAnalyticsService

        service = UserAnalyticsService(db)

        # 查找用户
        user_info = await _find_user_info_by_identifier(
            service, email=email, user_id=user_id
        )

        # 查询指定用户的生成图片
        query = (
            select(Resource)
            .where(
                Resource.user_id == user_info["id"],
                Resource.type == ResourceType.IMAGE,
                Resource.resource_metadata.isnot(None),
            )
            .order_by(Resource.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        resources = result.scalars().all()

        # 收集所有 agent_id 并查询角色信息
        from app.models.agent import Agent

        agent_ids = list(set(r.agent_id for r in resources if r.agent_id))
        agent_info_map: dict[str, dict] = {}
        if agent_ids:
            agent_query = select(Agent.id, Agent.name).where(
                Agent.id.in_(agent_ids)
            )
            agent_result = await db.execute(agent_query)
            for row in agent_result.all():
                agent_info_map[row.id] = {
                    "name": row.name,
                }

        # 构建返回数据
        images = []
        for resource in resources:
            metadata = resource.resource_metadata or {}
            generation_prompt = metadata.get("generation_prompt")

            # 只返回有 generation_prompt 的图片
            if not generation_prompt:
                continue

            size = metadata.get("size", {})
            try:
                cdn_url = image_transform_service.transform_desktop(
                    resource.url
                )
            except Exception as e:
                logger.warning(
                    f"转换图片URL失败: {resource.url}, 错误: {str(e)}"
                )
                cdn_url = resource.url  # 使用原始URL作为fallback
            reference_image_url = metadata.get("reference_image_url")

            agent_info = agent_info_map.get(resource.agent_id, {})
            images.append(
                {
                    "url": cdn_url,
                    "gcs_url": resource.url,
                    "generation_prompt": generation_prompt,
                    "reference_image_url": reference_image_url,
                    "width": size.get("width"),
                    "height": size.get("height"),
                    "created_at": (
                        resource.created_at.isoformat()
                        if resource.created_at
                        else None
                    ),
                    "agent_id": resource.agent_id,
                    "agent_name": agent_info.get("name"),
                }
            )

        # 获取总数
        count_query = select(Resource).where(
            Resource.user_id == user_info["id"],
            Resource.type == ResourceType.IMAGE,
            Resource.resource_metadata.isnot(None),
        )
        count_result = await db.execute(count_query)
        all_resources = count_result.scalars().all()
        total = 0
        for resource in all_resources:
            metadata = resource.resource_metadata or {}
            if metadata.get("generation_prompt"):
                total += 1

        logger.debug(
            f"获取用户 {user_info['id']} 的生成图片，共 {len(images)} 张"
        )
        return {"images": images, "total": total}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户生成图片失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch user generated images"
        )


@router.get(
    "/user-analytics/user-sessions",
    response_model=UserSessionsResponse,
)
async def get_user_sessions(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    email: Optional[str] = Query(None, description="用户邮箱"),
    user_id: Optional[str] = Query(None, description="用户ID"),
) -> Any:
    """获取用户的所有会话列表"""
    try:
        from app.services.user_analytics_service import UserAnalyticsService

        service = UserAnalyticsService(db)

        # 查找用户
        user_info = await _find_user_info_by_identifier(
            service, email=email, user_id=user_id
        )

        # 获取会话列表
        sessions = await service.get_user_sessions(user_info["id"])

        return {"sessions": sessions}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户会话列表失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch user sessions"
        )


@router.get(
    "/user-analytics/session-messages",
    response_model=SessionMessagesResponse,
)
async def get_session_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_replica_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    chat_id: str = Query(..., description="会话ID (chat_id)"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(50, ge=1, le=200, description="每页数量"),
) -> Any:
    """获取指定会话的对话历史"""
    try:
        from app.services.user_analytics_service import UserAnalyticsService

        service = UserAnalyticsService(db)

        # 获取会话消息
        result = await service.get_session_messages(chat_id, page, size)

        return result

    except Exception as e:
        logger.error(f"获取会话消息失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch session messages"
        )


# =============================================================================
# 生成图片管理API
# =============================================================================


@router.get(
    "/agents/generated-images/counts",
)
async def get_all_agents_image_counts(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    """
    获取所有角色的生成图片数量

    返回格式: {"agent_id_1": 5, "agent_id_2": 10, ...}
    """
    try:
        from sqlalchemy import func, select

        from app.models.resource import Resource, ResourceType

        # 使用 GROUP BY 统计每个角色的图片数量
        query = (
            select(Resource.agent_id, func.count(Resource.url).label("count"))
            .where(
                Resource.type == ResourceType.IMAGE,
                Resource.resource_metadata.isnot(None),
                Resource.agent_id.isnot(None),
            )
            .group_by(Resource.agent_id)
        )

        result = await db.execute(query)
        rows = result.all()

        # 构建返回数据
        counts = {row.agent_id: row.count for row in rows}

        logger.debug(f"获取所有角色图片数量，共 {len(counts)} 个角色有图片")
        return {"counts": counts}

    except Exception as e:
        logger.error(f"获取角色图片数量失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch agent image counts"
        )


@router.get(
    "/agents/{agent_id}/generated-images",
    tags=[INTY_EVAL_TAG],
)
async def get_agent_generated_images(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
    agent_id: str,
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(50, ge=1, le=200, description="返回的记录数"),
) -> Any:
    """
    获取指定角色的所有聊天生成图片

    从 resources 表查询带有 generation_prompt 的图片资源
    """
    try:
        from sqlalchemy import select

        from app.models.resource import Resource, ResourceType
        from app.services.image_transform_service import image_transform_service

        # 查询指定 agent 的生成图片
        query = (
            select(Resource)
            .where(
                Resource.agent_id == agent_id,
                Resource.type == ResourceType.IMAGE,
                Resource.resource_metadata.isnot(None),
            )
            .order_by(Resource.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        resources = result.scalars().all()

        # 收集所有 user_id 并查询用户信息
        from app.models.user import User

        user_ids = list(set(r.user_id for r in resources if r.user_id))
        user_info_map: dict[str, dict] = {}
        if user_ids:
            user_query = select(
                User.id, User.nickname, User.email, User.user_photo
            ).where(User.id.in_(user_ids))
            user_result = await db.execute(user_query)
            for row in user_result.all():
                user_info_map[row.id] = {
                    "nickname": row.nickname,
                    "email": row.email,
                    "user_photo": row.user_photo,
                }

        # 构建返回数据
        images = []
        for resource in resources:
            metadata = resource.resource_metadata or {}
            generation_prompt = metadata.get("generation_prompt")

            # 只返回有 generation_prompt 的图片
            if not generation_prompt:
                continue

            size = metadata.get("size", {})
            cdn_url = image_transform_service.transform_desktop(resource.url)
            reference_image_url = metadata.get("reference_image_url")
            user_reference_image_url = metadata.get("user_reference_image_url")
            reference_image_urls = metadata.get("reference_image_urls")
            generated_image_meta = metadata.get("generated_image")
            model = None
            generation_time_ms = None
            model_fallback_due_to_429 = None
            langsmith_trace_id = metadata.get("langsmith_trace_id")
            langsmith_trace_url = metadata.get("langsmith_trace_url")
            if isinstance(generated_image_meta, dict):
                model = generated_image_meta.get("model")
                generation_time_ms = generated_image_meta.get(
                    "generation_time_ms"
                )
                model_fallback_due_to_429 = generated_image_meta.get(
                    "model_fallback_due_to_429"
                )
                if reference_image_url is None:
                    reference_image_url = generated_image_meta.get(
                        "reference_image_url"
                    )
                if user_reference_image_url is None:
                    user_reference_image_url = generated_image_meta.get(
                        "user_reference_image_url"
                    )
                if reference_image_urls is None:
                    reference_image_urls = generated_image_meta.get(
                        "reference_image_urls"
                    )
            if model is None:
                model = metadata.get("model")

            user_info = user_info_map.get(resource.user_id, {})
            images.append(
                {
                    "url": cdn_url,
                    "gcs_url": resource.url,
                    "generation_prompt": generation_prompt,
                    "reference_image_url": reference_image_url,
                    "user_reference_image_url": user_reference_image_url,
                    "reference_image_urls": reference_image_urls,
                    "width": size.get("width"),
                    "height": size.get("height"),
                    "created_at": (
                        resource.created_at.isoformat()
                        if resource.created_at
                        else None
                    ),
                    "user_id": resource.user_id,
                    "user_nickname": user_info.get("nickname"),
                    "user_email": user_info.get("email"),
                    "user_photo": user_info.get("user_photo"),
                    "model": model,
                    "generation_time_ms": generation_time_ms,
                    "model_fallback_due_to_429": model_fallback_due_to_429,
                    "langsmith_trace_id": langsmith_trace_id,
                    "langsmith_trace_url": langsmith_trace_url,
                    "session_id": metadata.get("session_id"),
                    "meta_data": metadata,
                }
            )

        logger.debug(f"获取角色 {agent_id} 的生成图片，共 {len(images)} 张")
        return {"images": images, "total": len(images)}

    except Exception as e:
        logger.error(f"获取角色生成图片失败: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch agent generated images"
        )
