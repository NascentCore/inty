import traceback
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api import deps
from app.api.tags import WEB_APP_TAG, NOT_USED_TAG
from app.api.utils.logger_route import LoggerRoute
from app.services.settings_service import (
    create_settings,
    get_settings,
    update_settings,
)

from loguru import logger
from app.schemas.settings import Settings as SettingsSchema
from app.schemas.settings import SettingsCreate
from app.schemas.settings import SettingsUpdate
from app.schemas.user import User as UserSchema

router = APIRouter(prefix="/settings", route_class=LoggerRoute)


@router.get(
    "/", response_model=SettingsSchema, tags=[WEB_APP_TAG, NOT_USED_TAG]
)
def get_settings_endpoint(
    db: Session = Depends(deps.get_db),
    current_user: UserSchema = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user settings
    """
    try:
        logger.debug(f"Getting user settings: user_id={current_user.id}")
        settings = get_settings(db, user_id=current_user.id)
        if not settings:
            logger.debug(f"User settings not found: user_id={current_user.id}")
            raise HTTPException(status_code=404, detail="Settings not found")
        logger.debug(
            f"Successfully retrieved user settings: user_id={current_user.id}"
        )
        return settings
    except SQLAlchemyError as e:
        logger.error(
            f"Failed to get user settings: user_id={current_user.id}, error={str(e)}"
        )
        logger.error(f"Error stack: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        logger.error(
            f"Unknown error occurred while getting user settings: user_id={current_user.id}, error={str(e)}"
        )
        logger.error(f"Error stack: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/", response_model=SettingsSchema, tags=[WEB_APP_TAG, NOT_USED_TAG]
)
def update_settings_endpoint(
    *,
    db: Session = Depends(deps.get_db),
    settings_in: SettingsUpdate,
    current_user: UserSchema = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update current user settings
    """
    try:
        logger.debug(
            f"Updating user settings: user_id={current_user.id}, settings={settings_in.dict()}"
        )
        settings = get_settings(db, user_id=current_user.id)
        if not settings:
            # Create new settings
            settings_create = SettingsCreate(
                language=settings_in.language or "en",
                voice_enabled=(
                    settings_in.voice_enabled
                    if settings_in.voice_enabled is not None
                    else True
                ),
            )
            logger.debug(
                f"Creating new user settings: user_id={current_user.id}, settings={settings_create.dict()}"
            )
            settings = create_settings(
                db, settings_in=settings_create, user_id=current_user.id
            )
        else:
            logger.debug(
                f"Updating existing user settings: user_id={current_user.id}, settings={settings_in.dict()}"
            )
            settings = update_settings(
                db, db_settings=settings, settings_in=settings_in
            )
        logger.debug(
            f"Successfully updated user settings: user_id={current_user.id}"
        )
        return settings
    except SQLAlchemyError as e:
        logger.error(
            f"Failed to update user settings: user_id={current_user.id}, error={str(e)}"
        )
        logger.error(f"Error stack: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        logger.error(
            f"Unknown error occurred while updating user settings: user_id={current_user.id}, error={str(e)}"
        )
        logger.error(f"Error stack: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")
