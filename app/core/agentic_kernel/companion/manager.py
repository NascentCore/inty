"""CompanionManager: 管理 companion session 的生命周期。"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from .bootstrap import run_workspace_bootstrap_loop
from .llm_client import CompanionLLMClient, CompanionLLMConfig
from .memory_pipeline import MemoryPipelineConfig
from .transcript_compaction import CompactionConfig
from .memory_registry import get_memory_store, shutdown_memory_store
from .memory_store import MemoryStore
from .file_store import write_text
from .turn import run_turn
from .workspace import (
    WorkspacePaths,
    is_workspace_initialized_from_store,
    needs_startup_profile_inquiry,
)


class CompanionConfig(BaseModel):
    """集中管理 companion 所有可调参数。"""

    # workspace 根目录基路径；每个 session 在其下创建子目录
    workspaces_base_dir: str = "/tmp/companion_workspaces"

    # LLM 配置
    llm: CompanionLLMConfig = Field(default_factory=CompanionLLMConfig)

    # 记忆管线配置
    memory: MemoryPipelineConfig = Field(default_factory=MemoryPipelineConfig)

    # PostgreSQL DSN for memory store (空串 = 纯内存 + 可选磁盘回退，见 memory_allow_workspace_disk_fallback)
    memory_pg_dsn: str = ""
    memory_pg_table: str = "companion_memory_doc_versions"
    memory_mirror_to_files: bool = False
    memory_allow_workspace_disk_fallback: bool = False

    # Bootstrap
    bootstrap_max_rounds: int = 48

    # Context
    default_context_mode: str = "intimate"

    # Optional: fold older transcript dialogue into a structured system snapshot when
    # the OpenAI message list exceeds a character budget (see transcript_compaction).
    transcript_compaction: CompactionConfig | None = None
    # When transcript_compaction is set, cap transcript rows before compaction; None
    # uses companion.models.TRANSCRIPT_WINDOW_MAX_MESSAGES.
    transcript_llm_window_max_messages: int | None = None


def _store_allow_disk_fallback(cfg: CompanionConfig) -> bool:
    if not cfg.memory_pg_dsn.strip():
        return True
    return cfg.memory_allow_workspace_disk_fallback


class CompanionSession:
    """封装单个 user+companion 会话的 runtime state。"""

    def __init__(
        self,
        *,
        user_id: str,
        companion_id: str,
        chat_id: str,
        workspace_path: Path,
        store: MemoryStore,
        llm_client: CompanionLLMClient,
        config: CompanionConfig,
    ) -> None:
        self.user_id = user_id
        self.companion_id = companion_id
        self.chat_id = chat_id
        self.workspace_path = workspace_path
        self.store = store
        self.llm_client = llm_client
        self.config = config
        self._lock = threading.Lock()

    @property
    def is_initialized(self) -> bool:
        return is_workspace_initialized_from_store(self.workspace_path, self.store)

    @property
    def needs_profile_inquiry(self) -> bool:
        return needs_startup_profile_inquiry(self.workspace_path, self.store)


class CompanionManager:
    """管理所有活跃 companion session 的生命周期。"""

    def __init__(self, config: CompanionConfig) -> None:
        self._config = config
        self._sessions: dict[str, CompanionSession] = {}
        self._lock = threading.Lock()
        self._llm_client = CompanionLLMClient(config.llm)

    @staticmethod
    def _session_key(user_id: str, companion_id: str, chat_id: str) -> str:
        return f"{user_id}:{companion_id}:{chat_id}"

    def _workspace_path(self, user_id: str, companion_id: str, chat_id: str) -> Path:
        base = Path(self._config.workspaces_base_dir)
        return base / user_id / companion_id / chat_id

    def get_or_create_session(
        self,
        user_id: str,
        companion_id: str,
        chat_id: str,
    ) -> CompanionSession:
        key = self._session_key(user_id, companion_id, chat_id)
        with self._lock:
            existing = self._sessions.get(key)
            if existing is not None:
                return existing

            ws_path = self._workspace_path(user_id, companion_id, chat_id)
            ws_path.mkdir(parents=True, exist_ok=True)

            store = get_memory_store(
                ws_path,
                dsn=self._config.memory_pg_dsn,
                table_name=self._config.memory_pg_table,
                mirror_to_files=self._config.memory_mirror_to_files,
                allow_workspace_disk_fallback=_store_allow_disk_fallback(self._config),
            )

            # 写入 context.json (如果不存在)
            context_path = ws_path / "context.json"
            if not context_path.is_file():
                context_data = {
                    "context_mode": self._config.default_context_mode,
                    "user_id": user_id,
                    "companion_id": companion_id,
                    "chat_id": chat_id,
                }
                write_text(
                    context_path,
                    json.dumps(context_data, indent=2, ensure_ascii=False) + "\n",
                )

            session = CompanionSession(
                user_id=user_id,
                companion_id=companion_id,
                chat_id=chat_id,
                workspace_path=ws_path,
                store=store,
                llm_client=self._llm_client,
                config=self._config,
            )
            self._sessions[key] = session
            logger.info(
                "companion_manager session_created user={} companion={} chat={} ws={}",
                user_id,
                companion_id,
                chat_id,
                ws_path,
            )
            return session

    async def bootstrap_session(
        self,
        session: CompanionSession,
        user_message: str,
    ) -> str:
        """对未初始化的 session 执行 agentic bootstrap。返回第一条 assistant 消息。"""
        if session.is_initialized:
            logger.info(
                "companion_manager bootstrap_skipped (already initialized) user={} companion={}",
                session.user_id,
                session.companion_id,
            )
            return ""

        def _chat_fn(messages: list[dict[str, Any]], model: str, tools: list) -> Any:
            return session.llm_client.chat_completion(
                messages=messages,
                model=model,
                tools=tools,
            )

        return await run_workspace_bootstrap_loop(
            session.workspace_path,
            user_message,
            store=session.store,
            chat_completion_fn=_chat_fn,
            model=session.llm_client._resolve_model("tool"),
            max_rounds=session.config.bootstrap_max_rounds,
        )

    async def run_turn(
        self,
        session: CompanionSession,
        user_text: str,
        *,
        heartbeat_turn: bool = False,
        defer_memory_update: bool = True,
    ) -> str:
        """执行一轮对话。"""
        return await run_turn(
            session.workspace_path,
            user_text,
            store=session.store,
            llm_client=session.llm_client,
            heartbeat_turn=heartbeat_turn,
            defer_memory_update=defer_memory_update,
            memory_config=session.config.memory,
            transcript_compaction=session.config.transcript_compaction,
            transcript_llm_window_max_messages=session.config.transcript_llm_window_max_messages,
        )

    def shutdown_session(
        self,
        user_id: str,
        companion_id: str,
        chat_id: str,
    ) -> None:
        key = self._session_key(user_id, companion_id, chat_id)
        with self._lock:
            session = self._sessions.pop(key, None)
        if session is None:
            return
        shutdown_memory_store(session.workspace_path)
        logger.info(
            "companion_manager session_shutdown user={} companion={} chat={}",
            user_id,
            companion_id,
            chat_id,
        )

    def shutdown_all(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            shutdown_memory_store(session.workspace_path)
        logger.info("companion_manager all_sessions_shutdown count={}", len(sessions))
