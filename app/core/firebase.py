import firebase_admin
from firebase_admin import credentials
from loguru import logger

from app.core.config import settings


def init_firebase() -> None:
    """初始化 Firebase Admin SDK
    
    从 settings 加载 Firebase 凭证并初始化 SDK
    """
    try:
        # 获取 Firebase 配置
        if not settings.firebase.service_account_path:
            raise ValueError("Firebase service account path not configured")
            
        # 初始化 Firebase Admin SDK
        cred = credentials.Certificate(settings.firebase.service_account_path)
        # firebase_admin.initialize_app(cred)

        firebase_admin.initialize_app(cred, {
            "projectId": "alien-paratext-461204-i9"
        })

        logger.info("Firebase Admin SDK initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")
        raise
