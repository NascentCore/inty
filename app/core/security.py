from datetime import datetime, timedelta
from typing import Any, Optional, Union

import bcrypt
from jose import jwt

from app.core.config import global_config_loaded_from_config_yaml


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """创建访问令牌。

    expires_delta 为 `None` 时使用配置中的默认过期时间。
    传入 `timedelta(0)` 可使令牌立即过期。
    """
    if expires_delta is not None:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=global_config_loaded_from_config_yaml.security.access_token_expire_minutes
        )

    to_encode = {
        "exp": int(expire.timestamp()),  # 转换为 Unix 时间戳
        "sub": str(subject),
    }
    encoded_jwt = jwt.encode(
        to_encode,
        global_config_loaded_from_config_yaml.security.secret_key,
        algorithm=global_config_loaded_from_config_yaml.security.algorithm,
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """
    获取密码哈希
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )
