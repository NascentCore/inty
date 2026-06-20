# CREATED_BY_AGENT
"""节日记忆服务单元测试"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import psycopg
import pytest
from pydantic import ValidationError

from app.services import festival_memory_service
from app.services.memory_service import get_festival_memories_for_user_agent


class TestGetFestivalMemoriesForUserAgent:
    """get_festival_memories_for_user_agent 返回格式与空结果"""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_memories(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        out = await get_festival_memories_for_user_agent(
            mock_db, "user-1", "agent-1"
        )
        assert out == []


class TestAssembleArgs:
    """assemble_args 返回 (full_prompt, LLMConfig)，有无 llm_config 时 model/temperature/max_tokens 来自 LLMConfig"""

    def test_with_llm_config_uses_custom_model_and_params(self):
        messages = [("user", "hi"), ("assistant", "hello")]
        llm_config = {
            "model": "anthropic/claude-3.5-sonnet",
            "temperature": 0.5,
            "max_tokens": 4096,
        }
        full_prompt, ext_llm_config = festival_memory_service.assemble_args(
            messages,
            "春节",
            date(2026, 2, 1),
            "Extract memories.",
            llm_config=llm_config,
        )
        assert "春节" in full_prompt and "Extract memories." in full_prompt
        assert ext_llm_config.model == "anthropic/claude-3.5-sonnet"
        assert ext_llm_config.max_tokens == 4096
        assert ext_llm_config.temperature == 0.5

    def test_with_invalid_temperature_or_max_tokens_raises_validation_error(
        self,
    ):
        """非法 numeric 的 dict 经 model_validate 会抛出 ValidationError。"""
        messages = [("user", "hi")]
        llm_config = {
            "model": "some/model",
            "temperature": "not-a-number",
            "max_tokens": "invalid",
        }
        with pytest.raises(ValidationError):
            festival_memory_service.assemble_args(
                messages,
                "春节",
                date(2026, 2, 1),
                "Prompt.",
                llm_config=llm_config,
            )

    def test_with_empty_model_in_config_falls_back_to_default(self):
        messages = [("user", "hi")]
        llm_config = {"model": "", "temperature": 0.8}
        with patch.object(
            festival_memory_service,
            "global_config_loaded_from_config_yaml",
            MagicMock(memory_extraction=MagicMock(model=None)),
        ):
            full_prompt, ext_llm_config = festival_memory_service.assemble_args(
                messages,
                "春节",
                date(2026, 2, 1),
                "Prompt.",
                llm_config=llm_config,
            )
        assert (
            ext_llm_config.model
            == festival_memory_service.DEFAULT_FESTIVAL_EXTRACTION_MODEL
        )
        assert ext_llm_config.max_tokens == 2000
        assert ext_llm_config.temperature == 0.0

    def test_without_llm_config_uses_default(self):
        messages = [("user", "hi")]
        with patch.object(
            festival_memory_service,
            "global_config_loaded_from_config_yaml",
            MagicMock(memory_extraction=MagicMock(model=None)),
        ):
            full_prompt, ext_llm_config = festival_memory_service.assemble_args(
                messages, "春节", date(2026, 2, 1), "Prompt."
            )
        assert (
            ext_llm_config.model
            == festival_memory_service.DEFAULT_FESTIVAL_EXTRACTION_MODEL
        )
        assert ext_llm_config.max_tokens == 2000
        assert ext_llm_config.temperature == 0.0


@pytest.mark.asyncio
async def test_summarize_memory_from_messages_includes_llm_config_in_metadata():
    """summarize_memory_from_messages_between_user_and_agent 返回的 Memory.meta_data 包含 llm_config（model、temperature、max_tokens）。"""
    with (
        patch.object(
            festival_memory_service,
            "get_messages_for_user_agent_sync",
            return_value=[("user", "hello"), ("assistant", "hi there")],
        ),
        patch.object(
            festival_memory_service,
            "chat_completion_for_extraction",
            new_callable=AsyncMock,
            return_value=("A short summary of the conversation.", 100, 50),
        ),
        patch.object(
            festival_memory_service,
            "global_config_loaded_from_config_yaml",
            MagicMock(memory_extraction=MagicMock(model=None)),
        ),
    ):
        memory = await festival_memory_service.summarize_memory_from_messages_between_user_and_agent(
            "user-1",
            "agent-1",
            "Test Festival",
            date(2026, 3, 1),
            "Extract memories.",
        )
    assert memory is not None
    assert memory.meta_data is not None
    llm_config = memory.meta_data.get("llm_config")
    assert isinstance(llm_config, dict)
    assert (
        isinstance(llm_config.get("model"), str)
        and len(llm_config["model"]) > 0
    )
    assert llm_config.get("temperature") == 0.0
    assert llm_config.get("max_tokens") == 2000


class _FakeCursor:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params=None):
        self._conn.executed.append((query, params))

    def fetchall(self):
        if self._conn.fetchall_index >= len(self._conn.fetchall_results):
            return []
        result = self._conn.fetchall_results[self._conn.fetchall_index]
        self._conn.fetchall_index += 1
        return result

    def fetchone(self):
        if self._conn.fetchone_index >= len(self._conn.fetchone_results):
            return None
        result = self._conn.fetchone_results[self._conn.fetchone_index]
        self._conn.fetchone_index += 1
        return result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self, *, fetchall_results=None, fetchone_results=None):
        self.fetchall_results = fetchall_results or []
        self.fetchone_results = fetchone_results or []
        self.fetchall_index = 0
        self.fetchone_index = 0
        self.executed = []
        self.closed = False

    def cursor(self):
        return _FakeCursor(self)

    def close(self):
        self.closed = True


def test_get_pairs_with_min_rounds_fallbacks_to_primary_when_replica_connect_fails():
    replica_db_url = "postgresql://replica-host:5432/inty"
    primary_db_url = "postgresql://primary-host:5432/inty"
    primary_conn = _FakeConnection(
        fetchall_results=[
            [("user-1", "agent-1", "chat-1"), ("user-2", "agent-2", "chat-2")],
            [("session-chat-1", 20), ("session-chat-2", 10)],
        ]
    )

    with (
        patch.object(
            festival_memory_service,
            "global_config_loaded_from_config_yaml",
            MagicMock(database=MagicMock(url=primary_db_url)),
        ),
        patch.object(
            festival_memory_service.psycopg,
            "connect",
            side_effect=[
                psycopg.OperationalError("replica down"),
                primary_conn,
            ],
        ) as mock_connect,
        patch.object(
            festival_memory_service,
            "generate_session_id",
            side_effect=lambda chat_id: f"session-{chat_id}",
        ),
    ):
        pairs = (
            festival_memory_service.get_pairs_with_min_rounds_in_window_sync(
                festival_date=date(2026, 2, 14),
                db_url=replica_db_url,
                min_rounds=15,
                timezone_str="UTC",
            )
        )

    assert pairs == [("user-1", "agent-1")]
    assert mock_connect.call_count == 2
    assert mock_connect.call_args_list[0].args[0] == replica_db_url
    assert mock_connect.call_args_list[1].args[0] == primary_db_url
    assert primary_conn.closed is True


def test_get_pairs_with_min_rounds_skips_official_assistant_agent():
    primary_db_url = "postgresql://primary-host:5432/inty"
    official_agent_id = festival_memory_service.INTELLIMATE_OFFICIAL_AGENT_ID
    primary_conn = _FakeConnection(
        fetchall_results=[
            [
                ("user-1", official_agent_id, "chat-official"),
                ("user-2", "agent-2", "chat-2"),
            ],
            [("session-chat-official", 20), ("session-chat-2", 20)],
        ]
    )

    with (
        patch.object(
            festival_memory_service,
            "global_config_loaded_from_config_yaml",
            MagicMock(database=MagicMock(url=primary_db_url)),
        ),
        patch.object(
            festival_memory_service.psycopg,
            "connect",
            return_value=primary_conn,
        ),
        patch.object(
            festival_memory_service,
            "generate_session_id",
            side_effect=lambda chat_id: f"session-{chat_id}",
        ),
    ):
        pairs = (
            festival_memory_service.get_pairs_with_min_rounds_in_window_sync(
                festival_date=date(2026, 2, 14),
                db_url=primary_db_url,
                min_rounds=15,
                timezone_str="UTC",
            )
        )

    assert pairs == [("user-2", "agent-2")]


def test_get_messages_for_user_agent_sync_prefers_replica_connection():
    replica_conn = _FakeConnection(
        fetchone_results=[("chat-1",)],
        fetchall_results=[
            [
                ({"type": "human", "data": {"content": "hi"}},),
                ({"type": "ai", "data": {"content": "hello"}},),
            ]
        ],
    )

    with (
        patch.object(
            festival_memory_service,
            "get_chat_history_replica_connection",
            return_value=replica_conn,
        ) as mock_replica_conn,
        patch.object(
            festival_memory_service, "get_chat_history_connection"
        ) as mock_primary_conn,
        patch.object(
            festival_memory_service,
            "generate_session_id",
            return_value="session-chat-1",
        ),
    ):
        rows = festival_memory_service.get_messages_for_user_agent_sync(
            "user-1",
            "agent-1",
            prefer_replica_read=True,
        )

    assert rows == [("user", "hi"), ("assistant", "hello")]
    mock_replica_conn.assert_called_once()
    mock_primary_conn.assert_not_called()


def test_get_messages_for_user_agent_sync_fallbacks_to_primary_when_replica_fails():
    primary_conn = _FakeConnection(
        fetchone_results=[("chat-1",)],
        fetchall_results=[
            [
                ({"type": "human", "data": {"content": "fallback"}},),
            ]
        ],
    )

    with (
        patch.object(
            festival_memory_service,
            "get_chat_history_replica_connection",
            side_effect=psycopg.OperationalError("replica unavailable"),
        ),
        patch.object(
            festival_memory_service,
            "get_chat_history_connection",
            return_value=primary_conn,
        ) as mock_primary_conn,
        patch.object(
            festival_memory_service,
            "generate_session_id",
            return_value="session-chat-1",
        ),
    ):
        rows = festival_memory_service.get_messages_for_user_agent_sync(
            "user-1",
            "agent-1",
            prefer_replica_read=True,
        )

    assert rows == [("user", "fallback")]
    mock_primary_conn.assert_called_once()


def test_get_messages_for_user_agent_sync_logs_skipped_malformed_messages():
    primary_conn = _FakeConnection(
        fetchone_results=[("chat-1",)],
        fetchall_results=[
            [
                ("not-json",),
                ('["not", "an", "object"]',),
                ({"type": "human", "data": {"content": "kept"}},),
            ]
        ],
    )

    with (
        patch.object(
            festival_memory_service,
            "get_chat_history_connection",
            return_value=primary_conn,
        ),
        patch.object(
            festival_memory_service,
            "generate_session_id",
            return_value="session-chat-1",
        ),
        patch.object(festival_memory_service.logger, "warning") as mock_warning,
    ):
        rows = festival_memory_service.get_messages_for_user_agent_sync(
            "user-1",
            "agent-1",
        )

    assert rows == [("user", "kept")]
    assert mock_warning.call_count == 2
