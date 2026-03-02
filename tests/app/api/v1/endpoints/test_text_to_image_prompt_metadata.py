from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from app import models, schemas
from app.api.v1.endpoints import agents as agents_endpoint
from app.api.v1.endpoints.agents import generate_background
from app.db.session import AsyncSessionLocal
from app.external_services.fakes.gemini import FakeGeminiClient
from app.services.global_services import subscription_service
from app.utils import gemini as gemini_utils


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
                gender=models.Gender.FEMALE,
                is_superuser=False,
                system_language="en",
                created_at=datetime.now(timezone.utc),
            )
            session.add(user)
            await session.commit()

        fake_client = FakeGeminiClient()
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
            gender=models.Gender.FEMALE,
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


class _FakeFalImage:
    def __init__(
        self, *, url: str, mime_type: str, width: int | None = None, height: int | None = None
    ) -> None:
        self.url = url
        self.mime_type = mime_type
        self.width = width
        self.height = height


class _FakeFalResult:
    def __init__(self, images: list[_FakeFalImage]) -> None:
        self.images = images


@pytest.mark.asyncio
async def test_generate_with_fal_ai_accepts_z_image_turbo_model(
    monkeypatch: pytest.MonkeyPatch,
):
    called_models: list[str] = []

    def fake_generate_text_to_image(fal_request):
        called_models.append(fal_request.model)
        assert fal_request.negative_prompt == "blurry"
        return _FakeFalResult(
            images=[
                _FakeFalImage(
                    url="https://fal.example/generated/1.png",
                    mime_type="image/png",
                    width=1024,
                    height=1365,
                ),
                _FakeFalImage(
                    url="https://fal.example/generated/2.png",
                    mime_type="image/png",
                    width=1024,
                    height=1365,
                ),
            ]
        )

    async def fake_download_and_upload_to_gcs(
        *, url: str, gcs_bucket: str, gcs_path: str, content_type: str | None = None
    ):
        _ = (url, content_type)
        return f"https://storage.googleapis.com/{gcs_bucket}/{gcs_path}", 2048

    monkeypatch.setattr(
        agents_endpoint,
        "generate_text_to_image",
        fake_generate_text_to_image,
    )
    monkeypatch.setattr(
        agents_endpoint,
        "_download_and_upload_to_gcs",
        fake_download_and_upload_to_gcs,
    )

    generated_images, gcs_urls, rai_reasons, gcs_url_to_img_dict = (
        await agents_endpoint._generate_with_fal_ai(
            model="fal-ai/z-image/turbo",
            prompt="A vivid portrait with soft warm lighting",
            negative_prompt="blurry",
            num_images=2,
            gcs_bucket="inty-test",
            gcs_base_path="backgrounds/test-user/req-1",
        )
    )

    assert called_models == ["fal-ai/z-image/turbo"]
    assert len(generated_images) == 2
    assert len(gcs_urls) == 2
    assert rai_reasons == []
    assert set(gcs_urls) == set(gcs_url_to_img_dict.keys())
