import importlib
import sys
import types
from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.models.memory import FestivalMemoryMetadata as RealFestivalMemoryMetadata


def _build_festival_metadata(festival_name: str, festival_date: date) -> dict:
    """Fake: 与 memory_service.build_festival_memory_metadata 一致，仅 festival_name、festival_date。"""
    return {
        "festival_name": festival_name,
        "festival_date": festival_date.isoformat(),
    }


def _resolve_festival_name_and_date(metadata):
    """Fake: 与 memory_service.resolve_festival_name_and_date 一致，仅读 metadata。"""
    name = None
    day = None
    if isinstance(metadata, dict):
        raw_name = metadata.get("festival_name")
        if isinstance(raw_name, str) and raw_name.strip():
            name = raw_name.strip()
        raw_day = metadata.get("festival_date")
        if isinstance(raw_day, str):
            try:
                day = date.fromisoformat(raw_day)
            except ValueError:
                day = None
    return name, day


def _metadata_to_llm_config_output(meta_data: dict):
    """Fake: 与 memory_service.metadata_to_llm_config_output 一致，仅支持 llm_config。"""
    if not isinstance(meta_data, dict):
        return None
    stored = meta_data.get("llm_config")
    if isinstance(stored, dict) and (stored.get("model") or "").strip():
        return {
            "model": (stored.get("model") or "").strip(),
            "temperature": stored.get("temperature", 0.0),
            "max_tokens": stored.get("max_tokens", 2000),
        }
    return None


def _load_festival_memory_service_module():
    fake_llm_config_module = types.ModuleType("app.api.types.llm_config")

    class _LLMConfig:
        def __init__(self, model=None, max_tokens=None, temperature=None):
            self.model = model
            self.max_tokens = max_tokens
            self.temperature = temperature

        @classmethod
        def model_validate(cls, data: dict):
            return cls(
                model=data.get("model"),
                max_tokens=data.get("max_tokens"),
                temperature=data.get("temperature"),
            )

    fake_llm_config_module.LLMConfig = _LLMConfig

    fake_core_config_module = types.ModuleType("app.core.config")
    fake_core_config_module.global_config_loaded_from_config_yaml = types.SimpleNamespace(
        database=types.SimpleNamespace(
            url="postgresql://primary-host:5432/inty", async_replica_url=None
        ),
        memory_extraction=types.SimpleNamespace(model=None),
    )

    fake_prompt_cfg_module = types.ModuleType("app.core.agent.agent_prompt_configs")
    fake_prompt_cfg_module.INTELLIMATE_AGENT_ID = "official-agent"

    fake_agent_model_module = types.ModuleType("app.models.agent")
    fake_agent_model_module.Agent = type("Agent", (), {"name": object()})

    class _Memory:
        id = object()
        user_id = object()
        agent_id = object()
        memory_type = object()
        content = object()
        meta_data = object()
        extracted_at = object()

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    fake_memory_model_module = types.ModuleType("app.models.memory")
    fake_memory_model_module.Memory = _Memory
    fake_memory_model_module.FestivalMemoryMetadata = RealFestivalMemoryMetadata

    fake_user_model_module = types.ModuleType("app.models.user")
    fake_user_model_module.User = type("User", (), {"nickname": object()})

    fake_chat_history_module = types.ModuleType("app.services.chat_history_service")
    fake_chat_history_module.get_chat_history_connection = lambda: None
    fake_chat_history_module.get_chat_history_replica_connection = lambda: None

    fake_chat_service_module = types.ModuleType("app.services.chat_service")
    fake_chat_service_module.generate_session_id = lambda chat_id: str(chat_id)

    fake_memory_service_module = types.ModuleType("app.services.memory_service")
    fake_memory_service_module.MEMORY_TYPE_FESTIVAL = "festival"
    fake_memory_service_module.build_festival_memory_metadata = _build_festival_metadata
    fake_memory_service_module.metadata_to_llm_config_output = (
        _metadata_to_llm_config_output
    )
    fake_memory_service_module.resolve_festival_name_and_date = (
        _resolve_festival_name_and_date
    )

    fake_openai_client_module = types.ModuleType("app.core.llms.openai_client")

    async def _dummy_chat_completion_for_extraction(*args, **kwargs):
        return ("dummy summary", None, None)

    fake_openai_client_module.chat_completion_for_extraction = (
        _dummy_chat_completion_for_extraction
    )

    fake_openrouter_module = types.ModuleType("app.utils.openrouter_memory")
    fake_openrouter_module.DEFAULT_MEMORY_EXTRACTION_MODEL = "fake-model"

    sys.modules.pop("app.services.festival_memory_service", None)
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "app.api.types.llm_config", fake_llm_config_module)
        mp.setitem(sys.modules, "app.core.config", fake_core_config_module)
        mp.setitem(
            sys.modules, "app.core.agent.agent_prompt_configs", fake_prompt_cfg_module
        )
        mp.setitem(sys.modules, "app.models.agent", fake_agent_model_module)
        mp.setitem(sys.modules, "app.models.memory", fake_memory_model_module)
        mp.setitem(sys.modules, "app.models.user", fake_user_model_module)
        mp.setitem(sys.modules, "app.services.chat_history_service", fake_chat_history_module)
        mp.setitem(sys.modules, "app.services.chat_service", fake_chat_service_module)
        mp.setitem(sys.modules, "app.services.memory_service", fake_memory_service_module)
        mp.setitem(sys.modules, "app.core.llms.openai_client", fake_openai_client_module)
        mp.setitem(sys.modules, "app.utils.openrouter_memory", fake_openrouter_module)
        module = importlib.import_module("app.services.festival_memory_service")
    return module


