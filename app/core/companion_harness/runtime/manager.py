"""CompanionManager: 管理 companion session 的生命周期。

每个 ``CompanionSession`` 对应一个 **scope**（``user_id`` + ``companion_id`` + ``chat_id``）——
一份 MemoryStore，进程内单例。Prototype 假定每个 paired user 仅一条 presence（单 tab /
单 wire），见 ``companion_harness`` AGENTS.md「Concurrency (prototype)」。

每个 ``CompanionSession`` 还持有 ``tool_bg_idle`` — 上一轮 tool_background 是否结束；
下一轮 ``run_turn`` 加载 transcript 前等待。Dreaming 与用户 chat、inner-tick 在
**presence** ``Coordinator.turn_lock`` 上串行（见 ``session.Coordinator``）。
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
from app.utils.config import CompanionMemoryBootstrapType
from app.living_sphere.seeding import ensure_living_sphere_seeded
from app.techno_core.seeding import ensure_techno_core_seeded

from app.core.companion_harness.runtime.langsmith_parent_policy import (
    companion_turn_langsmith_parent_enabled_from_app_config,
)
from app.core.companion_harness.runtime.llm_client import (
    CompanionLLMClient,
    CompanionLLMConfig,
)
from app.core.companion_harness.memory.transcript_compaction import (
    CompactionConfig,
)
from app.core.companion_harness.memory.memory_registry import (
    MEMORY_STORE_REGISTRY_REQUIRES_DSN,
    get_memory_store,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from .models import CompanionTurnResult
from app.core.companion_harness.runtime.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from .scope import CompanionScope
from .turn_deps import CompanionTurnDeps
from app.core.companion_harness.runtime.turn_routes import (
    BackgroundToolEventSink,
    BootstrapInterimOutputSink,
)
from app.core.companion_harness.runtime.turn_tracks import (
    run_companion_implicit_sign_on_greeting_turn,
    run_companion_inner_tick_maintenance_turn,
    run_companion_inner_tick_proactive_chat_turn,
    run_companion_inner_tick_scheduled_turn,
    run_companion_user_chat_turn,
)
from app.core.companion_harness.memory.memory_store_scope import (
    ensure_minimal_documents_in_store,
    is_scope_initialized_in_store,
)


class CompanionConfig(BaseModel):
    """集中管理 companion 所有可调参数。"""

    # LLM 配置
    llm: CompanionLLMConfig = Field(default_factory=CompanionLLMConfig)

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
        # TODO(tool-bg-idle-starves-user-chat): Cleared by tool_background start; run_turn
        # awaits this before loading transcript. Wedged maintenance bg blocks user chat.
        # https://github.com/NascentCore/inty/issues/3123
        self.tool_bg_idle = threading.Event()
        self.tool_bg_idle.set()

    @property
    def is_initialized(self) -> bool:
        return is_scope_initialized_in_store(self.store)


class CompanionManager:
    """管理所有活跃 companion session 的生命周期。"""

    def __init__(self, config: CompanionConfig) -> None:
        self._config = config
        self._sessions: dict[str, CompanionSession] = {}
        self._lock = threading.Lock()
        # TODO(code-structure): This class holds too many objects, this llm client should not be a member of this class.
        # Instead, this should focus on managing the session lifecycle.
        # And let the caller to provide the llm client when needed.
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
            if not (self._config.memory_pg_dsn or "").strip():
                raise ValueError(MEMORY_STORE_REGISTRY_REQUIRES_DSN)
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
                    context_data["context_mode"] = (
                        ExperienceContextMode.UNSPECIFIC.value
                    )
                    context_data[
                        "workspace_bootstrap_user_interactive_completed"
                    ] = False
                    context_data["companion_ws_session_system_written"] = False
                else:
                    context_data["context_mode"] = (
                        self._config.default_context_mode
                    )
                context_json = (
                    json.dumps(context_data, indent=2, ensure_ascii=False)
                    + "\n"
                )
                store.write_document("context.json", context_json)
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

    def _langsmith_parent_run_enabled(self, session: CompanionSession) -> bool:
        override = session.config.langsmith_companion_parent_run_enabled
        return (
            companion_turn_langsmith_parent_enabled_from_app_config()
            if override is None
            else override
        )

    def _build_turn_deps(
        self,
        session: CompanionSession,
        *,
        background_output_sink: BackgroundToolEventSink | None,
        preset_user_msg_uuid: str | None,
        runtime_context: TurnRuntimeContext,
        bootstrap_interim_output_sink: BootstrapInterimOutputSink | None,
    ) -> CompanionTurnDeps:
        return CompanionTurnDeps(
            store=session.store,
            llm_client=session.llm_client,
            transcript_compaction=session.config.transcript_compaction,
            transcript_llm_window_max_messages=session.config.transcript_llm_window_max_messages,
            repository_only_store_text=session.config.repository_only_store_text,
            memory_bootstrap_type=session.config.memory_bootstrap_type,
            background_output_sink=background_output_sink,
            preset_user_msg_uuid=preset_user_msg_uuid,
            runtime_context=runtime_context,
            langsmith_parent_run_enabled=self._langsmith_parent_run_enabled(
                session
            ),
            tool_bg_idle_event=session.tool_bg_idle,
            bootstrap_interim_output_sink=bootstrap_interim_output_sink,
        )

    async def run_user_chat_turn(
        self,
        session: CompanionSession,
        user_text: str,
        *,
        background_output_sink: BackgroundToolEventSink | None = None,
        preset_user_msg_uuid: str | None = None,
        runtime_context: TurnRuntimeContext = TurnRuntimeContext(
            channel=CompanionRuntimeChannel.APP,
            implicit_signal_bundle=None,
        ),
        bootstrap_interim_output_sink: BootstrapInterimOutputSink | None = None,
    ) -> CompanionTurnResult:
        return await run_companion_user_chat_turn(
            user_text,
            deps=self._build_turn_deps(
                session,
                background_output_sink=background_output_sink,
                preset_user_msg_uuid=preset_user_msg_uuid,
                runtime_context=runtime_context,
                bootstrap_interim_output_sink=bootstrap_interim_output_sink,
            ),
        )

    async def run_implicit_sign_on_greeting_turn(
        self,
        session: CompanionSession,
        user_text: str,
        *,
        background_output_sink: BackgroundToolEventSink | None = None,
        preset_user_msg_uuid: str | None = None,
        runtime_context: TurnRuntimeContext = TurnRuntimeContext(
            channel=CompanionRuntimeChannel.APP,
            implicit_signal_bundle=None,
        ),
    ) -> CompanionTurnResult:
        return await run_companion_implicit_sign_on_greeting_turn(
            user_text,
            deps=self._build_turn_deps(
                session,
                background_output_sink=background_output_sink,
                preset_user_msg_uuid=preset_user_msg_uuid,
                runtime_context=runtime_context,
                bootstrap_interim_output_sink=None,
            ),
        )

    async def run_inner_tick_proactive_chat_turn(
        self,
        session: CompanionSession,
        *,
        background_output_sink: BackgroundToolEventSink | None = None,
        preset_user_msg_uuid: str | None = None,
        runtime_context: TurnRuntimeContext = TurnRuntimeContext(
            channel=CompanionRuntimeChannel.APP,
            implicit_signal_bundle=None,
        ),
    ) -> CompanionTurnResult:
        return await run_companion_inner_tick_proactive_chat_turn(
            deps=self._build_turn_deps(
                session,
                background_output_sink=background_output_sink,
                preset_user_msg_uuid=preset_user_msg_uuid,
                runtime_context=runtime_context,
                bootstrap_interim_output_sink=None,
            ),
        )

    async def run_inner_tick_scheduled_turn(
        self,
        session: CompanionSession,
        scheduled_user_text: str,
        *,
        background_output_sink: BackgroundToolEventSink | None = None,
        preset_user_msg_uuid: str | None = None,
        runtime_context: TurnRuntimeContext = TurnRuntimeContext(
            channel=CompanionRuntimeChannel.APP,
            implicit_signal_bundle=None,
        ),
    ) -> CompanionTurnResult:
        return await run_companion_inner_tick_scheduled_turn(
            scheduled_user_text,
            deps=self._build_turn_deps(
                session,
                background_output_sink=background_output_sink,
                preset_user_msg_uuid=preset_user_msg_uuid,
                runtime_context=runtime_context,
                bootstrap_interim_output_sink=None,
            ),
        )

    async def run_inner_tick_maintenance_turn(
        self,
        session: CompanionSession,
        *,
        background_output_sink: BackgroundToolEventSink | None = None,
        preset_user_msg_uuid: str | None = None,
        runtime_context: TurnRuntimeContext = TurnRuntimeContext(
            channel=CompanionRuntimeChannel.APP,
            implicit_signal_bundle=None,
        ),
    ) -> CompanionTurnResult:
        return await run_companion_inner_tick_maintenance_turn(
            deps=self._build_turn_deps(
                session,
                background_output_sink=background_output_sink,
                preset_user_msg_uuid=preset_user_msg_uuid,
                runtime_context=runtime_context,
                bootstrap_interim_output_sink=None,
            ),
        )
