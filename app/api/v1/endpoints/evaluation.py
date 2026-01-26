"""评测系统API端点 - 专门用于评测聊天系统效果"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.api.tags import INTY_EVAL_TAG, NOT_USED_TAG
from app.api.utils.logger_route import LoggerRoute
from app.services.evaluation_service import EvaluationService
from app.services.question_parser_service import QuestionParserService
from app.services.scoring_service import ScoringService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", route_class=LoggerRoute)


@router.get(
    "/sessions",
    response_model=List[schemas.EvaluationSessionResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_evaluation_sessions(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
    status: Optional[str] = Query(None, description="按状态过滤"),
) -> Any:
    """
    获取评测会话列表

    返回当前用户创建的评测会话列表
    """
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        evaluation_service = EvaluationService(db)

        sessions = await evaluation_service.get_user_sessions(
            user_id=current_user.id, skip=skip, limit=limit, status=status
        )

        return sessions

    except Exception as e:
        logger.error(f"获取评测会话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取评测会话列表失败")


@router.post(
    "/sessions",
    response_model=schemas.EvaluationSessionResponse,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
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
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="创建评测会话失败")


@router.post(
    "/sessions/{session_id}/start",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        evaluation_service = EvaluationService(db)

        # 验证会话所有权
        session = await evaluation_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="评测会话不存在")

        if session.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权操作此评测会话")

        success = await evaluation_service.start_session(session_id)

        logger.info(f"用户 {current_user.id} 启动评测会话: {session_id}")
        return {"success": success, "message": "评测会话已启动"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"启动评测会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="启动评测会话失败")


@router.get(
    "/sessions/{session_id}",
    response_model=schemas.EvaluationSessionDetail,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        evaluation_service = EvaluationService(db)

        session = await evaluation_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="评测会话不存在")

        if session.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此评测会话")

        return session

    except Exception as e:
        logger.error(f"获取评测会话详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取会话详情失败")


@router.get(
    "/sessions/{session_id}/results",
    response_model=List[schemas.EvaluationResultResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        evaluation_service = EvaluationService(db)

        # 验证权限
        session = await evaluation_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="评测会话不存在")

        if session.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此评测会话")

        results = await evaluation_service.get_session_results(session_id)
        return results

    except Exception as e:
        logger.error(f"获取评测结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取评测结果失败")


@router.post(
    "/sessions/{session_id}/cancel",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        evaluation_service = EvaluationService(db)

        # 验证权限
        session = await evaluation_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="评测会话不存在")

        if session.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权操作此评测会话")

        success = await evaluation_service.cancel_session(session_id)

        logger.info(f"用户 {current_user.id} 取消评测会话: {session_id}")
        return {"success": success, "message": "评测会话已取消"}

    except Exception as e:
        logger.error(f"取消评测会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="取消评测会话失败")


@router.post(
    "/questions/parse",
    response_model=schemas.QuestionFileUpload,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        # 验证文件大小（最大10MB）
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小不能超过10MB")

        # 验证文件类型
        allowed_types = [".json"]
        if not any(file.filename.lower().endswith(ext) for ext in allowed_types):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型，只支持: {', '.join(allowed_types)}",
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
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")


@router.get(
    "/models",
    response_model=List[schemas.ScoringModelInfo],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_scoring_models(
    *,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取可用模型列表
    """
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        scoring_service = ScoringService()
        models = await scoring_service.get_available_models()
        return models

    except Exception as e:
        logger.error(f"获取评分模型失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取评分模型失败")


