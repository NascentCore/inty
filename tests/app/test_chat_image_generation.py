"""
聊天生图功能集成测试 - 使用 Gemini 2.5 Flash Image 与 Fal（z_image_turbo、seedream）
"""

import asyncio
import datetime
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.core.config import global_config_loaded_from_config_yaml
from app.core.images.types import GeneratedImageProcessResult
from app.external_services.fakes.gemini import FakeGeminiClient
from app.models.agent import AgentStatus, AgentVisibility
from app.models.user import AuthType, Gender
from app.services import chat_history_service
from app.services.image_generation_service import (
    ChatImageGenModelInput,
    _process_inputs_generate_chat_image,
    image_generation_service,
)
from app.utils.image import ImageFormat, ImageSize
from app.utils.models_catalog import (
    NANO_BANANA,
    SEEDREAM_V4_5_EDIT,
    Z_IMAGE_TURBO_IMAGE_TO_IMAGE,
)


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        str(global_config_loaded_from_config_yaml.database.async_url),
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
    )
    async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


class TestImageGenerationService:
    """测试图片生成服务"""

    def test_trace_inputs_include_full_message_content(self):
        """LangSmith tracing 输入应保留完整 message_content，且不再返回 preview 字段。"""
        full_message_content = "x" * 600 + "-tail"
        inputs = {
            "session_id": "session-1",
            "message_id": 123,
            "agent_data": {"id": "agent-1"},
            "model": "gemini-2.5-flash-image",
            "user_id": "user-1",
            "history_count": 5,
            "message_content": full_message_content,
        }

        output = _process_inputs_generate_chat_image(inputs)

        assert output["message_content"] == full_message_content
        assert output["message_content_len"] == len(full_message_content)
        assert "message_content_preview" not in output

    @pytest.mark.asyncio
    async def test_generate_chat_image_by_model_raises_timeout_for_slow_gemini(self):
        """Gemini 路径传入 timeout_seconds 后，慢请求应抛出 TimeoutError。"""

        async def fake_async_generate_images(
            wrapped_client_self,
            model,
            contents,
            gcs_uri_base,
            system_instructions=None,
        ):
            await asyncio.sleep(2)
            result = GeneratedImageProcessResult(
                size=ImageSize(width=64, height=64),
                format=ImageFormat.JPEG,
                raw_data=b"fake-image",
                raw_data_total_bytes=len(b"fake-image"),
                gcs_uri="gs://test-bucket/chat_images/agent-timeout/output.jpg",
                gcs_http_url="https://storage.googleapis.com/test-bucket/chat_images/agent-timeout/output.jpg",
                generated_at=datetime.datetime.now(datetime.timezone.utc),
                raw_response_from_provider=None,
            )
            return [result]

        with patch(
            "app.core.google_genai.wrapped_client.WrappedClient.async_generate_images",
            new=fake_async_generate_images,
        ):
            with pytest.raises(TimeoutError, match="timeout after 1s"):
                await image_generation_service.generate_chat_image_by_model(
                    chat_input=ChatImageGenModelInput(
                        prompt="draw us in a cafe",
                        reference_image_url="https://example.com/reference.jpg",
                        message_history=[],
                        model_id_on_provider=NANO_BANANA.id_on_provider,
                    ),
                    gcs_uri_base="chat_images/agent-timeout",
                    timeout_seconds=1,
                )

    @pytest.mark.asyncio
    async def test_generate_chat_image_by_model_routes_nano_banana_nickname(self):
        """统一函数应支持 nickname，并自动路由到 Gemini 输入格式。"""
        captured = {}

        async def fake_async_generate_images(
            wrapped_client_self,
            model,
            contents,
            gcs_uri_base,
            system_instructions=None,
        ):
            captured["model"] = model
            captured["contents"] = contents
            captured["gcs_uri_base"] = gcs_uri_base
            captured["system_instructions"] = system_instructions
            result = GeneratedImageProcessResult(
                size=ImageSize(width=64, height=64),
                format=ImageFormat.JPEG,
                raw_data=b"fake-image",
                raw_data_total_bytes=len(b"fake-image"),
                gcs_uri="gs://test-bucket/chat_images/agent-nickname/output.jpg",
                gcs_http_url="https://storage.googleapis.com/test-bucket/chat_images/agent-nickname/output.jpg",
                generated_at=datetime.datetime.now(datetime.timezone.utc),
                raw_response_from_provider=None,
            )
            return [result]

        with patch(
            "app.core.google_genai.wrapped_client.WrappedClient.async_generate_images",
            new=fake_async_generate_images,
        ), patch(
            "app.services.image_generation_service.get_genai_client",
            return_value=FakeGeminiClient(),
        ):
            result = await image_generation_service.generate_chat_image_by_model(
                chat_input=ChatImageGenModelInput(
                    prompt="draw us in a cafe",
                    reference_image_url="https://example.com/reference.jpg",
                    message_history=[
                        {"role": "user", "content": "hello"},
                        {"role": "assistant", "content": "hi there"},
                    ],
                    model_id_on_provider=NANO_BANANA.id_on_provider,
                    user_reference_image_url="https://example.com/user-selfie.jpg",
                ),
                gcs_uri_base="chat_images/agent-nickname",
            )

        assert captured["model"] == NANO_BANANA.id_on_provider
        assert captured["contents"][0] == "https://example.com/reference.jpg"
        assert captured["contents"][1] == "https://example.com/user-selfie.jpg"
        assert "draw us in a cafe" in captured["contents"][2]
        assert captured["gcs_uri_base"] == "chat_images/agent-nickname"
        assert result.gcs_uri.startswith("gs://")

    @pytest.mark.asyncio
    async def test_generate_chat_image_by_model_seedream_auto_fill_second_reference(self):
        """Seedream 在无自拍参考图时应自动补齐第二张参考图。"""
        captured = {}

        async def fake_seedream_v4_5_edit(args, gcs_uri_base=None):
            captured["args"] = args
            captured["gcs_uri_base"] = gcs_uri_base
            return self._make_fake_fal_result(gcs_uri_base or "", "seedream")

        with patch(
            "app.services.image_generation_service.seedream_v4_5_edit",
            new=fake_seedream_v4_5_edit,
        ):
            result = await image_generation_service.generate_chat_image_by_model(
                chat_input=ChatImageGenModelInput(
                    prompt="draw a romantic evening",
                    reference_image_url="https://example.com/reference.jpg",
                    message_history=[
                        {"role": "assistant", "content": "let's watch the sunset"},
                    ],
                    model_id_on_provider=SEEDREAM_V4_5_EDIT.id_on_provider,
                ),
                gcs_uri_base="chat_images/agent-seedream",
            )

        args = captured["args"]
        assert args.prompt.startswith("draw a romantic evening")
        assert len(args.image_urls) == 2
        assert args.image_urls[0] == "https://example.com/reference.jpg"
        assert args.image_urls[1] == "https://example.com/reference.jpg"
        assert captured["gcs_uri_base"] == "chat_images/agent-seedream"
        assert result.gcs_uri.startswith("gs://")

    @pytest.mark.asyncio
    async def test_generate_chat_image_for_message_with_gemini(
        self,
        monkeypatch: pytest.MonkeyPatch,
        db_session: AsyncSession,
    ):
        """测试统一入口使用 Gemini 生成聊天图片（真实 DB 读写，仅 mock 外部服务）。"""
        captured = {"prompt": None}

        unique_suffix = uuid.uuid4().hex[:8]
        gcs_path = f"chat_images/agent-prompt/gemini_test_{unique_suffix}.jpg"

        async def fake_async_generate_images(
            wrapped_client_self,
            model,
            contents,
            gcs_uri_base,
            system_instructions=None,
        ):
            captured["prompt"] = contents[-1]
            result = GeneratedImageProcessResult(
                size=ImageSize(width=64, height=64),
                format=ImageFormat.JPEG,
                raw_data=b"fake-image",
                raw_data_total_bytes=len(b"fake-image"),
                gcs_uri=f"gs://test-bucket/{gcs_path}",
                gcs_http_url=f"https://storage.googleapis.com/test-bucket/{gcs_path}",
                generated_at=datetime.datetime.now(datetime.timezone.utc),
                raw_response_from_provider=None,
            )
            return [result]

        monkeypatch.setattr(
            "app.services.image_generation_service.get_genai_client",
            lambda: FakeGeminiClient(),
        )
        monkeypatch.setattr(
            "app.core.google_genai.wrapped_client.WrappedClient.async_generate_images",
            fake_async_generate_images,
        )
        monkeypatch.setattr(
            "app.core.google_genai.wrapped_client.upload_to_gcs",
            lambda file_data, content_type, bucket_name, path: "https://storage.googleapis.com/{}/{}".format(
                bucket_name, path
            ),
        )
        monkeypatch.setattr(
            "app.services.image_generation_service.image_transform_service.transform_desktop",
            lambda url: "https://cdn.example.com/{}".format(url.split("/", 3)[-1]),
        )
        monkeypatch.setattr(
            "app.services.image_generation_service.get_current_trace_info",
            lambda: (
                "trace-id-for-test",
                "https://smith.langchain.com/o/test/projects/p/test/r/trace-id-for-test",
            ),
        )

        session = db_session
        session_uuid = uuid.uuid4()
        session_id_str = str(session_uuid)
        user_id = "user-{}".format(uuid.uuid4().hex[:8])
        agent_id = "agent-{}".format(uuid.uuid4().hex[:8])

        user = models.User(
            id=user_id,
            readable_id=uuid.uuid4().hex[:8],
            auth_type=AuthType.PHONE,
            nickname="Chat Tester",
            email="test@example.com",
            system_language="en",
            user_photo="gs://test-bucket/user-selfie.jpg",
        )
        session.add(user)
        await session.commit()

        agent = models.Agent(
            id=agent_id,
            readable_id=uuid.uuid4().hex[:8],
            name="Chat Image Agent",
            gender=Gender.FEMALE,
            avatar="https://storage.googleapis.com/test-bucket/avatar.jpg",
            background="https://example.com/background.jpg",
            personality="可爱的女孩",
            scenario="在公园散步",
            intro="intro",
            opening="hello",
            visibility=AgentVisibility.PUBLIC,
            status=AgentStatus.APPROVED,
            creator_id=user_id,
            background_images=[],
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)

        chat_msg = models.ChatHistory(
            session_id=session_uuid,
            message={"type": "user", "data": {"content": "你好"}},
            meta_data=None,
        )
        session.add(chat_msg)
        await session.commit()
        await session.refresh(chat_msg)
        message_id = chat_msg.id

        agent_data = {
            "id": agent_id,
            "personality": agent.personality,
            "scenario": agent.scenario,
            "intro": agent.intro,
            "background": agent.background,
        }
        message_content = "给我画一张图片"

        result = await image_generation_service.generate_chat_image(
            db=session,
            session_id=session_id_str,
            message_id=message_id,
            agent_data=agent_data,
            message_content=message_content,
            model="gemini-2.5-flash-image",
            user_id=user_id,
            history_count=10,
        )

        assert "image_url" in result
        assert "image_metadata" in result
        assert "prompt" in result
        assert "message_id" in result
        assert result["message_id"] == message_id
        assert isinstance(captured["prompt"], str)
        assert "Recent conversation context:" not in captured["prompt"]

        row = (
            await session.execute(
                select(models.ChatHistory).where(
                    models.ChatHistory.session_id == session_uuid,
                    models.ChatHistory.id == message_id,
                )
            )
        ).scalar_one_or_none()
        assert row is not None
        assert row.meta_data is not None
        gen = row.meta_data.get("generated_image")
        assert gen is not None
        assert gen.get("image_url", "").startswith("gs://")

        await session.refresh(agent)
        assert len(agent.background_images) >= 1
        assert any(
            u.startswith("gs://") and "chat_images/" in u for u in agent.background_images
        )

        res_stmt = select(models.Resource).where(
            models.Resource.url == gen["image_url"]
        )
        resource = (await session.execute(res_stmt)).scalar_one_or_none()
        assert resource is not None, "Chat-generated image should be saved to resources table"
        assert resource.agent_id == agent_id
        assert resource.user_id == user_id
        stored_prompt = resource.resource_metadata.get("generation_prompt") or ""
        assert len(stored_prompt) > 0
        assert "给我画一张图片" in stored_prompt
        assert resource.resource_metadata.get("gcs_url") == gen["image_url"]

        if resource is not None:
            await session.delete(resource)
        await session.delete(chat_msg)
        await session.delete(agent)
        await session.delete(user)
        await session.commit()

    def _make_fake_fal_result(self, gcs_uri_base: str, suffix: str) -> GeneratedImageProcessResult:
        """Build a deterministic GeneratedImageProcessResult for Fal path tests (no real Fal/GCS)."""
        bucket = global_config_loaded_from_config_yaml.gcs.bucket
        gcs_uri = f"gs://{bucket}/{gcs_uri_base}/fal_test_{suffix}.jpg"
        gcs_http_url = f"https://storage.googleapis.com/{bucket}/{gcs_uri_base}/fal_test_{suffix}.jpg"
        return GeneratedImageProcessResult(
            size=ImageSize(width=64, height=64),
            format=ImageFormat.JPEG,
            raw_data=b"",
            raw_data_total_bytes=100,
            gcs_uri=gcs_uri,
            gcs_http_url=gcs_http_url,
            generated_at=datetime.datetime.now(datetime.timezone.utc),
            raw_response_from_provider=None,
        )

    @pytest.mark.asyncio
    async def test_generate_chat_image_for_message_fal_z_image_turbo_saves_to_resources(
        self,
        monkeypatch: pytest.MonkeyPatch,
        db_session: AsyncSession,
    ):
        """Fal z_image_turbo/image-to-image 生成的聊天图片应保存到 resources 表（真实 DB）。"""
        session = db_session
        session_uuid = uuid.uuid4()
        session_id_str = str(session_uuid)
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"

        user = models.User(
            id=user_id,
            readable_id=uuid.uuid4().hex[:8],
            auth_type=AuthType.PHONE,
            nickname="Fal Tester",
            email="fal@example.com",
            system_language="en",
        )
        session.add(user)
        await session.commit()

        agent = models.Agent(
            id=agent_id,
            readable_id=uuid.uuid4().hex[:8],
            name="Fal Chat Agent",
            gender=Gender.FEMALE,
            avatar="https://storage.googleapis.com/test-bucket/avatar.jpg",
            background="https://example.com/background.jpg",
            personality="gentle",
            scenario="cafe",
            intro="intro",
            opening="hello",
            visibility=AgentVisibility.PUBLIC,
            status=AgentStatus.APPROVED,
            creator_id=user_id,
            background_images=[],
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)

        chat_msg = models.ChatHistory(
            session_id=session_uuid,
            message={"type": "user", "data": {"content": "draw me a portrait"}},
            meta_data=None,
        )
        session.add(chat_msg)
        await session.commit()
        await session.refresh(chat_msg)
        message_id = chat_msg.id

        async def fake_z_image_turbo_image_to_image(args, gcs_uri_base=None):
            return self._make_fake_fal_result(gcs_uri_base or "", "z")

        monkeypatch.setattr(
            "app.services.image_generation_service.z_image_turbo_image_to_image",
            fake_z_image_turbo_image_to_image,
        )
        monkeypatch.setattr(
            "app.services.image_generation_service.image_transform_service.transform_desktop",
            lambda url: "https://cdn.example.com/" + url.split("/", 3)[-1],
        )

        agent_data = {
            "id": agent_id,
            "personality": agent.personality,
            "scenario": agent.scenario,
            "intro": agent.intro,
            "background": agent.background,
        }
        message_content = "draw me a portrait"

        result = await image_generation_service.generate_chat_image(
            db=session,
            session_id=session_id_str,
            message_id=message_id,
            agent_data=agent_data,
            message_content=message_content,
            model=Z_IMAGE_TURBO_IMAGE_TO_IMAGE.id_on_provider,
            user_id=user_id,
            history_count=5,
        )

        assert result["message_id"] == message_id
        assert "image_url" in result

        row = (
            await session.execute(
                select(models.ChatHistory).where(
                    models.ChatHistory.session_id == session_uuid,
                    models.ChatHistory.id == message_id,
                )
            )
        ).scalar_one_or_none()
        assert row is not None
        gen = row.meta_data.get("generated_image")
        assert gen is not None
        assert gen.get("image_url", "").startswith("gs://")

        res_stmt = select(models.Resource).where(models.Resource.url == gen["image_url"])
        resource = (await session.execute(res_stmt)).scalar_one_or_none()
        assert resource is not None, "Fal z_image_turbo chat image should be saved to resources table"
        assert resource.agent_id == agent_id
        assert resource.user_id == user_id
        stored_prompt = resource.resource_metadata.get("generation_prompt") or ""
        assert len(stored_prompt) > 0
        assert "draw me a portrait" in stored_prompt
        assert resource.resource_metadata.get("gcs_url") == gen["image_url"]

        await session.delete(resource)
        await session.delete(chat_msg)
        await session.delete(agent)
        await session.delete(user)
        await session.commit()

    @pytest.mark.asyncio
    async def test_generate_chat_image_for_message_fal_seedream_saves_to_resources(
        self,
        monkeypatch: pytest.MonkeyPatch,
        db_session: AsyncSession,
    ):
        """Fal seedream v4.5 edit 生成的聊天图片应保存到 resources 表（真实 DB）。"""
        session = db_session
        session_uuid = uuid.uuid4()
        session_id_str = str(session_uuid)
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"

        user = models.User(
            id=user_id,
            readable_id=uuid.uuid4().hex[:8],
            auth_type=AuthType.PHONE,
            nickname="Seedream Tester",
            email="seedream@example.com",
            system_language="en",
        )
        session.add(user)
        await session.commit()

        agent = models.Agent(
            id=agent_id,
            readable_id=uuid.uuid4().hex[:8],
            name="Seedream Chat Agent",
            gender=Gender.FEMALE,
            avatar="https://storage.googleapis.com/test-bucket/avatar.jpg",
            background="https://example.com/background.jpg",
            personality="warm",
            scenario="park",
            intro="intro",
            opening="hello",
            visibility=AgentVisibility.PUBLIC,
            status=AgentStatus.APPROVED,
            creator_id=user_id,
            background_images=[],
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)

        chat_msg = models.ChatHistory(
            session_id=session_uuid,
            message={"type": "user", "data": {"content": "generate a scene with us"}},
            meta_data=None,
        )
        session.add(chat_msg)
        await session.commit()
        await session.refresh(chat_msg)
        message_id = chat_msg.id

        async def fake_seedream_v4_5_edit(args, gcs_uri_base=None):
            return self._make_fake_fal_result(gcs_uri_base or "", "s")

        monkeypatch.setattr(
            "app.services.image_generation_service.seedream_v4_5_edit",
            fake_seedream_v4_5_edit,
        )
        monkeypatch.setattr(
            "app.services.image_generation_service.image_transform_service.transform_desktop",
            lambda url: "https://cdn.example.com/" + url.split("/", 3)[-1],
        )

        agent_data = {
            "id": agent_id,
            "personality": agent.personality,
            "scenario": agent.scenario,
            "intro": agent.intro,
            "background": agent.background,
        }
        message_content = "generate a scene with us"

        result = await image_generation_service.generate_chat_image(
            db=session,
            session_id=session_id_str,
            message_id=message_id,
            agent_data=agent_data,
            message_content=message_content,
            model=SEEDREAM_V4_5_EDIT.id_on_provider,
            user_id=user_id,
            history_count=5,
        )

        assert result["message_id"] == message_id
        assert "image_url" in result

        row = (
            await session.execute(
                select(models.ChatHistory).where(
                    models.ChatHistory.session_id == session_uuid,
                    models.ChatHistory.id == message_id,
                )
            )
        ).scalar_one_or_none()
        assert row is not None
        gen = row.meta_data.get("generated_image")
        assert gen is not None
        assert gen.get("image_url", "").startswith("gs://")

        res_stmt = select(models.Resource).where(models.Resource.url == gen["image_url"])
        resource = (await session.execute(res_stmt)).scalar_one_or_none()
        assert resource is not None, "Fal seedream chat image should be saved to resources table"
        assert resource.agent_id == agent_id
        assert resource.user_id == user_id
        stored_prompt = resource.resource_metadata.get("generation_prompt") or ""
        assert len(stored_prompt) > 0
        assert "generate a scene with us" in stored_prompt
        assert resource.resource_metadata.get("gcs_url") == gen["image_url"]

        await session.delete(resource)
        await session.delete(chat_msg)
        await session.delete(agent)
        await session.delete(user)
        await session.commit()


