from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
import logging
import traceback
import httpx
import uuid
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app import schemas
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.services.auth_service import register_user, get_user_by_phone, create_guest_user
from app.models import User
from app.models.user import AuthType

logger = logging.getLogger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.app.api_v1_prefix}/auth/login")


@router.post("/register", response_model=schemas.Token)
async def register(
    *,
    db: Session = Depends(get_db),
    user_in: schemas.UserCreate,
) -> Any:
    """注册新用户"""
    try:
        # 处理手机号注册
        user = register_user(db, user_in)
        access_token = create_access_token(user.id)
        return {
            "code": 200,
            "message": "success",
            "data": {
                "token": access_token,
                "user": {
                    "id": user.id,
                    "nickname": user.nickname,
                    "avatar": user.avatar,
                    "email": user.email,
                    "phone": user.phone,
                    "auth_type": user.auth_type,
                    "is_new_user": True
                }
            }
        }
    except Exception as e:
        logger.error(f"注册失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.post("/login", response_model=schemas.Token)
def login(
    *,
    db: Session = Depends(get_db),
    login_in: schemas.LoginRequest,
) -> Any:
    """
    用户登录
    """
    user = get_user_by_phone(db, login_in.phone)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or verification code",
        )
    # TODO: 验证验证码
    access_token = create_access_token(user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/guest", response_model=schemas.Token)
def create_guest(
    *,
    db: Session = Depends(get_db),
    guest_in: schemas.GuestRequest,
) -> Any:
    """
    创建游客账号
    """
    try:
        logger.info(f"开始创建游客账号: device_id={guest_in.device_id}, system_language={guest_in.system_language}")
        user = create_guest_user(
            db,
            device_id=guest_in.device_id,
            system_language=guest_in.system_language
        )
        logger.info(f"游客账号创建成功: user_id={user.id}")
        access_token = create_access_token(user.id)
        logger.info(f"访问令牌创建成功: user_id={user.id}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
    except Exception as e:
        logger.error(f"创建游客账号失败: error={str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/google/login", response_model=schemas.TokenResponse)
async def google_login(
    *,
    db: Session = Depends(get_db),
    login_in: schemas.GoogleAuthRequest,
) -> Any:
    """Google登录"""
    try:
        # 验证 Google ID Token
        idinfo = id_token.verify_oauth2_token(
            login_in.id_token, 
            google_requests.Request(), 
            settings.google_oauth.client_id
        )

        # 验证发行者
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Invalid token issuer')

        # 检查用户是否已存在
        existing_user = db.query(User).filter(
            User.google_id == idinfo["sub"]
        ).first()
        
        if existing_user:
            # 如果用户已存在，直接返回 token
            access_token = create_access_token(existing_user.id)
            return {
                "code": 200,
                "message": "success",
                "data": {
                    "token": access_token,
                    "user": {
                        "id": existing_user.id,
                        "nickname": existing_user.nickname,
                        "avatar": existing_user.avatar,
                        "email": existing_user.email,
                        "phone": existing_user.phone,
                        "auth_type": existing_user.auth_type,
                        "is_new_user": False
                    }
                }
            }
        
        # 创建新用户
        user_id = str(uuid.uuid4())
        new_user = User(
            id=user_id,
            auth_type=AuthType.GOOGLE,
            google_id=idinfo["sub"],
            nickname=idinfo.get("name", f"User_{user_id[:8]}"),
            avatar=idinfo.get("picture"),
            email=idinfo.get("email"),
            system_language=login_in.user_info.system_language if login_in.user_info else "en",
            is_active=True
        )
        
        if login_in.user_info:
            new_user.gender = login_in.user_info.gender
            new_user.age_group = login_in.user_info.age_group
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # 生成 token
        access_token = create_access_token(new_user.id)
        return {
            "code": 200,
            "message": "success",
            "data": {
                "token": access_token,
                "user": {
                    "id": new_user.id,
                    "nickname": new_user.nickname,
                    "avatar": new_user.avatar,
                    "email": new_user.email,
                    "phone": new_user.phone,
                    "auth_type": new_user.auth_type,
                    "is_new_user": True
                }
            }
        }
    except ValueError as e:
        logger.error(f"Google登录失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=400,
            detail="Invalid Google ID token"
        )
    except Exception as e:
        logger.error(f"Google登录失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        ) 