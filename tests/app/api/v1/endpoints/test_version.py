# CREATED_BY_AGENT: Version check API tests for last_android_app_version_code persistence.
# Test design: straightforward HTTP via TestClient; DB verification via global config database URL.

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api import deps
from app.api.v1.endpoints import version
from app.core.config import global_config_loaded_from_config_yaml
from app.core.uuid import get_new_user_id
from app.models.user import AuthType, User
from app.schemas.user import User as UserSchema
from app.schemas.version import VersionReminderAction


def _make_user(
    user_id: str = "user-1",
    *,
    is_superuser: bool = False,
) -> UserSchema:
    """Create a minimal user schema instance for dependency overrides."""
    return UserSchema(
        id=user_id,
        readable_id=f"readable-{user_id}",
        auth_type=AuthType.GOOGLE.value,
        is_active=True,
        is_superuser=is_superuser,
        created_at=datetime.now(timezone.utc),
    )


class FakeGooglePlayService:
    """Fake for version check; no real Google Play call."""

    def __init__(self):
        self.last_call: int | None = None

    def check_version_requirement(self, version_code: int):
        self.last_call = version_code
        return {
            "current_version": str(version_code),
            "latest_version": "200",
            "latest_version_code": 200,
            "update_required": False,
            "force_update": False,
            "force_update_reasons": [],
            "minimum_version": "100",
            "changelog": "Minor fixes",
            "download_url": "https://play.google.com/store/apps/details?id=com.ai.inty",
            "message": "ok",
            "error": None,
            "reminder_action": VersionReminderAction.POP_UP_REMINDER.value,
        }


@pytest.fixture
def version_app(monkeypatch: pytest.MonkeyPatch):
    """Provide a FastAPI app mounting only the version router (no real DB)."""
    app = FastAPI()
    app.include_router(version.router, prefix="/api/v1")

    async def override_current_active_user():
        return _make_user()

    async def override_get_async_db():
        yield None

    app.dependency_overrides[deps.get_current_active_user] = (
        override_current_active_user
    )
    app.dependency_overrides[deps.get_async_db] = override_get_async_db

    fake_service = FakeGooglePlayService()
    app.state.fake_google_play_service = fake_service
    monkeypatch.setattr(version, "google_play_service", fake_service)

    try:
        yield app
    finally:
        app.dependency_overrides.clear()


def test_version_check_returns_google_play_result(version_app: FastAPI):
    """Ensure /api/v1/version/check returns the payload from Google Play service."""
    headers = {
        "appVersionCode": "150",
        "appVersionName": "1.5.0",
    }

    with TestClient(version_app) as client:
        response = client.post("/api/v1/version/check", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["current_version"] == "150"
    assert body["data"]["latest_version"] == "200"
    assert (
        body["data"]["reminder_action"] == VersionReminderAction.POP_UP_REMINDER.value
    )
    assert version_app.state.fake_google_play_service.last_call == 150


@pytest.fixture
def db_session():
    """Sync DB session using config.yaml database.url; used to prepare data and assert."""
    engine = create_engine(global_config_loaded_from_config_yaml.database.url)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def version_app_with_real_db(db_session, monkeypatch: pytest.MonkeyPatch):
    """
    App with version router, real DB (get_async_db overridden with a per-fixture async
    engine so persistence works across both tests), fake Google Play, and a test user
    in the DB. Yields (app, user_id, db_session).
    """
    user_id = get_new_user_id()
    device_id = f"test-version-{uuid.uuid4().hex}"
    user = User(
        id=user_id,
        auth_type=AuthType.GOOGLE,
        device_id=device_id,
        last_android_app_version_code=None,
    )
    db_session.add(user)
    db_session.commit()

    _db = global_config_loaded_from_config_yaml.database
    async_engine = create_async_engine(
        str(_db.async_url),
        pool_size=1,
        max_overflow=0,
    )
    AsyncSessionLocalTest = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_async_db():
        async with AsyncSessionLocalTest() as session:
            yield session

    app = FastAPI()
    app.include_router(version.router, prefix="/api/v1")

    async def override_current_active_user():
        return _make_user(user_id=user_id)

    app.dependency_overrides[deps.get_current_active_user] = (
        override_current_active_user
    )
    app.dependency_overrides[deps.get_async_db] = override_get_async_db

    fake_service = FakeGooglePlayService()
    monkeypatch.setattr(version, "google_play_service", fake_service)

    try:
        yield app, user_id, db_session
    finally:
        app.dependency_overrides.clear()
        db_session.delete(user)
        db_session.commit()
        # Per-fixture async engine; skip dispose() in sync teardown (event loop closed).


@pytest.mark.noci
def test_version_check_sets_last_android_app_version_code_when_null(
    version_app_with_real_db,
):
    """When last_android_app_version_code is NULL, after version check it is set to the provided version code."""
    app, user_id, db_session = version_app_with_real_db
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/version/check",
            headers={"appVersionCode": "100"},
        )
    assert response.status_code == 200
    row = db_session.query(User).filter(User.id == user_id).first()
    assert row is not None
    assert row.last_android_app_version_code == 100


@pytest.mark.noci
def test_version_check_updates_last_android_app_version_code_when_not_null(
    version_app_with_real_db,
):
    """When last_android_app_version_code is not null, after version check it is updated to the provided version code."""
    app, user_id, db_session = version_app_with_real_db
    user = db_session.query(User).filter(User.id == user_id).first()
    user.last_android_app_version_code = 50
    db_session.commit()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/version/check",
            headers={"appVersionCode": "200"},
        )
    assert response.status_code == 200
    db_session.expire_all()
    row = db_session.query(User).filter(User.id == user_id).first()
    assert row is not None
    assert row.last_android_app_version_code == 200
