"""
GCSService 单元测试：upload_live_chat_audio 等。

使用 app.external_services.fakes.gcs.FakeGCSClient 注入，不依赖真实 GCS 或 config 文件。
"""

import types

import pytest

from app.external_services.fakes.gcs import FakeGCSClient
from app.services.gcs_service import GCSService


@pytest.fixture
def fake_gcs(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """注入 FakeGCSClient 到 app.external_services.gcs，返回 fake 实例供断言使用。"""
    import app.external_services.gcs as gcs_module

    fake = FakeGCSClient(base_dir=str(tmp_path))
    monkeypatch.setattr(gcs_module, "gcs_client", fake, raising=True)
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
async def test_upload_live_chat_audio_success(fake_gcs: FakeGCSClient, stub_config):
    """成功路径：上传后返回正确 URL，fake 中可下载到相同内容。"""
    wav_bytes = b"fake-wav-content"
    service = GCSService()
    url = await service.upload_live_chat_audio(
        "user1", "agent1", "sess1", wav_bytes
    )

    expected_url = "https://storage.googleapis.com/test-bucket/live_chat/user1/agent1/sess1.wav"
    assert url == expected_url

    blob = fake_gcs.bucket("test-bucket").blob("live_chat/user1/agent1/sess1.wav")
    assert blob.exists() is True
    assert blob.download_as_bytes() == wav_bytes


@pytest.mark.asyncio
async def test_upload_live_chat_audio_returns_none_on_upload_failure(stub_config):
    """失败路径：upload_to_gcs 抛异常时返回 None，不影响调用方。"""
    from unittest.mock import patch

    with patch("app.services.gcs_service.upload_to_gcs", side_effect=Exception("fake error")):
        service = GCSService()
        url = await service.upload_live_chat_audio(
            "user1", "agent1", "sess1", b"wav"
        )
    assert url is None