@router.post(
    "/scoring-criteria/validate",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        scoring_service = ScoringService()
        validation = scoring_service.validate_scoring_criteria(criteria)
        return validation

    except Exception as e:
        logger.error(f"验证评分标准失败: {str(e)}")
        raise HTTPException(status_code=500, detail="验证评分标准失败")


@router.get(
    "/stats",
    response_model=schemas.EvaluationStats,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
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
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="获取统计信息失败")


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


@router.get(
    "/agents",
    response_model=List[schemas.Agent],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_evaluation_agents(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    type: str = Query("public", pattern="^(public|private)$", description="智能体类型"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> Any:
    """
    获取用于评测的智能体列表

    支持获取公开和私有智能体，用于评测系统选择测试对象
    """
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        from app.services import agent_service

        if type == "private":
            # 获取用户创建的私有智能体
            agents = await agent_service.get_agents_by_creator(
                db, creator_id=current_user.id, skip=skip, limit=limit
            )
        else:
            # 获取公开智能体
            agents = await agent_service.get_public_agents(db, skip=skip, limit=limit)

        logger.info(
            f"用户 {current_user.id} 获取评测智能体列表: {type}, 数量: {len(agents)}"
        )
        return agents

    except Exception as e:
        logger.error(f"获取智能体列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取智能体列表失败")


@router.post(
    "/agents",
    response_model=schemas.Agent,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
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
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        from app.services import agent_service

        agent = await agent_service.create_agent(
            db=db, agent_in=agent_in, creator_id=current_user.id
        )

        logger.info(f"用户 {current_user.id} 创建评测智能体: {agent.id}")
        return agent

    except Exception as e:
        logger.error(f"创建智能体失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建智能体失败")


@router.put(
    "/agents/{agent_id}",
    response_model=schemas.Agent,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
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
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        from app.services import agent_service

        # 验证权限
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="智能体不存在")

        if agent.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权修改此智能体")

        updated_agent = await agent_service.update_agent(
            db=db, agent_id=agent_id, agent_in=agent_in
        )

        logger.info(f"用户 {current_user.id} 更新智能体: {agent_id}")
        return updated_agent

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新智能体失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新智能体失败")


@router.delete(
    "/agents/{agent_id}",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        from app.services import agent_service

        # 验证权限
        agent = await agent_service.get_agent(db, agent_id=agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="智能体不存在")

        if agent.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权删除此智能体")

        await agent_service.delete_agent(db=db, agent_id=agent_id)

        logger.info(f"用户 {current_user.id} 删除智能体: {agent_id}")
        return {"message": "智能体已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除智能体失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除智能体失败")


@router.get(
    "/agents/{agent_id}/check-background-aspect-ratio",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def check_background_aspect_ratio(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    检查背景图是否为 9:16 比例

    用于生成背景动图前验证背景图比例
    """
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
            raise HTTPException(status_code=400, detail="请先上传背景图")

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
                status_code=400, detail="无法获取背景图 URL，请重新上传背景图"
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
        raise HTTPException(status_code=500, detail="检查背景图宽高比失败")


@router.post(
    "/agents/{agent_id}/upload-cropped-background",
    response_model=schemas.APIResponse[schemas.Agent],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def upload_cropped_background(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    agent_id: str,
    file: UploadFile = File(...),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    上传裁剪后的背景图

    替换智能体的背景图为裁剪后的 9:16 比例图片
    """
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
                status_code=400, detail=result.message or "图片上传失败"
            )

        # 更新 Agent 的背景图
        agent_update = AgentUpdate(background=result.data.url)
        updated_agent = await agent_service.update_agent(
            db, db_agent=agent, agent_in=agent_update
        )

        logger.info(
            f"用户 {current_user.id} 为智能体 {agent_id} 上传裁剪后的背景图: {result.data.url}"
        )
        return schemas.APIResponse.success(data=updated_agent)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传裁剪后的背景图失败: {str(e)}")
        raise HTTPException(status_code=500, detail="上传裁剪后的背景图失败")


@router.post(
    "/agents/{agent_id}/deploy",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        # 这里应该实现实际的部署逻辑
        # 暂时返回模拟响应
        logger.info(f"用户 {current_user.id} 请求部署智能体 {agent_id} 到生产环境")

        return {
            "success": True,
            "message": "智能体部署成功",
            "agent_id": agent_id,
            "deploy_time": "2025-07-26T00:00:00Z",
        }

    except Exception as e:
        logger.error(f"部署智能体失败: {str(e)}")
        raise HTTPException(status_code=500, detail="部署智能体失败")


# =============================================================================
# 模板管理API
# =============================================================================


@router.post(
    "/templates",
    response_model=schemas.EvaluationTemplateResponse,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="创建评测模板失败")


@router.get(
    "/templates",
    response_model=List[schemas.EvaluationTemplateResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_evaluation_templates(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    include_public: bool = Query(True, description="是否包含公开模板"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """
    获取评测模板列表

    返回用户的模板和公开模板
    """
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        from sqlalchemy import or_, select

        from app.models.evaluation import EvaluationTemplate

        # 构建查询条件
        conditions = [EvaluationTemplate.creator_id == current_user.id]
        if include_public:
            conditions.append(EvaluationTemplate.is_public == True)

        stmt = (
            select(EvaluationTemplate).where(or_(*conditions)).offset(skip).limit(limit)
        )

        result = await db.execute(stmt)
        templates = result.scalars().all()

        return templates

    except Exception as e:
        logger.error(f"获取评测模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取评测模板失败")


# =============================================================================
# 批量评测和结果导出API
# =============================================================================


@router.post(
    "/sessions/batch",
    response_model=List[schemas.EvaluationSessionResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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
        return schemas.APIResponse.error(message="Unauthorized access")

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
        return sessions

    except Exception as e:
        logger.error(f"批量创建评测失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量创建评测失败")


@router.post(
    "/results/export",
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="导出评测结果失败")


@router.post(
    "/sessions/compare",
    response_model=schemas.EvaluationComparison,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
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
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="对比评测会话失败")


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
    email: Optional[str], user_id: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    normalized_email = email.strip() if email else None
    normalized_user_id = user_id.strip() if user_id else None

    # 必须且只能提供其中一个
    if bool(normalized_email) == bool(normalized_user_id):
        raise HTTPException(status_code=400, detail="必须且只能提供 email 或 user_id")

    return normalized_email, normalized_user_id


async def _find_user_info_by_identifier(
    service: Any, *, email: Optional[str], user_id: Optional[str]
) -> Dict[str, Any]:
    normalized_email, normalized_user_id = _normalize_user_lookup_params(email, user_id)

    if normalized_email:
        user_info = await service.find_user_by_email(normalized_email)
        if not user_info:
            raise HTTPException(
                status_code=404, detail=f"未找到邮箱为 {normalized_email} 的用户"
            )
        return user_info

    user_info = await service.find_user_by_id(normalized_user_id)
    if not user_info:
        raise HTTPException(
            status_code=404, detail=f"未找到ID为 {normalized_user_id} 的用户"
        )
    return user_info


@router.get(
    "/user-analytics/new-users",
    response_model=List[schemas.user_analytics.DailyNewUsersResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_new_users(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="获取用户统计失败")


@router.get(
    "/user-analytics/user-activity",
    response_model=List[schemas.user_analytics.UserChatActivityItem],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_user_activity(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="获取用户活动失败")


@router.get(
    "/user-analytics/conversation-rounds",
    response_model=List[schemas.user_analytics.ConversationRoundsResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_conversation_rounds(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="获取对话轮数失败")


@router.get(
    "/user-analytics/user-rounds-distribution",
    response_model=List[schemas.user_analytics.UserRoundsDistributionItem],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_user_rounds_distribution(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="获取用户轮数分布失败")


@router.get(
    "/user-analytics/popular-agents",
    response_model=List[schemas.user_analytics.PopularAgentsResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_popular_agents(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
        activity_data = await service.get_user_chat_activity(reg_start, reg_end)

        agent_stats = defaultdict(
            lambda: {
                "users": set(),
                "rounds": 0,
                "sessions": [],
                "total_chats": set(),
            }
        )
        rounds_data = await service.get_conversation_rounds(
            reg_start, reg_end, act_start, act_end
        )
        chat_to_rounds = {
            item["chat_id"]: item["message_count_excluding_opening"]
            for item in rounds_data
        }

        for item in activity_data:
            if item["chat_id"] and item["agent_name"]:
                agent_name = item["agent_name"]
                agent_stats[agent_name]["total_chats"].add(item["chat_id"])

        for item in activity_data:
            if item["chat_id"] and item["agent_name"]:
                agent_name = item["agent_name"]
                rounds = chat_to_rounds.get(item["chat_id"], 0)
                if rounds > 0:
                    agent_stats[agent_name]["users"].add(item["user_id"])
                    agent_stats[agent_name]["rounds"] += rounds
                    agent_stats[agent_name]["sessions"].append(rounds)

        result = []
        for agent_name, stats in agent_stats.items():
            user_count = len(stats["users"])
            total_rounds = stats["rounds"]
            sessions = stats["sessions"]
            active_sessions = len(sessions)
            total_sessions = len(stats["total_chats"])

            avg_rounds_per_user = total_rounds / user_count if user_count > 0 else 0.0
            sessions_ge_5 = sum(1 for r in sessions if r >= 5)
            sessions_ge_10 = sum(1 for r in sessions if r >= 10)
            pct_sessions_ge_5 = (
                (sessions_ge_5 / active_sessions * 100) if active_sessions > 0 else 0.0
            )
            pct_sessions_ge_10 = (
                (sessions_ge_10 / active_sessions * 100) if active_sessions > 0 else 0.0
            )
            open_rate = (
                (active_sessions / total_sessions * 100) if total_sessions > 0 else 0.0
            )

            result.append(
                {
                    "agent_name": agent_name,
                    "user_count": user_count,
                    "total_rounds": total_rounds,
                    "avg_rounds_per_user": round(avg_rounds_per_user, 2),
                    "pct_sessions_ge_5": round(pct_sessions_ge_5, 2),
                    "pct_sessions_ge_10": round(pct_sessions_ge_10, 2),
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "open_rate": round(open_rate, 2),
                }
            )

        result.sort(key=lambda x: x["user_count"], reverse=True)
        return result[:20]

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取热门角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取热门角色失败")


@router.get(
    "/user-analytics/users-hitting-limit",
    response_model=List[schemas.user_analytics.UsersHittingLimitResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_users_hitting_limit(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        now = datetime.now(timezone.utc)

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
        raise HTTPException(status_code=500, detail="获取达到限制的用户失败")


@router.get(
    "/user-analytics/agent-analytics",
    response_model=List[schemas.user_analytics.AgentAnalyticsResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_agent_analytics(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
        data = await service.get_agent_analytics(reg_start, reg_end, act_start, act_end)
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取角色分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取角色分析失败")


@router.get(
    "/user-analytics/user-sessions-detail",
    response_model=List[schemas.user_analytics.UserSessionsDetailResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_user_sessions_detail(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="获取用户会话详情失败")


@router.get(
    "/user-analytics/conversations-detail",
    response_model=List[schemas.user_analytics.ConversationsDetailResponse],
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_conversations_detail(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="获取对话详情失败")


@router.get(
    "/user-analytics/stats",
    response_model=schemas.user_analytics.UserAnalyticsStatsResponse,
    tags=[INTY_EVAL_TAG, NOT_USED_TAG],
)
async def get_user_analytics_stats(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
        data = await service.get_analytics_stats(reg_start, reg_end, act_start, act_end)
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取统计数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取统计数据失败")


@router.get(
    "/user-analytics/llm-latency",
    response_model=schemas.user_analytics.LLMLatencyResponse,
    tags=[INTY_EVAL_TAG],
)
async def get_llm_latency_trend(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        now = datetime.now(timezone.utc)

        # 直接解析活跃日期范围（不依赖 register 参数）
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
        raise HTTPException(status_code=500, detail="获取 LLM 延迟趋势失败")


@router.get(
    "/user-analytics/image-generation-latency",
    response_model=schemas.user_analytics.ImageGenerationLatencyResponse,
    tags=[INTY_EVAL_TAG],
)
async def get_image_generation_latency_trend(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        now = datetime.now(timezone.utc)

        # 直接解析活跃日期范围
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
        else:
            raise HTTPException(
                status_code=400,
                detail="请提供 activity_start_date/activity_end_date 或 activity_last_days",
            )

        service = UserAnalyticsService(db)
        data = await service.get_image_generation_latency_trend(act_start, act_end)
        return {"data": data}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取生图耗时趋势失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取生图耗时趋势失败")


@router.get(
    "/user-analytics/live-chat-latency",
    response_model=schemas.user_analytics.LiveChatLatencyResponse,
    tags=[INTY_EVAL_TAG],
)
async def get_live_chat_latency_trend(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        now = datetime.now(timezone.utc)

        # 解析活跃日期范围
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
        raise HTTPException(status_code=500, detail="获取 Live Chat 延迟趋势失败")


@router.get(
    "/user-analytics/live-chat-stats",
    response_model=schemas.user_analytics.LiveChatBasicStatsResponse,
    tags=[INTY_EVAL_TAG],
)
async def get_live_chat_basic_stats(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
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
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        now = datetime.now(timezone.utc)

        # 解析活跃日期范围
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
        raise HTTPException(status_code=500, detail="获取 Live Chat 基础统计失败")


@router.get(
    "/user-analytics/user-daily-messages",
    response_model=schemas.user_analytics.UserDailyMessagesResponse,
    tags=[INTY_EVAL_TAG],
)
async def get_user_daily_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    email: Optional[str] = Query(None, description="用户邮箱"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
) -> Any:
    """获取用户每日消息统计"""
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        from datetime import datetime, timedelta, timezone

        from app.services.user_analytics_service import UserAnalyticsService

        service = UserAnalyticsService(db)

        # 查找用户
        user_info = await _find_user_info_by_identifier(
            service, email=email, user_id=user_id
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

        # 获取每日消息统计
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
        raise HTTPException(status_code=500, detail="获取用户每日消息统计失败")


@router.get(
    "/user-analytics/user-today-stats",
    response_model=schemas.user_analytics.UserTodayStatsResponse,
    tags=[INTY_EVAL_TAG],
)
async def get_user_today_stats(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    email: Optional[str] = Query(None, description="用户邮箱"),
    user_id: Optional[str] = Query(None, description="用户ID"),
) -> Any:
    """获取用户当日统计"""
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="获取用户当日统计失败")


@router.get(
    "/user-analytics/user-generated-images",
    response_model=schemas.user_analytics.UserGeneratedImagesResponse,
    tags=[INTY_EVAL_TAG],
)
async def get_user_generated_images(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    email: Optional[str] = Query(None, description="用户邮箱"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(50, ge=1, le=200, description="返回的记录数"),
) -> Any:
    """
    获取指定用户的所有聊天生成图片

    从 resources 表查询带有 generation_prompt 的图片资源
    """
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
            agent_query = select(Agent.id, Agent.name).where(Agent.id.in_(agent_ids))
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
                cdn_url = image_transform_service.transform_desktop(resource.url)
            except Exception as e:
                logger.warning(f"转换图片URL失败: {resource.url}, 错误: {str(e)}")
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
                        resource.created_at.isoformat() if resource.created_at else None
                    ),
                    "agent_id": resource.agent_id,
                    "agent_name": agent_info.get("name"),
                }
            )

        # 获取总数
        count_query = (
            select(Resource)
            .where(
                Resource.user_id == user_info["id"],
                Resource.type == ResourceType.IMAGE,
                Resource.resource_metadata.isnot(None),
            )
        )
        count_result = await db.execute(count_query)
        all_resources = count_result.scalars().all()
        total = 0
        for resource in all_resources:
            metadata = resource.resource_metadata or {}
            if metadata.get("generation_prompt"):
                total += 1

        logger.debug(f"获取用户 {user_info['id']} 的生成图片，共 {len(images)} 张")
        return {"images": images, "total": total}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户生成图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户生成图片失败")


@router.get(
    "/user-analytics/user-sessions",
    response_model=schemas.user_analytics.UserSessionsResponse,
    tags=[INTY_EVAL_TAG],
)
async def get_user_sessions(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    email: Optional[str] = Query(None, description="用户邮箱"),
    user_id: Optional[str] = Query(None, description="用户ID"),
) -> Any:
    """获取用户的所有会话列表"""
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="获取用户会话列表失败")


@router.get(
    "/user-analytics/session-messages",
    response_model=schemas.user_analytics.SessionMessagesResponse,
    tags=[INTY_EVAL_TAG],
)
async def get_session_messages(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    chat_id: str = Query(..., description="会话ID (chat_id)"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(50, ge=1, le=200, description="每页数量"),
) -> Any:
    """获取指定会话的对话历史"""
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

    try:
        from app.services.user_analytics_service import UserAnalyticsService

        service = UserAnalyticsService(db)

        # 获取会话消息
        result = await service.get_session_messages(chat_id, page, size)

        return result

    except Exception as e:
        logger.error(f"获取会话消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取会话消息失败")


# =============================================================================
# 生成图片管理API
# =============================================================================


@router.get(
    "/agents/generated-images/counts",
    tags=[INTY_EVAL_TAG],
)
async def get_all_agents_image_counts(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取所有角色的生成图片数量

    返回格式: {"agent_id_1": 5, "agent_id_2": 10, ...}
    """
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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
        raise HTTPException(status_code=500, detail="获取角色图片数量失败")


@router.get(
    "/agents/{agent_id}/generated-images",
    tags=[INTY_EVAL_TAG],
)
async def get_agent_generated_images(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user),
    agent_id: str,
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(50, ge=1, le=200, description="返回的记录数"),
) -> Any:
    """
    获取指定角色的所有聊天生成图片

    从 resources 表查询带有 generation_prompt 的图片资源
    """
    if not current_user.is_superuser:
        return schemas.APIResponse.error(message="Unauthorized access")

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

            user_info = user_info_map.get(resource.user_id, {})
            images.append(
                {
                    "url": cdn_url,
                    "gcs_url": resource.url,
                    "generation_prompt": generation_prompt,
                    "reference_image_url": reference_image_url,
                    "width": size.get("width"),
                    "height": size.get("height"),
                    "created_at": (
                        resource.created_at.isoformat() if resource.created_at else None
                    ),
                    "user_id": resource.user_id,
                    "user_nickname": user_info.get("nickname"),
                    "user_email": user_info.get("email"),
                    "user_photo": user_info.get("user_photo"),
                }
            )

        logger.debug(f"获取角色 {agent_id} 的生成图片，共 {len(images)} 张")
        return {"images": images, "total": len(images)}

    except Exception as e:
        logger.error(f"获取角色生成图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取角色生成图片失败")
