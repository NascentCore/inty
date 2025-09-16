"""评测系统API端点 - 专门用于评测聊天系统效果"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.schemas.response import APIResponse, PaginationData
from app.services.evaluation_service import EvaluationService
from app.services.question_parser_service import QuestionParserService
from app.services.scoring_service import ScoringService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", route_class=LoggerRoute)


@router.get(
    "/sessions",
    response_model=APIResponse[PaginationData[schemas.EvaluationSessionResponse]],
)
async def get_evaluation_sessions(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=1000, description="每页数量"),
    status: Optional[str] = Query(None, description="按状态过滤"),
) -> Any:
    """
    获取评测会话列表

    返回当前用户创建的评测会话列表
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        evaluation_service = EvaluationService(db)

        # 计算skip和limit
        skip = (page - 1) * page_size

        sessions = await evaluation_service.get_user_sessions(
            user_id=current_user.id, skip=skip, limit=page_size, status=status
        )

        # 当前获取的数量，如果少于page_size说明是最后一页
        current_count = len(sessions)
        # 估算总数 - 实际项目中应该有专门的count方法
        total = skip + current_count
        if current_count == page_size:
            # 可能还有更多数据，这里用估算
            total = skip + current_count + 1
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1

        # 创建分页数据
        pagination_data = PaginationData[schemas.EvaluationSessionResponse](
            list=sessions,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
        return APIResponse.success(data=pagination_data)

    except Exception as e:
        logger.error(f"获取评测会话列表失败: {str(e)}")
        return APIResponse.error(message="获取评测会话列表失败")


@router.post("/sessions", response_model=APIResponse[schemas.EvaluationSessionResponse])
async def create_evaluation_session(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    session_in: schemas.EvaluationSessionCreate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建评测会话

    用于评测当前聊天系统的智能体对话效果
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

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
        return APIResponse.success(data=session)

    except ValueError as e:
        return APIResponse.error(message=str(e), code=400)
    except Exception as e:
        logger.error(f"创建评测会话失败: {str(e)}")
        return APIResponse.error(message="创建评测会话失败")


@router.post(
    "/sessions/{session_id}/start",
    response_model=APIResponse[schemas.SessionActionResponse],
)
async def start_evaluation_session(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    session_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    启动评测会话

    开始执行对智能体的批量测试和评分
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        evaluation_service = EvaluationService(db)

        # 验证会话所有权
        session = await evaluation_service.get_session(session_id)
        if not session:
            return APIResponse.error(message="评测会话不存在", code=404)

        if session.creator_id != current_user.id:
            return APIResponse.error(message="无权操作此评测会话", code=403)

        success = await evaluation_service.start_session(session_id)

        logger.info(f"用户 {current_user.id} 启动评测会话: {session_id}")
        response_data = schemas.SessionActionResponse(
            success=success, message="评测会话已启动"
        )
        return APIResponse.success(data=response_data)

    except ValueError as e:
        return APIResponse.error(message=str(e), code=400)
    except Exception as e:
        logger.error(f"启动评测会话失败: {str(e)}")
        return APIResponse.error(message="启动评测会话失败")


@router.get(
    "/sessions/{session_id}",
    response_model=APIResponse[schemas.EvaluationSessionDetail],
)
async def get_evaluation_session(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    session_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取评测会话详情

    包含完整的测试结果和交互记录
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        evaluation_service = EvaluationService(db)

        session = await evaluation_service.get_session(session_id)
        if not session:
            return APIResponse.error(message="评测会话不存在", code=404)

        if session.creator_id != current_user.id:
            return APIResponse.error(message="无权访问此评测会话", code=403)

        return APIResponse.success(data=session)

    except Exception as e:
        logger.error(f"获取评测会话详情失败: {str(e)}")
        return APIResponse.error(message="获取会话详情失败")


@router.get(
    "/sessions/{session_id}/results",
    response_model=APIResponse[List[schemas.EvaluationResultResponse]],
)
async def get_evaluation_results(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    session_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取评测结果

    返回指定会话的所有测试结果
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        evaluation_service = EvaluationService(db)

        # 验证权限
        session = await evaluation_service.get_session(session_id)
        if not session:
            return APIResponse.error(message="评测会话不存在", code=404)

        if session.creator_id != current_user.id:
            return APIResponse.error(message="无权访问此评测会话", code=403)

        results = await evaluation_service.get_session_results(session_id)
        return APIResponse.success(data=results)

    except Exception as e:
        logger.error(f"获取评测结果失败: {str(e)}")
        return APIResponse.error(message="获取评测结果失败")


@router.post(
    "/sessions/{session_id}/cancel",
    response_model=APIResponse[schemas.SessionActionResponse],
)
async def cancel_evaluation_session(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    session_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    取消评测会话

    停止正在进行的评测任务
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        evaluation_service = EvaluationService(db)

        # 验证权限
        session = await evaluation_service.get_session(session_id)
        if not session:
            return APIResponse.error(message="评测会话不存在", code=404)

        if session.creator_id != current_user.id:
            return APIResponse.error(message="无权操作此评测会话", code=403)

        success = await evaluation_service.cancel_session(session_id)

        logger.info(f"用户 {current_user.id} 取消评测会话: {session_id}")
        response_data = schemas.SessionActionResponse(
            success=success, message="评测会话已取消"
        )
        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"取消评测会话失败: {str(e)}")
        return APIResponse.error(message="取消评测会话失败")


@router.post(
    "/questions/parse", response_model=APIResponse[schemas.QuestionFileUploadResponse]
)
async def parse_questions_file(
    *,
    file: UploadFile = File(...),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    解析问题文件

    支持txt、csv、json格式的问题文件上传和解析
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        # 验证文件大小（最大10MB）
        if file.size and file.size > 10 * 1024 * 1024:
            return APIResponse.error(message="文件大小不能超过10MB", code=400)

        # 验证文件类型
        allowed_types = [".json"]
        if not any(file.filename.lower().endswith(ext) for ext in allowed_types):
            return APIResponse.error(
                message=f"不支持的文件类型，只支持: {', '.join(allowed_types)}",
                code=400,
            )

        questions = await QuestionParserService.parse_questions_file(file)

        # 验证问题质量
        validation = QuestionParserService.validate_questions(questions)

        logger.info(
            f"用户 {current_user.id} 上传问题文件: {file.filename}, 解析出 {len(questions)} 个问题"
        )

        response_data = schemas.QuestionFileUploadResponse(
            questions=questions,
            total_count=validation["stats"]["total"],
            valid_count=validation["stats"]["valid"],
            duplicates_removed=validation["stats"]["duplicates"],
            warnings=validation.get("warnings", []),
        )
        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"解析问题文件失败: {str(e)}")
        return APIResponse.error(message=f"文件解析失败: {str(e)}", code=400)


@router.get("/models", response_model=APIResponse[List[schemas.ScoringModelInfo]])
async def get_scoring_models(
    *,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取可用模型列表
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        scoring_service = ScoringService()
        models = await scoring_service.get_available_models()
        return APIResponse.success(data=models)

    except Exception as e:
        logger.error(f"获取评分模型失败: {str(e)}")
        return APIResponse.error(message="获取评分模型失败")


@router.post(
    "/scoring-criteria/validate",
    response_model=APIResponse[schemas.ScoringCriteriaValidationResponse],
)
async def validate_scoring_criteria(
    *,
    criteria: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    验证评分标准

    检查评分标准的格式和完整性
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        scoring_service = ScoringService()
        validation = scoring_service.validate_scoring_criteria(criteria)

        response_data = schemas.ScoringCriteriaValidationResponse(
            is_valid=validation.get("is_valid", False),
            errors=validation.get("errors", []),
            warnings=validation.get("warnings", []),
        )
        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"验证评分标准失败: {str(e)}")
        return APIResponse.error(message="验证评分标准失败")


@router.get("/stats", response_model=APIResponse[schemas.EvaluationStatsResponse])
async def get_evaluation_stats(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
) -> Any:
    """
    获取评测统计信息

    显示用户的评测历史和统计数据
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        # 这里可以实现统计逻辑，当前为mock实现
        # TODO: 使用db和days参数获取真实统计数据
        # 暂时返回模拟数据
        response_data = schemas.EvaluationStatsResponse(
            total_sessions=0,
            completed_sessions=0,
            running_sessions=0,
            failed_sessions=0,
            average_score=None,
            success_rate=None,
            total_tests=0,
            total_agents_tested=0,
        )
        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"获取评测统计失败: {str(e)}")
        return APIResponse.error(message="获取统计信息失败")


# WebSocket端点用于实时监控评测进度
@router.websocket("/sessions/{session_id}/monitor")
async def monitor_evaluation_session(
    websocket,
    session_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
):
    """
    实时监控评测会话进度

    通过WebSocket推送评测进度和结果
    """
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
            except Exception:
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


@router.get("/agents", response_model=APIResponse[PaginationData[schemas.Agent]])
async def get_evaluation_agents(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    type: str = Query("public", pattern="^(public|private)$", description="智能体类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=1000, description="每页数量"),
) -> Any:
    """
    获取用于评测的智能体列表

    支持获取公开和私有智能体，用于评测系统选择测试对象
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        from app.services import agent_service

        # 计算skip和limit
        skip = (page - 1) * page_size

        if type == "private":
            # 获取用户创建的私有智能体
            agents = await agent_service.get_user_agents(
                db,
                user_id=current_user.id,
                skip=skip,
                limit=page_size,
                current_user_id=current_user.id,
            )
        else:
            # 获取公开智能体
            agents = await agent_service.get_recommended_agents(
                db, skip=skip, limit=page_size, current_user_id=current_user.id
            )

        # 当前获取的数量，如果少于page_size说明是最后一页
        current_count = len(agents)
        # 估算总数 - 实际项目中应该有专门的count方法
        total = skip + current_count
        if current_count == page_size:
            # 可能还有更多数据，这里用估算
            total = skip + current_count + 1
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1

        # 创建分页数据
        pagination_data = PaginationData[schemas.Agent](
            list=agents,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

        logger.info(
            f"用户 {current_user.id} 获取评测智能体列表: {type}, 数量: {len(agents)}"
        )
        return APIResponse.success(data=pagination_data)

    except Exception as e:
        logger.error(f"获取智能体列表失败: {str(e)}")
        return APIResponse.error(message="获取智能体列表失败")


@router.post("/agents", response_model=APIResponse[schemas.Agent])
async def create_evaluation_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_in: schemas.AgentCreate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建用于评测的智能体

    在评测系统中创建新的智能体用于测试
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        from app.services import agent_service

        agent = await agent_service.create_agent(
            db=db, agent_in=agent_in, user_id=current_user.id
        )

        logger.info(f"用户 {current_user.id} 创建评测智能体: {agent.id}")
        return APIResponse.success(data=agent)

    except Exception as e:
        logger.error(f"创建智能体失败: {str(e)}")
        return APIResponse.error(message="创建智能体失败")


@router.put("/agents/{agent_id}", response_model=APIResponse[schemas.Agent])
async def update_evaluation_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    agent_in: schemas.AgentUpdate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新评测智能体

    修改智能体的配置和提示词等信息
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        from app.services import agent_service

        # 验证权限
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            return APIResponse.error(message="智能体不存在", code=404)

        if agent.creator_id != current_user.id:
            return APIResponse.error(message="无权修改此智能体", code=403)

        updated_agent = await agent_service.update_agent(
            db=db, db_agent=agent, agent_in=agent_in
        )

        logger.info(f"用户 {current_user.id} 更新智能体: {agent_id}")
        return APIResponse.success(data=updated_agent)

    except Exception as e:
        logger.error(f"更新智能体失败: {str(e)}")
        return APIResponse.error(message="更新智能体失败")


@router.delete(
    "/agents/{agent_id}", response_model=APIResponse[schemas.SessionActionResponse]
)
async def delete_evaluation_agent(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除评测智能体

    删除用户创建的私有智能体
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        from app.services import agent_service

        # 验证权限
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            return APIResponse.error(message="智能体不存在", code=404)

        if agent.creator_id != current_user.id:
            return APIResponse.error(message="无权删除此智能体", code=403)

        await agent_service.delete_agent(db=db, agent_id=agent_id)

        logger.info(f"用户 {current_user.id} 删除智能体: {agent_id}")
        response_data = schemas.SessionActionResponse(
            success=True, message="智能体已删除"
        )
        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"删除智能体失败: {str(e)}")
        return APIResponse.error(message="删除智能体失败")


@router.post(
    "/agents/{agent_id}/deploy", response_model=APIResponse[schemas.AgentDeployResponse]
)
async def deploy_agent_to_production(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    admin_password: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    将智能体部署到生产环境

    需要管理员权限，将测试智能体上线到生产环境
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        # 这里应该实现实际的部署逻辑
        # TODO: 使用db和admin_password验证和部署
        # 暂时返回模拟响应
        logger.info(f"用户 {current_user.id} 请求部署智能体 {agent_id} 到生产环境")

        response_data = schemas.AgentDeployResponse(
            success=True,
            message="智能体部署成功",
            agent_id=agent_id,
            deploy_time="2025-07-26T00:00:00Z",
        )
        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"部署智能体失败: {str(e)}")
        return APIResponse.error(message="部署智能体失败")


# =============================================================================
# 模板管理API
# =============================================================================


@router.post(
    "/templates", response_model=APIResponse[schemas.EvaluationTemplateResponse]
)
async def create_evaluation_template(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    template_in: schemas.EvaluationTemplateCreate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建评测模板

    保存常用的问题集和评分标准为模板
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

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
        return APIResponse.success(data=template)

    except Exception as e:
        logger.error(f"创建评测模板失败: {str(e)}")
        return APIResponse.error(message="创建评测模板失败")


@router.get(
    "/templates",
    response_model=APIResponse[PaginationData[schemas.EvaluationTemplateResponse]],
)
async def get_evaluation_templates(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    include_public: bool = Query(True, description="是否包含公开模板"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=1000, description="每页数量"),
) -> Any:
    """
    获取评测模板列表

    返回用户的模板和公开模板
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        from sqlalchemy import or_, select

        from app.models.evaluation import EvaluationTemplate

        # 计算skip和limit
        skip = (page - 1) * page_size

        # 构建查询条件
        conditions = [EvaluationTemplate.creator_id == current_user.id]
        if include_public:
            conditions.append(EvaluationTemplate.is_public == True)

        stmt = (
            select(EvaluationTemplate)
            .where(or_(*conditions))
            .offset(skip)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        templates = result.scalars().all()

        # 当前获取的数量，如果少于page_size说明是最后一页
        current_count = len(templates)
        # 估算总数 - 实际项目中应该有专门的count方法
        total = skip + current_count
        if current_count == page_size:
            # 可能还有更多数据，这里用估算
            total = skip + current_count + 1
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1

        # 创建分页数据
        pagination_data = PaginationData[schemas.EvaluationTemplateResponse](
            list=templates,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

        return APIResponse.success(data=pagination_data)

    except Exception as e:
        logger.error(f"获取评测模板失败: {str(e)}")
        return APIResponse.error(message="获取评测模板失败")


# =============================================================================
# 批量评测和结果导出API
# =============================================================================


@router.post(
    "/sessions/batch",
    response_model=APIResponse[List[schemas.EvaluationSessionResponse]],
)
async def create_batch_evaluation(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    batch_request: schemas.BatchEvaluationRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    批量创建评测会话

    一次性创建多个评测会话
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

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

        logger.info(f"用户 {current_user.id} 批量创建 {len(sessions)} 个评测会话")
        return APIResponse.success(data=sessions)

    except Exception as e:
        logger.error(f"批量创建评测失败: {str(e)}")
        return APIResponse.error(message="批量创建评测失败")


@router.post(
    "/results/export", response_model=APIResponse[schemas.EvaluationExportResponse]
)
async def export_evaluation_results(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    export_request: schemas.EvaluationExportRequest,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    导出评测结果

    将评测结果导出为CSV、JSON或Excel格式
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        # 这里应该实现实际的导出逻辑
        # TODO: 使用db获取数据并导出
        # 暂时返回下载链接
        logger.info(
            f"用户 {current_user.id} 导出评测结果: {len(export_request.session_ids)} 个会话"
        )

        response_data = schemas.EvaluationExportResponse(
            download_url=f"/evaluation/downloads/{current_user.id}/export.{export_request.format}",
            format=export_request.format,
            session_count=len(export_request.session_ids),
        )
        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"导出评测结果失败: {str(e)}")
        return APIResponse.error(message="导出评测结果失败")


@router.post(
    "/sessions/compare",
    response_model=APIResponse[schemas.EvaluationComparisonResponse],
)
async def compare_evaluation_sessions(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    session_ids: List[str],
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    对比评测会话结果

    分析多个会话的结果差异
    """
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")

    try:
        # 这里应该实现实际的对比逻辑
        # TODO: 使用db获取数据并对比
        # 暂时返回模拟数据
        logger.info(f"用户 {current_user.id} 对比评测会话: {session_ids}")

        response_data = schemas.EvaluationComparisonResponse(
            agents=[],
            questions=[],
            results={},
            summary={
                "best_agent": None,
                "average_score": None,
                "score_variance": None,
            },
        )
        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"对比评测会话失败: {str(e)}")
        return APIResponse.error(message="对比评测会话失败")
