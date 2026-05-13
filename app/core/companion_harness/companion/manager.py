"""CompanionManager: 管理 companion session 的生命周期。

每个 ``CompanionSession`` 持有 ``tool_bg_idle``（``threading.Event``），用于在下一轮
``run_turn`` 加载 transcript 之前等待上一轮异步 tool_background 线程结束。
"""

from __future__ import annotations

import json
import threading

from loguru import logger
from pydantic import BaseModel, Field, field_validator

from app.core.companion_harness.experience_profile import (
    ExperienceContextMode,
    normalize_experience_profile_id,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.config import CompanionMemoryBootstrapType
from living_sphere.seeding import ensure_living_sphere_seeded
from techno_core.seeding import ensure_techno_core_seeded

from .langsmith_parent_policy import (
    companion_turn_langsmith_parent_enabled_from_app_config,
)
from .llm_client import CompanionLLMClient, CompanionLLMConfig
from app.core.companion_harness.memory.memory_pipeline import MemoryPipelineConfig
from app.core.companion_harness.memory.transcript_compaction import CompactionConfig
from app.core.companion_harness.memory.memory_registry import get_memory_store, shutdown_memory_store
from app.core.companion_harness.memory.memory_store import MemoryStore
from .models import CompanionTurnResult, InnerTickMode
from .scope import CompanionScope
from .turn import run_turn
from .turn_routes import BackgroundToolEventSink
from app.core.companion_harness.memory.memory_store_scope import (
    ensure_minimal_documents_in_store,
    is_scope_initialized_in_store,
    needs_startup_profile_inquiry,
)


def _migrate_interactive_bootstrap_context_if_needed(
    store: MemoryStore,
    parsed_ctx: dict[str, object],
    *,
    default_context_mode: str,
) -> None:
    if parsed_ctx.get("workspace_bootstrap_user_interactive_completed") is not False:
        return
    fixed = dict(parsed_ctx)
    bootstrap_id = ExperienceContextMode.BOOTSTRAP.value
    try:
        cm = normalize_experience_profile_id(str(fixed.get("context_mode", "")))
    except ValueError:
        cm = ""
    if cm != bootstrap_id:
        fixed["context_mode"] = bootstrap_id
    pb_raw = str(fixed.get("post_bootstrap_context_mode", "")).strip()
    if not pb_raw:
        fixed["post_bootstrap_context_mode"] = default_context_mode
    else:
        try:
            pbn = normalize_experience_profile_id(pb_raw)
        except ValueError:
            fixed["post_bootstrap_context_mode"] = default_context_mode
        else:
            if pbn == bootstrap_id:
                fixed["post_bootstrap_context_mode"] = default_context_mode
            else:
                fixed["post_bootstrap_context_mode"] = pbn
    if json.dumps(fixed, sort_keys=True) != json.dumps(parsed_ctx, sort_keys=True):
        store.write_document(
            "context.json",
            json.dumps(fixed, indent=2, ensure_ascii=False) + "\n",
        )


class CompanionConfig(BaseModel):
    """集中管理 companion 所有可调参数。"""

    # LLM 配置
    llm: CompanionLLMConfig = Field(default_factory=CompanionLLMConfig)

    # 记忆管线配置
    memory: MemoryPipelineConfig = Field(default_factory=MemoryPipelineConfig)

    # PostgreSQL: non-empty DSN enables ORM-backed MemoryStore (companion_memory_document_versions).
    memory_pg_dsn: str = ""

    # Transcript/context/ai_private 等与约定 md 一律仅走 MemoryStore（见 companion_tool_runtime）
    repository_only_store_text: bool = True

    # Bootstrap: app.features.companion_memory_bootstrap_type (NONE | USER_INTERACTIVE).
    memory_bootstrap_type: str = CompanionMemoryBootstrapType.NONE.value

    # Context: default experience profile id written to new sessions (context.json context_mode).
    default_context_mode: str = "intimate"

    # Optional: fold older transcript dialogue into a structured system snapshot when
    # the OpenAI message list exceeds a character budget (see transcript_compaction).
    transcript_compaction: CompactionConfig | None = None
    # When transcript_compaction is set, cap transcript rows before compaction; None
    # uses companion.models.TRANSCRIPT_WINDOW_MAX_MESSAGES.
    transcript_llm_window_max_messages: int | None = None

    # None: LangSmith companion parent RunTree follows app-wide policy
    # (``companion_turn_langsmith_parent_enabled_from_app_config``). True/False: force on or off
    # for all ``CompanionManager.run_turn`` calls using this config.
    langsmith_companion_parent_run_enabled: bool | None = None

    @field_validator("default_context_mode")
    @classmethod
    def _validate_default_context_mode(cls, v: str) -> str:
        n = normalize_experience_profile_id(v)
        if n == ExperienceContextMode.BOOTSTRAP:
            raise ValueError("default_context_mode cannot be 'bootstrap'")
        return n


class CompanionSession:
    """封装单个 user+companion 会话的 runtime state。"""

    def __init__(
        self,
        *,
        scope: CompanionScope,
        store: MemoryStore,
        llm_client: CompanionLLMClient,
        config: CompanionConfig,
    ) -> None:
        self.scope = scope
        self.user_id = scope.user_id
        self.companion_id = scope.companion_id
        self.chat_id = scope.chat_id
        self.store = store
        self.llm_client = llm_client
        self.config = config
        self.tool_bg_idle = threading.Event()
        self.tool_bg_idle.set()

    @property
    def is_initialized(self) -> bool:
        return is_scope_initialized_in_store(self.store)

    @property
    def needs_profile_inquiry(self) -> bool:
        return needs_startup_profile_inquiry(self.store)


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

            scope = CompanionScope(user_id, companion_id, chat_id)
            store = get_memory_store(scope, dsn=self._config.memory_pg_dsn)

            user_interactive = (
                self._config.memory_bootstrap_type
                == CompanionMemoryBootstrapType.USER_INTERACTIVE.value
            )
            existing_ctx = store.read_document_if_exists("context.json")
            parsed_ctx: dict[str, object] | None = None
            write_full_context = False
            if existing_ctx is None:
                write_full_context = True
            else:
                stripped = str(existing_ctx).strip()
                if not stripped:
                    write_full_context = True
                else:
                    try:
                        loaded = json.loads(stripped)
                    except json.JSONDecodeError:
                        write_full_context = True
                    else:
                        if isinstance(loaded, dict):
                            parsed_ctx = loaded
                        else:
                            write_full_context = True
                        if (
                            isinstance(parsed_ctx, dict)
                            and len(parsed_ctx) == 0
                            and user_interactive
                        ):
                            write_full_context = True
            if write_full_context:
                context_data: dict[str, object] = {
                    "user_id": user_id,
                    "companion_id": companion_id,
                    "chat_id": chat_id,
                }
                if user_interactive:
                    context_data["context_mode"] = ExperienceContextMode.BOOTSTRAP.value
                    context_data["post_bootstrap_context_mode"] = (
                        self._config.default_context_mode
                    )
                    context_data["workspace_bootstrap_user_interactive_completed"] = (
                        False
                    )
                    context_data["companion_ws_session_system_written"] = False
                else:
                    context_data["context_mode"] = self._config.default_context_mode
                context_json = (
                    json.dumps(context_data, indent=2, ensure_ascii=False) + "\n"
                )
                store.write_document("context.json", context_json)
            elif user_interactive and isinstance(parsed_ctx, dict):
                _migrate_interactive_bootstrap_context_if_needed(
                    store,
                    parsed_ctx,
                    default_context_mode=self._config.default_context_mode,
                )

            ensure_minimal_documents_in_store(store)
            ensure_techno_core_seeded(store)
            ensure_living_sphere_seeded(store)

            session = CompanionSession(
                scope=scope,
                store=store,
                llm_client=self._llm_client,
                config=self._config,
            )
            self._sessions[key] = session
            logger.info(
                "companion_manager session_created user={} companion={} chat={} scope={}",
                user_id,
                companion_id,
                chat_id,
                scope.registry_key(),
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
        override = session.config.langsmith_companion_parent_run_enabled
        ls_parent_enabled = (
            companion_turn_langsmith_parent_enabled_from_app_config()
            if override is None
            else override
        )
        return await run_turn(
            user_text,
            store=session.store,
            llm_client=session.llm_client,
            inner_tick_turn=inner_tick_turn,
            inner_tick_mode=inner_tick_mode,
            defer_memory_update=defer_memory_update,
            memory_config=session.config.memory,
            transcript_compaction=session.config.transcript_compaction,
            transcript_llm_window_max_messages=session.config.transcript_llm_window_max_messages,
            repository_only_store_text=session.config.repository_only_store_text,
            memory_bootstrap_type=session.config.memory_bootstrap_type,
            background_output_sink=background_output_sink,
            preset_user_msg_uuid=preset_user_msg_uuid,
            implicit_signal_bundle=implicit_signal_bundle,
            langsmith_parent_run_enabled=ls_parent_enabled,
            tool_bg_idle_event=session.tool_bg_idle,
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
        shutdown_memory_store(session.scope)
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
            shutdown_memory_store(session.scope)
        logger.info("companion_manager all_sessions_shutdown count={}", len(sessions))
