# CREATED_BY_AGENT
"""节日记忆配置与立即执行 API（仅超级用户）"""

import asyncio
from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.api.tags import INTY_EVAL_TAG
from app.api.utils.logger_route import LoggerRoute
from app.models.memory import FestivalMemoryConfig, Memory
from app.schemas.festival_memory import (
    FestivalMemoryConfigCreate,
    FestivalMemoryConfigInDB,
    FestivalMemoryConfigResultResponse,
    FestivalMemoryConfigUpdate,
    FestivalMemoryExtractionRunRequest,
    FestivalMemoryExtractionRunResponse,
    FestivalMemoryResultItem,
)
from app.services import festival_memory_service
from app.services import festival_memory_task_state_service
from app.services.memory_service import MEMORY_TYPE_FESTIVAL

router = APIRouter(
    prefix="/evaluation/admin", route_class=LoggerRoute, tags=[INTY_EVAL_TAG]
)


async def get_current_superuser(
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> schemas.User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Only superusers can access this endpoint"
        )
    return current_user


def _resolve_run_state_fields(config: FestivalMemoryConfig) -> dict[str, Any]:
    state = festival_memory_task_state_service.get_run_state(config.id)
    if state is None:
        if config.last_run_at is not None:
            return {
                "run_status": "completed",
                "run_started_at": None,
                "run_finished_at": config.last_run_at,
                "run_total_pairs": None,
                "run_success_count": None,
                "run_failed_count": None,
                "run_error_message": None,
            }
        return {
            "run_status": "idle",
            "run_started_at": None,
            "run_finished_at": None,
            "run_total_pairs": None,
            "run_success_count": None,
            "run_failed_count": None,
            "run_error_message": None,
        }
    return {
        "run_status": state.run_status,
        "run_started_at": state.run_started_at,
        "run_finished_at": state.run_finished_at,
        "run_total_pairs": state.run_total_pairs,
        "run_success_count": state.run_success_count,
        "run_failed_count": state.run_failed_count,
        "run_error_message": state.run_error_message,
    }


