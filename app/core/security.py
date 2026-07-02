from datetime import timedelta
import time
from typing import Any, Optional, Union

import bcrypt
from jose import JWTError, jwt

from app.core.config import global_config_loaded_from_config_yaml

# Minimum JWT lifetime for local Ops bearer files (``init_admin_user --token-file``);
# also the minimum time-remaining threshold below which a cached token is rotated
# instead of reused, so a reused token is never weaker than a freshly minted one.
LOCAL_OPS_BEARER_MIN_LIFETIME = timedelta(hours=2)


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """创建访问令牌。

    expires_delta 为 `None` 时使用配置中的默认过期时间。
    传入 `timedelta(0)` 可使令牌立即过期。
    """
    if expires_delta is not None:
        expire_ts = int(time.time()) + int(expires_delta.total_seconds())
    else:
        expire_ts = int(time.time()) + int(
            timedelta(
                minutes=global_config_loaded_from_config_yaml.security.access_token_expire_minutes
            ).total_seconds()
        )

    to_encode = {
        "exp": expire_ts,
        "sub": str(subject),
    }
    encoded_jwt = jwt.encode(
        to_encode,
        global_config_loaded_from_config_yaml.security.secret_key,
        algorithm=global_config_loaded_from_config_yaml.security.algorithm,
    )
    return encoded_jwt


def local_ops_bearer_expires_delta() -> timedelta:
    """JWT lifetime for local Ops bearer files; never below ``LOCAL_OPS_BEARER_MIN_LIFETIME``."""
    configured = timedelta(
        minutes=global_config_loaded_from_config_yaml.security.access_token_expire_minutes
    )
    if configured >= LOCAL_OPS_BEARER_MIN_LIFETIME:
        return configured
    return LOCAL_OPS_BEARER_MIN_LIFETIME


def existing_bearer_token_usable(token: str, user_id: str) -> bool:
    """True when ``token`` decodes for ``user_id`` with ``LOCAL_OPS_BEARER_MIN_LIFETIME`` left."""
    assert token != ""
    assert user_id != ""
    try:
        payload = jwt.decode(
            token,
            global_config_loaded_from_config_yaml.security.secret_key,
            algorithms=[
                global_config_loaded_from_config_yaml.security.algorithm
            ],
        )
    except JWTError:
        return False
    if str(payload.get("sub") or "") != str(user_id):
        return False
    exp = payload.get("exp")
    if exp is None:
        return False
    remaining_seconds = int(exp) - int(time.time())
    return remaining_seconds >= int(
        LOCAL_OPS_BEARER_MIN_LIFETIME.total_seconds()
    )


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