service = _load_festival_memory_service_module()


@pytest.mark.asyncio
async def test_extract_festival_to_dict_uses_metadata_and_omits_extracted_at():
    llm_config_stored = {
        "model": "fake-model",
        "temperature": 0.0,
        "max_tokens": 2000,
    }
    fake_memory = types.SimpleNamespace(
        user_id="u-1",
        agent_id="a-1",
        memory_type="festival",
        content="summary",
        meta_data={
            "festival_name": "Easter",
            "festival_date": "2026-04-05",
            "llm_config": llm_config_stored,
        },
    )
    service.summarize_memory_from_messages_between_user_and_agent = AsyncMock(
        return_value=fake_memory
    )

    out = await service.extract_festival_to_dict(
        user_id="u-1",
        agent_id="a-1",
        festival_name="Easter",
        festival_date=date(2026, 4, 5),
        prompt_template="prompt",
    )

    assert out is not None
    assert "metadata" in out
    assert out["metadata"]["festival_name"] == "Easter"
    assert out["metadata"]["festival_date"] == "2026-04-05"
    # llm_config 为完整 LLMConfig.model_dump()，至少包含传入的 model/temperature/max_tokens
    out_llm = out["metadata"]["llm_config"]
    assert out_llm["model"] == llm_config_stored["model"]
    assert out_llm["temperature"] == llm_config_stored["temperature"]
    assert out_llm["max_tokens"] == llm_config_stored["max_tokens"]
    assert "festival_name" not in out
    assert "festival_date" not in out
    assert "llm_config" not in out
    assert "extracted_at" not in out


@pytest.mark.asyncio
async def test_extract_festival_to_dict_returns_none_when_metadata_empty():
    """meta_data 为空时无法解析节日名/日期，extract_festival_to_dict 返回 None。"""
    fake_memory = types.SimpleNamespace(
        user_id="u-2",
        agent_id="a-2",
        memory_type="festival",
        content="legacy summary",
        meta_data=None,
    )
    service.summarize_memory_from_messages_between_user_and_agent = AsyncMock(
        return_value=fake_memory
    )

    out = await service.extract_festival_to_dict(
        user_id="u-2",
        agent_id="a-2",
        festival_name="Legacy Festival",
        festival_date=date(2026, 8, 8),
        prompt_template="prompt",
    )

    assert out is None


@pytest.mark.asyncio
async def test_extract_festival_to_dict_passes_llm_config_to_summarizer():
    """extract_festival_to_dict 传入 llm_config 时，summarize 被以该 config 调用，且返回 dict 的 llm_config 与之一致。"""
    custom_model = "openrouter/anthropic/claude-3.5-sonnet"
    llm_config = {"model": custom_model, "temperature": 0.0, "max_tokens": 2000}
    fake_memory = types.SimpleNamespace(
        user_id="u-3",
        agent_id="a-3",
        memory_type="festival",
        content="summary with custom model",
        meta_data={
            "festival_name": "Valentine",
            "festival_date": "2026-02-14",
            "llm_config": llm_config,
        },
    )
    summarizer_calls = []

    async def _capture_summarize(*args, **kwargs):
        summarizer_calls.append({"args": args, "kwargs": kwargs})
        return fake_memory

    service.summarize_memory_from_messages_between_user_and_agent = _capture_summarize

    out = await service.extract_festival_to_dict(
        user_id="u-3",
        agent_id="a-3",
        festival_name="Valentine",
        festival_date=date(2026, 2, 14),
        prompt_template="prompt",
        llm_config=llm_config,
    )

    assert out is not None
    assert "metadata" in out
    # 返回的 metadata.llm_config 为完整 model_dump()，至少包含传入的 model/temperature/max_tokens
    out_llm = out["metadata"].get("llm_config")
    assert out_llm is not None
    assert out_llm["model"] == llm_config["model"]
    assert out_llm["temperature"] == llm_config["temperature"]
    assert out_llm["max_tokens"] == llm_config["max_tokens"]
    assert "festival_name" not in out
    assert "llm_config" not in out
    assert len(summarizer_calls) == 1
    assert summarizer_calls[0]["kwargs"].get("llm_config") == llm_config
