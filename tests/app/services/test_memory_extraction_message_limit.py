"""
测试记忆抽取消息数量限制功能
"""
import importlib
import sys
import types
from unittest.mock import patch

import pytest


def _load_memory_extraction_service_module():
    """加载记忆抽取服务模块（用于测试）"""
    fake_config = types.SimpleNamespace(
        database=types.SimpleNamespace(
            url="postgresql://primary-host:5432/inty",
            async_replica_url="postgresql+asyncpg://replica-host:5432/inty",
        ),
        memory_extraction=types.SimpleNamespace(
            trigger_new_user_messages=30,
            trigger_incremental_messages=30,
            model="",
            max_messages_for_extraction=1000,
        ),
    )
    fake_core_config_module = types.ModuleType("app.core.config")
    fake_core_config_module.global_config_loaded_from_config_yaml = fake_config

    fake_memory_model_module = types.ModuleType("app.models.memory")
    fake_memory_model_module.Memory = type("Memory", (), {})
    fake_memory_model_module.MemoryExtractionLog = type("MemoryExtractionLog", (), {})

    fake_chat_history_module = types.ModuleType("app.services.chat_history_service")
    fake_chat_history_module.get_chat_history_connection = lambda: None
    fake_chat_history_module.get_chat_history_replica_connection = lambda: None

    fake_chat_service_module = types.ModuleType("app.services.chat_service")
    fake_chat_service_module.generate_session_id = lambda chat_id: f"session-{chat_id}"

    fake_openrouter_module = types.ModuleType("app.utils.openrouter_memory")
    fake_openrouter_module.DEFAULT_MEMORY_EXTRACTION_MODEL = "mistralai/devstral-2512"

    fake_openai_client_module = types.ModuleType("app.utils.openai_client")

    async def _dummy_chat_completion_for_extraction(*args, **kwargs):
        return ("dummy", None, None)

    fake_openai_client_module.chat_completion_for_extraction = (
        _dummy_chat_completion_for_extraction
    )

    sys.modules.pop("app.services.memory_extraction_service", None)
    with patch.dict(
        sys.modules,
        {
            "app.core.config": fake_core_config_module,
            "app.models.memory": fake_memory_model_module,
            "app.services.chat_history_service": fake_chat_history_module,
            "app.services.chat_service": fake_chat_service_module,
            "app.utils.openai_client": fake_openai_client_module,
            "app.utils.openrouter_memory": fake_openrouter_module,
        },
    ):
        return importlib.import_module("app.services.memory_extraction_service")


service = _load_memory_extraction_service_module()


class _FakeCursor:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params):
        self._conn.executed.append((query, params))

    def fetchall(self):
        result = self._conn.fetchall_results[self._conn.fetchall_index]
        self._conn.fetchall_index += 1
        return result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self, fetchall_results):
        self.fetchall_results = fetchall_results
        self.fetchall_index = 0
        self.executed = []

    def cursor(self):
        return _FakeCursor(self)


def test_get_all_messages_respects_max_messages_limit():
    """测试消息数量限制：当提供 max_messages 参数时，应该限制返回的消息数量"""
    # 准备 5 条消息，但限制为 3 条
    conn = _FakeConnection(
        fetchall_results=[
            [("chat-1",)],  # 一个聊天会话
            [
                ({"type": "human", "data": {"content": "msg1"}},),
                ({"type": "ai", "data": {"content": "resp1"}},),
                ({"type": "human", "data": {"content": "msg2"}},),
                ({"type": "ai", "data": {"content": "resp2"}},),
                ({"type": "human", "data": {"content": "msg3"}},),  # 最新的 3 条从这里开始
            ],
        ]
    )

    with (
        patch.object(
            service,
            "get_chat_history_connection",
            return_value=conn,
        ),
        patch.object(
            service,
            "generate_session_id",
            side_effect=lambda chat_id: f"session-{chat_id}",
        ),
    ):
        # 调用函数，限制为 3 条消息
        rows = service.get_all_messages_for_user(
            "user-1", prefer_replica_read=False, max_messages=3
        )

    # 应该只返回最新的 3 条消息
    assert len(rows) == 3
    # 验证返回的是最新的消息（按时间升序）
    assert rows == [
        ("user", "msg2"),
        ("assistant", "resp2"),
        ("user", "msg3"),
    ]


def test_get_all_messages_no_limit_when_max_messages_none():
    """测试当 max_messages 为 None 时，不限制消息数量"""
    conn = _FakeConnection(
        fetchall_results=[
            [("chat-1",)],
            [
                ({"type": "human", "data": {"content": "msg1"}},),
                ({"type": "ai", "data": {"content": "resp1"}},),
                ({"type": "human", "data": {"content": "msg2"}},),
            ],
        ]
    )

    with (
        patch.object(
            service,
            "get_chat_history_connection",
            return_value=conn,
        ),
        patch.object(
            service,
            "generate_session_id",
            side_effect=lambda chat_id: f"session-{chat_id}",
        ),
    ):
        # 调用函数，不限制消息数
        rows = service.get_all_messages_for_user(
            "user-1", prefer_replica_read=False, max_messages=None
        )

    # 应该返回所有 3 条消息
    assert len(rows) == 3
    assert rows == [
        ("user", "msg1"),
        ("assistant", "resp1"),
        ("user", "msg2"),
    ]


def test_get_all_messages_query_includes_limit_clause():
    """测试当 max_messages > 0 时，SQL 查询包含 LIMIT 子句"""
    conn = _FakeConnection(
        fetchall_results=[
            [("chat-1",)],
            [({"type": "human", "data": {"content": "msg1"}},)],
        ]
    )

    with (
        patch.object(
            service,
            "get_chat_history_connection",
            return_value=conn,
        ),
        patch.object(
            service,
            "generate_session_id",
            side_effect=lambda chat_id: f"session-{chat_id}",
        ),
    ):
        service.get_all_messages_for_user(
            "user-1", prefer_replica_read=False, max_messages=100
        )

    # 检查执行的 SQL 查询
    executed_queries = conn.executed
    assert len(executed_queries) == 2  # 一次获取 chat_ids，一次获取消息

    # 第二个查询应该包含 LIMIT
    message_query, params = executed_queries[1]
    assert "LIMIT" in message_query
    # 参数列表最后一个应该是 limit 值
    assert params[-1] == 100
