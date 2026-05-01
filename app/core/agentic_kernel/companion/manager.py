"""CompanionManager: 管理 companion session 的生命周期。"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field, field_validator

from app.core.agentic_kernel.experience_profile import normalize_experience_profile_id
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.config import CompanionWorkspaceBootstrapType

from .llm_client import CompanionLLMClient, CompanionLLMConfig
from .memory_pipeline import MemoryPipelineConfig
from .transcript_compaction import CompactionConfig
from .memory_registry import get_memory_store, shutdown_memory_store
from .memory_store import MemoryStore
from .models import CompanionTurnResult, InnerTickMode
from .turn import run_turn
from .turn_routes import BackgroundToolEventSink
from .workspace import (
    ensure_minimal_workspace_documents_in_store,
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

    # PostgreSQL: non-empty DSN enables ORM-backed MemoryStore (app.models.companion_workspace).
    memory_pg_dsn: str = ""

    # Transcript/context/ai_private 等与约定 md 一律仅走 MemoryStore（见 companion_tool_runtime）
    repository_only_workspace_text: bool = True

    # Bootstrap: app.features.companion_workspace_bootstrap_type (NONE | USER_INTERACTIVE).
    workspace_bootstrap_type: str = CompanionWorkspaceBootstrapType.NONE.value

    # Context: default experience profile id written to new sessions (context.json context_mode).
    default_context_mode: str = "intimate"

    # Optional: fold older transcript dialogue into a structured system snapshot when
    # the OpenAI message list exceeds a character budget (see transcript_compaction).
    transcript_compaction: CompactionConfig | None = None
    # When transcript_compaction is set, cap transcript rows before compaction; None
    # uses companion.models.TRANSCRIPT_WINDOW_MAX_MESSAGES.
    transcript_llm_window_max_messages: int | None = None

    @field_validator("default_context_mode")
    @classmethod
    def _validate_default_context_mode(cls, v: str) -> str:
        return normalize_experience_profile_id(v)

    @property
    def skip_workspace_directory_creation(self) -> bool:
        """Session state does not require a directory under workspaces_base_dir."""
        return True


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

            store = get_memory_store(
                ws_path,
                dsn=self._config.memory_pg_dsn,
                user_id=user_id,
                companion_id=companion_id,
                chat_id=chat_id,
            )

            context_data = {
                "context_mode": self._config.default_context_mode,
                "user_id": user_id,
                "companion_id": companion_id,
                "chat_id": chat_id,
            }
            if (
                self._config.workspace_bootstrap_type
                == CompanionWorkspaceBootstrapType.USER_INTERACTIVE.value
            ):
                context_data["workspace_bootstrap_user_interactive_completed"] = False
                context_data["companion_ws_session_system_written"] = False
                context_data["companion_ws_interactive_kickoff_sent"] = False
            context_json = json.dumps(context_data, indent=2, ensure_ascii=False) + "\n"
            if store.read_document_if_exists("context.json") is None:
                store.write_document("context.json", context_json)

            ensure_minimal_workspace_documents_in_store(ws_path, store)

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

    async def run_turn(
        self,
        session: CompanionSession,
        user_text: str,
        *,
        inner_tick_turn: bool = False,
        inner_tick_mode: InnerTickMode = InnerTickMode.MAINTENANCE,
        defer_memory_update: bool = True,
        background_output_sink: BackgroundToolEventSink | None = None,
        preset_user_msg_uuid: str | None = None,
        implicit_signal_bundle: ImplicitSignalBundle | None = None,
    ) -> CompanionTurnResult:
        """执行一轮对话。"""
        return await run_turn(
            session.workspace_path,
            user_text,
            store=session.store,
            llm_client=session.llm_client,
            inner_tick_turn=inner_tick_turn,
            inner_tick_mode=inner_tick_mode,
            defer_memory_update=defer_memory_update,
            memory_config=session.config.memory,
            transcript_compaction=session.config.transcript_compaction,
            transcript_llm_window_max_messages=session.config.transcript_llm_window_max_messages,
            repository_only_workspace_text=session.config.repository_only_workspace_text,
            workspace_bootstrap_type=session.config.workspace_bootstrap_type,
            background_output_sink=background_output_sink,
            preset_user_msg_uuid=preset_user_msg_uuid,
            implicit_signal_bundle=implicit_signal_bundle,
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
        shutdown_memory_store(
            session.workspace_path,
            user_id=session.user_id,
            companion_id=session.companion_id,
            chat_id=session.chat_id,
        )
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
            shutdown_memory_store(
                session.workspace_path,
                user_id=session.user_id,
                companion_id=session.companion_id,
                chat_id=session.chat_id,
            )
        logger.info("companion_manager all_sessions_shutdown count={}", len(sessions))
