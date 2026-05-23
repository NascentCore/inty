# CREATED_BY_AGENT
"""节日记忆配置与立即执行 API（仅超级用户）"""

import asyncio
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.tags import INTY_EVAL_TAG
from app.api.types.llm_config import LLMConfig
from app.api.utils.logger_route import LoggerRoute
from app.models.memory import FestivalMemoryConfig
from backend.ops.schemas.festival_memory import (
    FestivalMemoryConfigCreate,
    FestivalMemoryConfigInDB,
    FestivalMemoryConfigUpdate,
    FestivalMemoryExtractionRunRequest,
    FestivalMemoryExtractionRunResponse,
)
from app.services import festival_memory_service
from app.schemas.response import APIResponse
from app.schemas.user import User as UserSchema

router = APIRouter(
    prefix="/evaluation/admin", route_class=LoggerRoute, tags=[INTY_EVAL_TAG]
)


@router.get(
    "/festival-memory-configs",
    response_model=APIResponse[List[FestivalMemoryConfigInDB]],
    summary="节日记忆配置列表",
)
async def list_festival_memory_configs(
    db: AsyncSession = Depends(deps.get_async_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    result = await db.execute(
        select(FestivalMemoryConfig)
        .order_by(FestivalMemoryConfig.id.desc())
        .offset(skip)
        .limit(limit)
    )
    configs = result.scalars().all()
    return APIResponse.success(
        data=[FestivalMemoryConfigInDB.model_validate(c) for c in configs]
    )


@router.post(
    "/festival-memory-configs",
    response_model=APIResponse[FestivalMemoryConfigInDB],
    summary="创建节日记忆配置",
)
async def create_festival_memory_config(
    body: FestivalMemoryConfigCreate,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
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
        llm_config=(
            body.llm_config.model_dump()
            if body.llm_config is not None
            else None
        ),
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return APIResponse.success(
        data=FestivalMemoryConfigInDB.model_validate(config)
    )


@router.delete(
    "/festival-memory-configs/{config_id}",
    response_model=APIResponse[None],
    summary="删除节日记忆配置",
)
async def delete_festival_memory_config(
    config_id: int,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    result = await db.execute(
        select(FestivalMemoryConfig).where(FestivalMemoryConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    await db.delete(config)
    await db.commit()
    return APIResponse.success(data=None)


@router.put(
    "/festival-memory-configs/{config_id}",
    response_model=APIResponse[FestivalMemoryConfigInDB],
    summary="更新节日记忆配置",
)
async def update_festival_memory_config(
    config_id: int,
    body: FestivalMemoryConfigUpdate,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
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
    if "llm_config" in body.model_fields_set:
        config.llm_config = (
            body.llm_config.model_dump()
            if body.llm_config is not None
            else None
        )
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
    return APIResponse.success(
        data=FestivalMemoryConfigInDB.model_validate(config)
    )


@router.post(
    "/festival-memory-extraction/run",
    response_model=APIResponse[FestivalMemoryExtractionRunResponse],
    summary="立即执行节日记忆抽取",
)
async def run_festival_memory_extraction(
    body: FestivalMemoryExtractionRunRequest,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: UserSchema = Depends(deps.get_current_superuser),
) -> Any:
    if body.config_id is not None:
        result = await db.execute(
            select(FestivalMemoryConfig).where(
                FestivalMemoryConfig.id == body.config_id
            )
        )
        config = result.scalar_one_or_none()
        if not config:
            raise HTTPException(
                status_code=404, detail="Configuration not found"
            )
        festival_name = config.festival_name
        festival_date = config.festival_date
        prompt = config.prompt
        tz_str = getattr(config, "timezone", "UTC") or "UTC"
        min_rounds = (
            getattr(config, "min_rounds_in_window", None)
            or festival_memory_service.DEFAULT_MIN_ROUNDS_IN_WINDOW
        )
        raw_llm = getattr(config, "llm_config", None)
        llm_config = (
            LLMConfig.model_validate(raw_llm) if raw_llm is not None else None
        )
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
        llm_config = None

    read_db_url = festival_memory_service.resolve_sync_read_db_url(
        prefer_replica_read=True
    )
    pairs = await asyncio.to_thread(
        festival_memory_service.get_pairs_with_min_rounds_in_window_sync,
        festival_date,
        read_db_url,
        min_rounds,
        tz_str,
    )
    total = len(pairs)
    success = 0
    failed = 0
    for user_id, agent_id in pairs:
        ok = await festival_memory_service.extract_festival_and_save(
            db,
            user_id,
            agent_id,
            festival_name,
            festival_date,
            prompt,
            llm_config=llm_config,
            prefer_replica_read=True,
        )
        if ok:
            success += 1
        else:
            failed += 1
    logger.info(
        f"节日记忆抽取完成 festival={festival_name} total={total} success={success} failed={failed}"
    )
    return APIResponse.success(
        data=FestivalMemoryExtractionRunResponse(
            total_pairs=total,
            success_count=success,
            failed_count=failed,
        )
    )
