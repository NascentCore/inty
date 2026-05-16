from datetime import datetime, timedelta

from jose import jwt

from app.core import security


def test_zero_delta_respected():
    token = security.create_access_token("user", expires_delta=timedelta(seconds=0))
    exp = jwt.get_unverified_claims(token)['exp']
    diff = exp - datetime.utcnow().timestamp()
    # ``exp`` is ``int(expire.timestamp())`` while ``expire`` and this ``utcnow()`` are two samples;
    # across a second boundary ``diff`` can dip slightly below -1 without a logic bug (CI saw ~-1.00008).
    assert -2 <= diff <= 1


def test_default_expiration_when_none():
    token = security.create_access_token("user")
    exp = jwt.get_unverified_claims(token)['exp']
    diff = exp - datetime.utcnow().timestamp()
    # approximately 10080 minutes (7 days) from config.py
    # Allow for small time differences due to test execution time and system clock variations
    assert 604000 <= diff <= 610000
