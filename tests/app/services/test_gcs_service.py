"""
GCSService 单元测试：upload_live_chat_audio 等。

使用 app.external_services.fakes.gcs.FakeGCSClient 注入，不依赖真实 GCS 或 config 文件。
"""

import types

import pytest

from app.external_services.fakes.gcs import FakeGCSClient
from app.external_services.gcs import get_bucket_and_path_from_gcs_url
from app.services.gcs_service import GCSService


@pytest.fixture
def fake_gcs(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """注入 FakeGCSClient 到 app.external_services.gcs，返回 fake 实例供断言使用。"""
    import app.external_services.gcs as gcs_module

    base = str(tmp_path.resolve())
    fake = FakeGCSClient(base_dir=base)
    monkeypatch.setattr(gcs_module, "gcs_client", fake, raising=True)
    gcs_cfg = types.SimpleNamespace(
        bucket="test-bucket",
        use_fake_gcs=True,
        fake_gcs_base_dir=base,
    )
    merged = types.SimpleNamespace(gcs=gcs_cfg)
    monkeypatch.setattr(
        gcs_module,
        "global_config_loaded_from_config_yaml",
        merged,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.gcs_service.global_config_loaded_from_config_yaml",
        merged,
        raising=True,
    )
    yield fake


@pytest.fixture
def stub_config(monkeypatch: pytest.MonkeyPatch):
    """Stub GCSService 使用的 gcs.bucket 配置。"""
    stub = types.SimpleNamespace(
        gcs=types.SimpleNamespace(bucket="test-bucket"),
    )
    monkeypatch.setattr(
        "app.services.gcs_service.global_config_loaded_from_config_yaml",
        stub,
        raising=True,
    )


@pytest.mark.asyncio
async def test_upload_live_chat_audio_success(fake_gcs: FakeGCSClient):
    """成功路径：上传后返回正确 URL，fake 中可下载到相同内容。"""
    wav_bytes = b"fake-wav-content"
    service = GCSService()
    url = await service.upload_live_chat_audio(
        "user1", "agent1", "sess1", "voice1", wav_bytes
    )

    expected_url = (
        fake_gcs.base_dir / "test-bucket" / "live_chat/user1/agent1/sess1_voice1.wav"
    ).resolve().as_uri()
    assert url == expected_url

    blob = fake_gcs.bucket("test-bucket").blob(
        "live_chat/user1/agent1/sess1_voice1.wav"
    )
    assert blob.exists() is True
    assert blob.download_as_bytes() == wav_bytes


@pytest.mark.asyncio
async def test_upload_live_chat_audio_returns_none_on_upload_failure(stub_config):
    """失败路径：upload_to_gcs 抛异常时返回 None，不影响调用方。"""
    from unittest.mock import patch

    with patch("app.services.gcs_service.upload_to_gcs", side_effect=Exception("fake error")):
        service = GCSService()
        url = await service.upload_live_chat_audio(
            "user1", "agent1", "sess1", "voice1", b"wav"
        )
    assert url is None


@pytest.mark.asyncio
async def test_upload_voice_file_fake_gcs_upload_and_cache_hit(
    fake_gcs: FakeGCSClient,
):
    """Fake GCS: first upload and cache hit both return file:// URIs."""
    mp3_bytes = b"fake-mp3-content"
    service = GCSService()
    file_name = "voice_cache_test.mp3"
    url1 = await service.upload_voice_file(file_name, mp3_bytes)
    assert url1 is not None
    assert url1.startswith("file:")

    url2 = await service.upload_voice_file(file_name, mp3_bytes)
    assert url2 == url1


@pytest.mark.asyncio
async def test_upload_live_chat_audio_e2e_download_by_url(fake_gcs: FakeGCSClient):
    """端到端：上传后按返回 URL 用 FakeGCS 下载，验证路径正确且文件可检索。"""
    wav_bytes = b"fake-wav-content"
    service = GCSService()
    url = await service.upload_live_chat_audio(
        "user1", "agent1", "sess1", "voice1", wav_bytes
    )
    assert url is not None

    bucket_name, gcs_path = get_bucket_and_path_from_gcs_url(url)
    downloaded = fake_gcs.bucket(bucket_name).blob(gcs_path).download_as_bytes()
    assert downloaded == wav_bytes
