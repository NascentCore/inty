from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.api.v1.endpoints.agents import generate_background
from app.services.global_services import subscription_service
from app.utils import gemini as gemini_utils
from tests.fakes.gemini import FakeGeminiClient


@pytest.mark.asyncio
async def test_text_to_image_resources_store_generation_prompt(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

        async_session_factory = sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )

        user_id = "user-text-image"
        readable_id = "87654321"

        async with async_session_factory() as session:
            user = models.User(
                id=user_id,
                readable_id=readable_id,
                auth_type=models.AuthType.GOOGLE,
                is_active=True,
                is_superuser=False,
                system_language="en",
                created_at=datetime.now(timezone.utc),
            )
            session.add(user)
            await session.commit()

        fake_client = FakeGeminiClient()
        monkeypatch.setattr(gemini_utils, "client", fake_client)
        monkeypatch.setattr(gemini_utils, "get_genai_client", lambda: fake_client)
        monkeypatch.setattr(gemini_utils, "download_from_gcs", fake_client.download_image)

        async def fake_check_image_gen_limit(db, current_user):
            return True, 0, 10

        async def fake_record_usage(db, user_id_arg, feature, count):
            return None

        monkeypatch.setattr(
            subscription_service,
            "check_image_gen_limit",
            fake_check_image_gen_limit,
        )
        monkeypatch.setattr(
            subscription_service,
            "record_usage",
            fake_record_usage,
        )

        request_prompt = "A friendly companion smiling at the camera"
        request = schemas.TextToImageRequest(
            prompt=request_prompt,
            count=2,
            enhance_prompt=False,
        )
        current_user = schemas.User(
            id=user_id,
            readable_id=readable_id,
            auth_type=models.AuthType.GOOGLE.value,
            is_active=True,
            is_superuser=False,
            created_at=datetime.now(timezone.utc),
        )

        async with async_session_factory() as session:
            response = await generate_background(request, db=session, current_user=current_user)

        assert response.code == 200
        assert response.data is not None
        assert response.data["count"] == 2
        urls = response.data["urls"]
        assert len(urls) == 2

        async with async_session_factory() as session:
            result = await session.execute(select(models.Resource))
            resources = result.scalars().all()

        assert len(resources) == 2
        stored_urls = sorted(resource.url for resource in resources)
        assert stored_urls == sorted(urls)

        stored_prompts = {
            resource.resource_metadata.get("generation_prompt") for resource in resources
        }
        assert stored_prompts == {request_prompt}

    finally:
        await engine.dispose()
