import firebase_admin
from firebase_admin import credentials
from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml


debug = global_config_loaded_from_config_yaml.app.debug


def init_firebase() -> None:
    """初始化 Firebase Admin SDK

    从 settings 加载 Firebase 凭证并初始化 SDK
    """
    try:
# 获取 Firebase 配置
        if not global_config_loaded_from_config_yaml.firebase.service_account_path:
            raise ValueError("Firebase service account path not configured")
# 初始化 Firebase 管理员 SDK
        cred = credentials.Certificate(
            global_config_loaded_from_config_yaml.firebase.service_account_path
        )
# firebase_admin。初始化应用程序（信用）

        firebase_admin.initialize_app(cred, {"projectId": "alien-paratext-461204-i9"})

        logger.info("Firebase Admin SDK initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")
        if debug:
            logger.error("Failure ignored in debug mode")
        else:
            raise e
