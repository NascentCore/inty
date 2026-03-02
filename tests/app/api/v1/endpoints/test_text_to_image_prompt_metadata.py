from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from app import models, schemas
from app.api.v1.endpoints import agents as agents_endpoint
from app.api.v1.endpoints.agents import generate_background
from app.core.images.types import GeneratedImageProcessResult
from app.db.session import AsyncSessionLocal
from app.external_services.fakes.gemini import FakeGeminiClient
from app.services.global_services import subscription_service
from app.utils import gemini as gemini_utils
from app.utils.image import ImageFormat, ImageSize


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


@pytest.mark.asyncio
@pytest.mark.parametrize("model_id", ["fal-ai/z-image/turbo", "fal/z-image/turbo"])
async def test_generate_with_fal_ai_accepts_z_image_turbo_model(
    monkeypatch: pytest.MonkeyPatch,
    model_id: str,
):
    called_bases: list[str] = []
    called_prompts: list[str] = []

    async def fake_z_image_turbo(args, gcs_uri_base):
        called_bases.append(gcs_uri_base)
        called_prompts.append(args.prompt)
        assert args.num_images == 2
        assert args.image_size == "portrait_4_3"
        assert args.output_format == ImageFormat.PNG
        return [
            GeneratedImageProcessResult(
                size=ImageSize(width=1024, height=1365),
                format=ImageFormat.PNG,
                raw_data=b"fake-png-bytes-1",
                raw_data_total_bytes=16,
                gcs_uri=f"gs://inty-test/{gcs_uri_base}/fake_1.png",
                gcs_http_url=f"https://storage.googleapis.com/inty-test/{gcs_uri_base}/fake_1.png",
                generated_at=datetime.now(timezone.utc),
                raw_response_from_provider={"images": [{"url": "data:image/png;base64,fake1"}]},
            ),
            GeneratedImageProcessResult(
                size=ImageSize(width=1024, height=1365),
                format=ImageFormat.PNG,
                raw_data=b"fake-png-bytes-2",
                raw_data_total_bytes=16,
                gcs_uri=f"gs://inty-test/{gcs_uri_base}/fake_2.png",
                gcs_http_url=f"https://storage.googleapis.com/inty-test/{gcs_uri_base}/fake_2.png",
                generated_at=datetime.now(timezone.utc),
                raw_response_from_provider={"images": [{"url": "data:image/png;base64,fake2"}]},
            ),
        ]
    def fail_generate_text_to_image(_):
        raise AssertionError("z-image/turbo should use app/core/images/fal.py API")

    monkeypatch.setattr(
        agents_endpoint,
        "z_image_turbo",
        fake_z_image_turbo,
    )
    monkeypatch.setattr(
        agents_endpoint,
        "generate_text_to_image",
        fail_generate_text_to_image,
    )

    generated_images, gcs_urls, rai_reasons, gcs_url_to_img_dict = (
        await agents_endpoint._generate_with_fal_ai(
            model=model_id,
            prompt="A vivid portrait with soft warm lighting",
            negative_prompt="blurry",
            num_images=2,
            gcs_bucket="inty-test",
            gcs_base_path="backgrounds/test-user/req-1",
        )
    )

    assert called_bases == ["backgrounds/test-user/req-1"]
    assert called_prompts == ["A vivid portrait with soft warm lighting"]
    assert len(generated_images) == 2
    assert len(gcs_urls) == 2
    assert rai_reasons == []
    assert set(gcs_urls) == set(gcs_url_to_img_dict.keys())


@pytest.mark.asyncio
async def test_text_to_image_uses_requested_model_for_generation(
    monkeypatch: pytest.MonkeyPatch,
):
    requested_model = "google/imagen-4.0-fast-generate-001"
    called_models: list[str | None] = []

    async def fake_check_image_gen_limit(db, current_user):
        return True, 0, 10

    async def fake_get_user_current_subscription(db, user_id):
        return None

    async def fake_record_usage(db, user_id_arg, feature, count):
        return None

    def fail_select_text_to_image_model(*, user, is_subscribed):
        raise AssertionError("request.model should bypass auto model selection")

    def fake_text_to_image(
        prompt,
        negative_prompt,
        enhanced_prompt,
        gender,
        aspect_ratio,
        gcs_uri_base,
        count,
        model,
    ):
        called_models.append(model)
        assert prompt == "A cinematic portrait, soft studio light"
        assert count == 1
        assert model == requested_model
        return [
            gemini_utils.ImagenGeneratedImage(
                gcs_uri="gs://inty-test/backgrounds/user-model-test/generated-1.jpg",
                size=ImageSize(width=1024, height=1365),
                byte_size=123,
                format=ImageFormat.JPEG,
                rai_filtered_reason=None,
                enhanced_prompt=prompt,
            )
        ]

    async def fake_async_create_image_resource(**kwargs):
        return None

    monkeypatch.setattr(
        subscription_service,
        "check_image_gen_limit",
        fake_check_image_gen_limit,
    )
    monkeypatch.setattr(
        subscription_service,
        "get_user_current_subscription",
        fake_get_user_current_subscription,
    )
    monkeypatch.setattr(
        subscription_service,
        "record_usage",
        fake_record_usage,
    )
    monkeypatch.setattr(
        agents_endpoint,
        "select_text_to_image_model",
        fail_select_text_to_image_model,
    )
    monkeypatch.setattr(
        agents_endpoint,
        "text_to_image",
        fake_text_to_image,
    )
    monkeypatch.setattr(
        agents_endpoint,
        "async_create_image_resource",
        fake_async_create_image_resource,
    )
    monkeypatch.setattr(
        agents_endpoint.image_transform_service,
        "transform_desktop",
        lambda gcs_url: gcs_url,
    )

    request = schemas.TextToImageRequest(
        prompt="A cinematic portrait, soft studio light",
        count=1,
        enhance_prompt=False,
        model=requested_model,
    )
    current_user = schemas.User(
        id=f"user-text-image-model-{uuid.uuid4().hex}",
        readable_id=uuid.uuid4().hex[:8],
        auth_type=models.AuthType.GOOGLE.value,
        gender=models.Gender.FEMALE,
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(timezone.utc),
    )

    response = await generate_background(request, db=object(), current_user=current_user)

    assert response.code == 200
    assert response.data is not None
    assert response.data["count"] == 1
    assert called_models == [requested_model]
