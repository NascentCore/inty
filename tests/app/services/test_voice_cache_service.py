import pytest

import app.services.voice_cache_service as voice_cache_module
from app.services.voice_cache_service import VoiceCacheService


class _RollbackFailingDb:
    async def execute(self, stmt):
        raise RuntimeError("write failed")

    async def rollback(self):
        raise RuntimeError("rollback failed")


@pytest.mark.asyncio
async def test_save_voice_cache_logs_rollback_failure(monkeypatch):
    error_messages = []

    def fake_error(message):
        error_messages.append(message)

    monkeypatch.setattr(voice_cache_module.logger, "error", fake_error)
    service = object.__new__(VoiceCacheService)

    saved = await service._save_voice_cache_impl(
        _RollbackFailingDb(),
        "hello",
        "voice-a",
        "model-a",
        "en",
        "https://example.com/audio.mp3",
        1.0,
    )

    assert saved is False
    assert error_messages == [
        "保存语音缓存失败: write failed",
        "保存语音缓存失败后回滚失败: voice_id=voice-a, model=model-a, language=en, "
        "original_error=write failed, rollback_error=rollback failed",
    ]


@pytest.mark.asyncio
async def test_update_access_stats_logs_rollback_failure(monkeypatch):
    error_messages = []

    def fake_error(message):
        error_messages.append(message)

    monkeypatch.setattr(voice_cache_module.logger, "error", fake_error)
    service = object.__new__(VoiceCacheService)

    await service._update_access_stats_impl(
        _RollbackFailingDb(),
        "hello",
        "voice-a",
        "model-a",
        "en",
    )

    assert error_messages == [
        "更新缓存访问统计失败: write failed",
        "更新缓存访问统计失败后回滚失败: voice_id=voice-a, model=model-a, language=en, "
        "original_error=write failed, rollback_error=rollback failed",
    ]
