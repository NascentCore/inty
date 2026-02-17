import importlib
import sys
import types
from datetime import date
from unittest.mock import AsyncMock

import pytest


def _build_festival_metadata(festival_name: str, festival_date: date) -> dict:
    day = festival_date.isoformat()
    return {
        "festival_name": festival_name,
        "festival_data": day,
        "festival_date": day,
    }


def _resolve_festival_name_and_date(metadata, legacy_name, legacy_date):
    name = None
    day = None
    if isinstance(metadata, dict):
        raw_name = metadata.get("festival_name")
        if isinstance(raw_name, str) and raw_name.strip():
            name = raw_name.strip()
        raw_day = metadata.get("festival_data") or metadata.get("festival_date")
        if isinstance(raw_day, str):
            try:
                day = date.fromisoformat(raw_day)
            except ValueError:
                day = None
    if name is None and isinstance(legacy_name, str) and legacy_name.strip():
        name = legacy_name.strip()
    if day is None and isinstance(legacy_date, date):
        day = legacy_date
    return name, day


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
        festival_name = object()
        festival_date = object()

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    fake_memory_model_module = types.ModuleType("app.models.memory")
    fake_memory_model_module.Memory = _Memory

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
    fake_memory_service_module.resolve_festival_name_and_date = (
        _resolve_festival_name_and_date
    )

    fake_openai_client_module = types.ModuleType("app.utils.openai_client")

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
        mp.setitem(sys.modules, "app.utils.openai_client", fake_openai_client_module)
        mp.setitem(sys.modules, "app.utils.openrouter_memory", fake_openrouter_module)
        module = importlib.import_module("app.services.festival_memory_service")
    return module


service = _load_festival_memory_service_module()


@pytest.mark.asyncio
async def test_extract_festival_to_dict_uses_metadata_and_omits_extracted_at():
    fake_memory = types.SimpleNamespace(
        user_id="u-1",
        agent_id="a-1",
        memory_type="festival",
        content="summary",
        meta_data={
            "festival_name": "Easter",
            "festival_data": "2026-04-05",
            "llm": "fake-model",
        },
        festival_name="Legacy Easter",
        festival_date=date(2026, 4, 6),
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
    assert out["festival_name"] == "Easter"
    assert out["festival_date"] == "2026-04-05"
    assert out["llm"] == "fake-model"
    assert "extracted_at" not in out


@pytest.mark.asyncio
async def test_extract_festival_to_dict_falls_back_to_legacy_columns():
    fake_memory = types.SimpleNamespace(
        user_id="u-2",
        agent_id="a-2",
        memory_type="festival",
        content="legacy summary",
        meta_data=None,
        festival_name="Legacy Festival",
        festival_date=date(2026, 8, 8),
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

    assert out is not None
    assert out["festival_name"] == "Legacy Festival"
    assert out["festival_date"] == "2026-08-08"
    assert "llm" in out
    assert out["llm"] is None
