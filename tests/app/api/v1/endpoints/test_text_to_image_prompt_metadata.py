from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import delete, select

from app import models, schemas
from app.api.v1.endpoints.agents import generate_background
from app.db.session import AsyncSessionLocal
from app.services.global_services import subscription_service
from app.utils import gemini as gemini_utils
from tests.fakes.gemini import FakeGeminiClient


@pytest.mark.asyncio
async def test_text_to_image_resources_store_generation_prompt(monkeypatch: pytest.MonkeyPatch):
    user_id = f"user-text-image-{uuid.uuid4().hex}"
    readable_id = uuid.uuid4().hex[:8]
    urls: list[str] = []

    try:
        async with AsyncSessionLocal() as session:
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

        async with AsyncSessionLocal() as session:
            response = await generate_background(request, db=session, current_user=current_user)

        assert response.code == 200
        assert response.data is not None
        assert response.data["count"] == 2
        urls = list(response.data["urls"])
        assert len(urls) == 2

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(models.Resource).where(models.Resource.url.in_(urls))
            )
            resources = result.scalars().all()

        assert len(resources) == len(urls)
        stored_urls = sorted(resource.url for resource in resources)
        assert stored_urls == sorted(urls)

        stored_prompts = {
            resource.resource_metadata.get("generation_prompt") for resource in resources
        }
        assert stored_prompts == {request_prompt}

    finally:
        async with AsyncSessionLocal() as session:
            if urls:
                await session.execute(delete(models.Resource).where(models.Resource.url.in_(urls)))
            await session.execute(delete(models.User).where(models.User.id == user_id))
            await session.commit()