@router.get(
    "/festival-memory-configs",
    response_model=schemas.APIResponse[List[FestivalMemoryConfigInDB]],
    summary="节日记忆配置列表",
)
async def list_festival_memory_configs(
    db: AsyncSession = Depends(deps.get_async_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: schemas.User = Depends(get_current_superuser),
) -> Any:
    result = await db.execute(
        select(FestivalMemoryConfig)
        .order_by(FestivalMemoryConfig.id.desc())
        .offset(skip)
        .limit(limit)
    )
    configs = result.scalars().all()
    response_items = []
    for config in configs:
        item = FestivalMemoryConfigInDB.model_validate(config).model_copy(
            update=_resolve_run_state_fields(config)
        )
        response_items.append(item)
    return schemas.APIResponse.success(
        data=response_items
    )


@router.post(
    "/festival-memory-configs",
    response_model=schemas.APIResponse[FestivalMemoryConfigInDB],
    summary="创建节日记忆配置",
)
async def create_festival_memory_config(
    body: FestivalMemoryConfigCreate,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(get_current_superuser),
) -> Any:
    config = FestivalMemoryConfig(
        festival_name=body.festival_name,
        festival_date=body.festival_date,
        prompt=body.prompt,
        enabled=body.enabled,
        timezone=body.timezone,
        run_at_date=body.run_at_date,
        run_at_hour=body.run_at_hour,
        min_rounds_in_window=body.min_rounds_in_window,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return schemas.APIResponse.success(
        data=FestivalMemoryConfigInDB.model_validate(config)
    )


@router.delete(
    "/festival-memory-configs/{config_id}",
    response_model=schemas.APIResponse[None],
    summary="删除节日记忆配置",
)
async def delete_festival_memory_config(
    config_id: int,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(get_current_superuser),
) -> Any:
    result = await db.execute(
        select(FestivalMemoryConfig).where(FestivalMemoryConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    await db.delete(config)
    await db.commit()
    return schemas.APIResponse.success(data=None)


@router.put(
    "/festival-memory-configs/{config_id}",
    response_model=schemas.APIResponse[FestivalMemoryConfigInDB],
    summary="更新节日记忆配置",
)
async def update_festival_memory_config(
    config_id: int,
    body: FestivalMemoryConfigUpdate,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(get_current_superuser),
) -> Any:
    result = await db.execute(
        select(FestivalMemoryConfig).where(FestivalMemoryConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    if body.festival_name is not None:
        config.festival_name = body.festival_name
    if body.festival_date is not None:
        config.festival_date = body.festival_date
    if body.prompt is not None:
        config.prompt = body.prompt
    if body.enabled is not None:
        config.enabled = body.enabled
    if body.timezone is not None:
        config.timezone = body.timezone
    if body.run_at_date is not None:
        config.run_at_date = body.run_at_date
    if body.run_at_hour is not None:
        config.run_at_hour = body.run_at_hour
    if body.min_rounds_in_window is not None:
        config.min_rounds_in_window = body.min_rounds_in_window
    if (
        config.run_at_date is not None
        and config.festival_date is not None
        and config.run_at_date < config.festival_date
    ):
        raise HTTPException(
            status_code=400,
            detail="Run date cannot be earlier than the festival date",
        )
    await db.commit()
    await db.refresh(config)
    return schemas.APIResponse.success(
        data=FestivalMemoryConfigInDB.model_validate(config)
    )


@router.get(
    "/festival-memory-configs/{config_id}/results",
    response_model=schemas.APIResponse[FestivalMemoryConfigResultResponse],
    summary="查看节日记忆配置最近结果（最多 10 条）",
)
async def get_festival_memory_config_results(
    config_id: int,
    limit: int = Query(10, ge=1, le=10),
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(get_current_superuser),
) -> Any:
    config_result = await db.execute(
        select(FestivalMemoryConfig).where(FestivalMemoryConfig.id == config_id)
    )
    config = config_result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    memory_result = await db.execute(
        select(
            Memory.id,
            Memory.user_id,
            Memory.agent_id,
            Memory.festival_name,
            Memory.festival_date,
            Memory.content,
            Memory.extracted_at,
        )
        .where(
            Memory.memory_type == MEMORY_TYPE_FESTIVAL,
            Memory.festival_name == config.festival_name,
            Memory.festival_date == config.festival_date,
        )
        .order_by(Memory.extracted_at.desc(), Memory.id.desc())
        .limit(limit)
    )
    rows = memory_result.fetchall()
    items = [
        FestivalMemoryResultItem(
            memory_id=row[0],
            user_id=row[1],
            agent_id=row[2],
            festival_name=row[3],
            festival_date=row[4],
            memory=row[5],
            extracted_at=row[6],
        )
        for row in rows
    ]

    run_state_fields = _resolve_run_state_fields(config)
    return schemas.APIResponse.success(
        data=FestivalMemoryConfigResultResponse(
            config_id=config.id,
            festival_name=config.festival_name,
            festival_date=config.festival_date,
            run_status=run_state_fields["run_status"],
            run_started_at=run_state_fields["run_started_at"],
            run_finished_at=run_state_fields["run_finished_at"],
            run_total_pairs=run_state_fields["run_total_pairs"],
            run_success_count=run_state_fields["run_success_count"],
            run_failed_count=run_state_fields["run_failed_count"],
            run_error_message=run_state_fields["run_error_message"],
            items=items,
        )
    )


@router.post(
    "/festival-memory-extraction/run",
    response_model=schemas.APIResponse[FestivalMemoryExtractionRunResponse],
    summary="立即执行节日记忆抽取",
)
async def run_festival_memory_extraction(
    body: FestivalMemoryExtractionRunRequest,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(get_current_superuser),
) -> Any:
    tracked_config: FestivalMemoryConfig | None = None
    if body.config_id is not None:
        result = await db.execute(
            select(FestivalMemoryConfig).where(
                FestivalMemoryConfig.id == body.config_id
            )
        )
        config = result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        festival_name = config.festival_name
        festival_date = config.festival_date
        prompt = config.prompt
        tz_str = getattr(config, "timezone", "UTC") or "UTC"
        min_rounds = (
            getattr(config, "min_rounds_in_window", None)
            or festival_memory_service.DEFAULT_MIN_ROUNDS_IN_WINDOW
        )
        tracked_config = config
    else:
        if (
            body.festival_name is None
            or body.festival_date is None
            or body.prompt is None
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "festival_name, festival_date, and prompt are required when "
                    "config_id is not provided"
                ),
            )
        festival_name = body.festival_name
        festival_date = body.festival_date
        prompt = body.prompt
        tz_str = (body.timezone or "UTC").strip() or "UTC"
        min_rounds = (
            body.min_rounds_in_window
            or festival_memory_service.DEFAULT_MIN_ROUNDS_IN_WINDOW
        )

    if tracked_config is not None:
        festival_memory_task_state_service.mark_running(
            tracked_config.id,
            tracked_config.festival_name,
            tracked_config.festival_date,
        )

    total = 0
    success = 0
    failed = 0
    try:
        pairs = await asyncio.to_thread(
            festival_memory_service.get_pairs_with_min_rounds_in_window_sync,
            festival_date,
            min_rounds,
            tz_str,
        )
        total = len(pairs)
        for user_id, agent_id in pairs:
            try:
                ok = await festival_memory_service.extract_festival_and_save(
                    db, user_id, agent_id, festival_name, festival_date, prompt
                )
            except Exception as e:
                await db.rollback()
                failed += 1
                logger.warning(
                    f"festival memory extraction failed for user={user_id}, "
                    f"agent={agent_id}, config_id={body.config_id}: {e}"
                )
                continue
            if ok:
                success += 1
            else:
                failed += 1

        if tracked_config is not None:
            tracked_config.last_run_at = datetime.now(timezone.utc)
            await db.commit()
            festival_memory_task_state_service.mark_completed(
                tracked_config.id,
                tracked_config.festival_name,
                tracked_config.festival_date,
                total_pairs=total,
                success_count=success,
                failed_count=failed,
            )
    except Exception as e:
        if tracked_config is not None:
            festival_memory_task_state_service.mark_failed(
                tracked_config.id,
                tracked_config.festival_name,
                tracked_config.festival_date,
                total_pairs=total,
                success_count=success,
                failed_count=failed,
                error_message=str(e),
            )
        raise

    logger.info(
        f"节日记忆抽取完成 festival={festival_name} total={total} success={success} failed={failed}"
    )
    return schemas.APIResponse.success(
        data=FestivalMemoryExtractionRunResponse(
            total_pairs=total,
            success_count=success,
            failed_count=failed,
        )
    )
