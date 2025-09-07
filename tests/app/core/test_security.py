from datetime import timedelta, datetime
from jose import jwt

from app.core import security


def test_zero_delta_respected():
    token = security.create_access_token("user", expires_delta=timedelta(seconds=0))
    exp = jwt.get_unverified_claims(token)['exp']
    diff = exp - datetime.utcnow().timestamp()
    assert -1 <= diff <= 1


def test_default_expiration_when_none():
    token = security.create_access_token("user")
    exp = jwt.get_unverified_claims(token)['exp']
    diff = exp - datetime.utcnow().timestamp()
    # approximately 10080 minutes (7 days) from config.py
    assert 604790 <= diff <= 604810
