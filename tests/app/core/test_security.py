from datetime import timedelta
import time

from jose import jwt

from app.core import security


def test_zero_delta_respected():
    token = security.create_access_token(
        "user", expires_delta=timedelta(seconds=0)
    )
    exp = jwt.get_unverified_claims(token)["exp"]
    diff = exp - time.time()
    assert -2 <= diff <= 1


def test_default_expiration_when_none():
    token = security.create_access_token("user")
    exp = jwt.get_unverified_claims(token)["exp"]
    diff = exp - time.time()
    # approximately 10080 minutes (7 days) from config.py
    # Allow for small time differences due to test execution time and system clock variations
    assert 604000 <= diff <= 610000


def test_local_ops_bearer_expires_delta_at_least_min_lifetime() -> None:
    delta = security.local_ops_bearer_expires_delta()
    assert delta >= security.LOCAL_OPS_BEARER_MIN_LIFETIME


def test_existing_bearer_token_usable_requires_min_lifetime_remaining() -> None:
    user_id = "user-testing"
    config = security.global_config_loaded_from_config_yaml
    now_ts = int(time.time())
    token_soon = jwt.encode(
        {"exp": now_ts + 3600, "sub": user_id},
        config.security.secret_key,
        algorithm=config.security.algorithm,
    )
    token_ok = jwt.encode(
        {
            "exp": now_ts
            + int(security.LOCAL_OPS_BEARER_MIN_LIFETIME.total_seconds())
            + 3600,
            "sub": user_id,
        },
        config.security.secret_key,
        algorithm=config.security.algorithm,
    )
    token_wrong_user = jwt.encode(
        {
            "exp": now_ts
            + int(security.LOCAL_OPS_BEARER_MIN_LIFETIME.total_seconds())
            + 3600,
            "sub": "user-someone-else",
        },
        config.security.secret_key,
        algorithm=config.security.algorithm,
    )
    assert security.existing_bearer_token_usable(token_soon, user_id) is False
    assert security.existing_bearer_token_usable(token_ok, user_id) is True
    assert (
        security.existing_bearer_token_usable(token_wrong_user, user_id)
        is False
    )
    assert security.existing_bearer_token_usable("not-a-jwt", user_id) is False
