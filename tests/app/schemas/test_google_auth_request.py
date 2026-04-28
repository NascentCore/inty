# GoogleAuthRequest: id_token-only vs email+password are mutually exclusive

import pytest
from pydantic import ValidationError

from app.schemas.auth import GoogleAuthRequest


def test_id_token_only_ok():
    GoogleAuthRequest.model_validate({"id_token": "google-jwt-here"})


def test_id_token_with_request_metadata_ok():
    GoogleAuthRequest.model_validate(
        {"id_token": "t", "request_id": "req-1"},
    )


def test_email_and_password_only_ok():
    GoogleAuthRequest.model_validate(
        {"email": "a@example.com", "password": "s3cret"},
    )


def test_mixed_id_token_with_email_and_password_rejected():
    with pytest.raises(ValidationError) as exc_info:
        GoogleAuthRequest.model_validate(
            {
                "id_token": "x",
                "email": "a@example.com",
                "password": "p",
            },
        )
    errs = exc_info.value.errors()
    assert any(e.get("type") == "incompatible_auth" for e in errs)


def test_mixed_id_token_with_email_only_rejected():
    with pytest.raises(ValidationError) as exc_info:
        GoogleAuthRequest.model_validate(
            {"id_token": "x", "email": "a@example.com"},
        )
    assert any(e.get("type") == "incompatible_auth" for e in exc_info.value.errors())
