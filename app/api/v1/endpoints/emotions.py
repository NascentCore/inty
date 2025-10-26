from fastapi import APIRouter, Depends
from loguru import logger

from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.schemas.response import APIResponse
from app.schemas.emotion import (
    EmotionListResponse,
    EmotionMappingResponse,
    EmotionMappingSetRequest,
    EmotionSelectRequest,
    EmotionSelectResult,
)
from app.services import emotion_service


router = APIRouter(prefix="/emotions", route_class=LoggerRoute)


@router.get("/list", response_model=APIResponse[EmotionListResponse])
async def list_emotions(_: deps.CurrentUser = Depends(deps.get_current_active_user)):
    emotions = emotion_service.list_emotions()
    return APIResponse.success(EmotionListResponse(emotions=emotions))


@router.get("/mapping", response_model=APIResponse[EmotionMappingResponse])
async def get_mapping(_: deps.CurrentUser = Depends(deps.get_current_active_user)):
    mapping = emotion_service.get_mapping()
    return APIResponse.success(EmotionMappingResponse(mapping=mapping))


@router.post("/mapping", response_model=APIResponse[EmotionMappingResponse])
async def set_mapping(
    body: EmotionMappingSetRequest,
    _: deps.CurrentUser = Depends(deps.get_current_active_user),
):
    try:
        mapping = emotion_service.set_mapping(body.mapping, replace=body.replace)
        return APIResponse.success(EmotionMappingResponse(mapping=mapping))
    except ValueError as e:
        logger.warning(f"Invalid mapping: {e}")
        return APIResponse.error(str(e))


@router.post("/select", response_model=APIResponse[EmotionSelectResult])
async def select_emotion(
    body: EmotionSelectRequest,
    _: deps.CurrentUser = Depends(deps.get_current_active_user),
):
    selected = emotion_service.select_emotion_with_gemini(
        emotion_service.EmotionSelectInput(
            utterance=body.utterance,
            context=body.context,
            character_state=body.character_state,
        )
    )
    image_url = emotion_service.get_image_for_emotion(selected)
    return APIResponse.success(EmotionSelectResult(emotion=selected, image_url=image_url))
