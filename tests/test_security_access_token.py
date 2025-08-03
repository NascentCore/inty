import sys
import types
from datetime import timedelta, datetime
from jose import jwt
import importlib


def get_security_module():
    # Create stub config module with minimal security settings
    config_module = types.ModuleType('config')
    security_settings = types.SimpleNamespace(
        secret_key='secret', algorithm='HS256', access_token_expire_minutes=60
    )
    config_module.settings = types.SimpleNamespace(security=security_settings)
    sys.modules['app.core.config'] = config_module
    import app.core.security as security
    return importlib.reload(security)


def test_zero_delta_respected():
    security = get_security_module()
    token = security.create_access_token('user', expires_delta=timedelta(seconds=0))
    exp = jwt.get_unverified_claims(token)['exp']
    diff = exp - datetime.utcnow().timestamp()
    assert -1 <= diff <= 1


def test_default_expiration_when_none():
    security = get_security_module()
    token = security.create_access_token('user')
    exp = jwt.get_unverified_claims(token)['exp']
    diff = exp - datetime.utcnow().timestamp()
    # approximately 60 minutes
    assert 3590 <= diff <= 3610