class TestChatHistoryService:
    """测试聊天历史服务"""

    @pytest.mark.asyncio
    async def test_add_ai_image_message(self, db_session: AsyncSession):
        """测试添加AI图片消息（真实 DB 读写）。"""
        session = db_session
        session_uuid = uuid.uuid4()
        session_id_str = str(session_uuid)

        user_msg = models.ChatHistory(
            session_id=session_uuid,
            message={"type": "user", "data": {"content": "draw an image"}},
            meta_data=None,
        )
        session.add(user_msg)
        await session.commit()
        await session.refresh(user_msg)

        image_url = "gs://bucket/image.jpg"
        image_metadata = {
            "width": 1024,
            "height": 1792,
            "format": "jpeg",
        }
        prompt = "测试提示词"
        agent_id = "agent_123"

        msg_id = await chat_history_service.add_ai_image_message(
            db=session,
            session_id=session_id_str,
            image_url=image_url,
            image_metadata=image_metadata,
            prompt=prompt,
            agent_id=agent_id,
            source_message_id=user_msg.id,
        )
        assert msg_id is not None

        stmt = (
            select(models.ChatHistory)
            .where(models.ChatHistory.session_id == session_uuid)
            .order_by(models.ChatHistory.id.desc())
            .limit(1)
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        assert row is not None
        assert row.id == msg_id
        assert row.message.get("type") == "image"
        assert row.message.get("data", {}).get("image_url") == image_url
        assert row.message.get("data", {}).get("prompt") == prompt
        assert row.meta_data is not None
        assert row.meta_data.get("agentId") == agent_id
        assert row.meta_data.get("source_message_id") == user_msg.id

        await session.delete(row)
        await session.delete(user_msg)
        await session.commit()

    @pytest.mark.asyncio
    async def test_generate_chat_image_appends_agent_background_images(
        self,
        monkeypatch: pytest.MonkeyPatch,
        db_session: AsyncSession,
    ):
        """生成聊天图片后应将GCS图片追加到Agent的background_images（真实 DB 读写）。"""
        monkeypatch.setattr(
            "app.services.image_generation_service.get_genai_client",
            lambda: FakeGeminiClient(),
        )
        monkeypatch.setattr(
            "app.core.google_genai.wrapped_client.upload_to_gcs",
            lambda file_data, content_type, bucket_name, path: "https://storage.googleapis.com/{}/{}".format(
                bucket_name, path
            ),
        )
        monkeypatch.setattr(
            "app.services.image_generation_service.image_transform_service.transform_desktop",
            lambda url: "https://cdn.example.com/{}".format(url.split("/", 3)[-1]),
        )

        session = db_session
        session_uuid = uuid.uuid4()
        session_id_str = str(session_uuid)
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"

        user = models.User(
            id=user_id,
            readable_id=uuid.uuid4().hex[:8],
            auth_type=AuthType.PHONE,
            nickname="Chat Tester",
            email="test@example.com",
            system_language="en",
        )
        session.add(user)
        await session.commit()

        agent = models.Agent(
            id=agent_id,
            readable_id=uuid.uuid4().hex[:8],
            name="Chat Image Agent",
            gender=Gender.FEMALE,
            avatar="https://storage.googleapis.com/test-bucket/avatar.jpg",
            background="https://storage.googleapis.com/test-bucket/background.jpg",
            personality="gentle",
            scenario="coffee shop",
            intro="intro text",
            opening="hello",
            visibility=AgentVisibility.PUBLIC,
            status=AgentStatus.APPROVED,
            creator_id=user_id,
            background_images=["gs://test-bucket/original.jpg"],
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)

        chat_msg = models.ChatHistory(
            session_id=session_uuid,
            message={"type": "user", "data": {"content": "please draw an image"}},
            meta_data=None,
        )
        session.add(chat_msg)
        await session.commit()
        await session.refresh(chat_msg)
        message_id = chat_msg.id

        agent_data = {
            "id": agent_id,
            "personality": agent.personality,
            "scenario": agent.scenario,
            "intro": agent.intro,
            "background": agent.background,
        }

        result = await image_generation_service.generate_chat_image(
            db=session,
            session_id=session_id_str,
            message_id=message_id,
            agent_data=agent_data,
            message_content="please draw an image",
            model="gemini-2.5-flash-image",
            user_id=user_id,
            history_count=5,
        )

        assert result["message_id"] == message_id
        assert result["image_url"].startswith("https://cdn.example.com/")

        await session.refresh(agent)
        assert agent.background_images[0] == "gs://test-bucket/original.jpg"
        assert len(agent.background_images) == 2
        bucket = global_config_loaded_from_config_yaml.gcs.bucket
        assert agent.background_images[1].startswith(f"gs://{bucket}/chat_images/")

        row = (
            await session.execute(
                select(models.ChatHistory).where(
                    models.ChatHistory.session_id == session_uuid,
                    models.ChatHistory.id == message_id,
                )
            )
        ).scalar_one_or_none()
        assert row is not None
        assert row.meta_data is not None
        assert row.meta_data.get("generated_image") is not None

        res_stmt = select(models.Resource).where(
            models.Resource.agent_id == agent_id
        )
        res_result = await session.execute(res_stmt)
        resources = res_result.scalars().all()
        for res in resources:
            await session.delete(res)
        await session.delete(chat_msg)
        await session.delete(agent)
        await session.delete(user)
        await session.commit()

    @pytest.mark.asyncio
    async def test_generate_chat_image_for_message_writes_db_records_as_expected(
        self,
        monkeypatch: pytest.MonkeyPatch,
        db_session: AsyncSession,
    ):
        """generate_chat_image_for_message 写入的 DB 记录符合预期：消息 meta_data、Agent background_images、Resource 表（真实 DB 读写）。"""
        monkeypatch.setattr(
            "app.services.image_generation_service.get_genai_client",
            lambda: FakeGeminiClient(),
        )

        def fake_upload(file_data, content_type, bucket_name, path):
            return "https://storage.googleapis.com/{}/{}".format(bucket_name, path)

        monkeypatch.setattr(
            "app.core.google_genai.wrapped_client.upload_to_gcs",
            fake_upload,
        )
        monkeypatch.setattr(
            "app.services.image_generation_service.image_transform_service.transform_desktop",
            lambda url: "https://cdn.example.com/{}".format(url.split("/", 3)[-1]),
        )
        monkeypatch.setattr(
            "app.services.image_generation_service.get_current_trace_info",
            lambda: (
                "trace-id-for-test-chat-image",
                "https://smith.langchain.com/o/test/projects/p/test/r/trace-id-for-test-chat-image",
            ),
        )

        session = db_session
        user_id = "user-{}".format(uuid.uuid4().hex[:8])
        agent_id = "agent-{}".format(uuid.uuid4().hex[:8])
        session_uuid = uuid.uuid4()
        session_id_str = str(session_uuid)

        user = models.User(
            id=user_id,
            readable_id=uuid.uuid4().hex[:8],
            auth_type=AuthType.PHONE,
            nickname="Chat Tester",
            email="test@example.com",
            system_language="en",
            user_photo="gs://test-bucket/user-selfie.jpg",
        )
        session.add(user)
        await session.commit()

        agent = models.Agent(
            id=agent_id,
            readable_id=uuid.uuid4().hex[:8],
            name="Chat Image Agent",
            gender=Gender.FEMALE,
            avatar="https://storage.googleapis.com/test-bucket/avatar.jpg",
            background="https://storage.googleapis.com/test-bucket/background.jpg",
            personality="gentle",
            scenario="coffee shop",
            intro="intro text",
            opening="hello",
            visibility=AgentVisibility.PUBLIC,
            status=AgentStatus.APPROVED,
            creator_id=user_id,
            background_images=["gs://test-bucket/original.jpg"],
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)

        # 真实消息行，以便 update_message_metadata 能更新
        chat_msg = models.ChatHistory(
            session_id=session_uuid,
            message={"type": "user", "data": {"content": "draw an image"}},
            meta_data=None,
        )
        session.add(chat_msg)
        await session.commit()
        await session.refresh(chat_msg)
        message_id = chat_msg.id

        agent_data = {
            "id": agent_id,
            "personality": agent.personality,
            "scenario": agent.scenario,
            "intro": agent.intro,
            "background": agent.background,
        }

        result = await image_generation_service.generate_chat_image(
            db=session,
            session_id=session_id_str,
            message_id=message_id,
            agent_data=agent_data,
            message_content="please draw an image",
            model="gemini-2.5-flash-image",
            user_id=user_id,
            history_count=5,
        )

        assert result["message_id"] == message_id
        assert result["image_url"].startswith("https://cdn.example.com/")

        # 1) 消息 meta_data 中应有 generated_image
        stmt = select(models.ChatHistory).where(
            models.ChatHistory.session_id == session_uuid,
            models.ChatHistory.id == message_id,
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        assert row is not None
        assert row.meta_data is not None
        gen = row.meta_data.get("generated_image")
        assert gen is not None
        assert "image_url" in gen
        assert gen["image_url"].startswith("gs://")
        assert gen.get("width") is not None
        assert gen.get("height") is not None
        assert gen.get("format") is not None
        assert gen.get("prompt") is not None
        assert gen.get("generated_at") is not None
        assert gen.get("reference_image_url") == agent.background
        assert (
            gen.get("user_reference_image_url")
            == "https://storage.googleapis.com/test-bucket/user-selfie.jpg"
        )
        assert gen.get("reference_image_urls") == [
            agent.background,
            "https://storage.googleapis.com/test-bucket/user-selfie.jpg",
        ]

        gcs_uri = gen["image_url"]

        # 2) Agent background_images 应包含新图
        await session.refresh(agent)
        assert len(agent.background_images) == 2
        assert agent.background_images[0] == "gs://test-bucket/original.jpg"
        assert gcs_uri in agent.background_images or agent.background_images[1] == gcs_uri

        # 3) Resource 表应有对应记录（user_id 传入时）
        res_stmt = select(models.Resource).where(models.Resource.url == gcs_uri)
        resource = (await session.execute(res_stmt)).scalar_one_or_none()
        assert resource is not None
        assert resource.agent_id == agent_id
        assert resource.user_id == user_id
        meta = resource.resource_metadata or {}
        assert meta.get("generation_prompt") is not None
        assert meta.get("gcs_url") == gcs_uri
        assert meta.get("reference_image_url") == agent.background
        assert (
            meta.get("user_reference_image_url")
            == "https://storage.googleapis.com/test-bucket/user-selfie.jpg"
        )
        assert meta.get("reference_image_urls") == [
            agent.background,
            "https://storage.googleapis.com/test-bucket/user-selfie.jpg",
        ]
        assert meta.get("langsmith_trace_id") == "trace-id-for-test-chat-image"
        assert (
            meta.get("langsmith_trace_url")
            == "https://smith.langchain.com/o/test/projects/p/test/r/trace-id-for-test-chat-image"
        )

        await session.delete(resource)
        await session.delete(chat_msg)
        await session.delete(agent)
        await session.delete(user)
        await session.commit()
