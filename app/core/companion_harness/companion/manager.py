"""CompanionManager: 管理 companion session 的生命周期。

每个 ``CompanionSession`` 对应一个 **scope**（``user_id`` + ``companion_id`` + ``chat_id``）——
一份 MemoryStore，进程内单例。Prototype 假定每个 paired user 仅一条 presence（单 tab /
单 wire），见 ``companion_harness`` AGENTS.md「Concurrency (prototype)」。

每个 ``CompanionSession`` 还通过 ``turn_lock`` / ``tool_bg_idle`` 暴露 scope 级串行化状态
（``scope_turn_lock``；#3272）。
"""

from __future__ import annotations

import json
import threading

from loguru import logger
from pydantic import BaseModel, Field

from app.core.companion_harness.experience_profile.context_mode import (
    ExperienceContextMode,
)
from app.living_sphere.seeding import ensure_living_sphere_seeded
from app.techno_core.seeding import ensure_techno_core_seeded

from .langsmith_parent_policy import (
    companion_turn_langsmith_parent_enabled_from_app_config,
)
from app.core.llms.client import CompanionLLMConfig, LlmClient
from app.core.companion_harness.memory.transcript_compaction import (
    CompactionConfig,
)
from app.core.companion_harness.memory.memory_registry import (
    MEMORY_STORE_REGISTRY_REQUIRES_DSN,
    get_memory_store,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    CONTEXT_JSON_REL,
)
from .models import CompanionTurnResult, CompanionTurnTrack
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from .scope import CompanionScope
from .scope_turn_lock import (
    ScopeTurnLock,
    get_scope_tool_bg_idle,
    get_scope_turn_lock,
)
from .turn_deps import CompanionTurnDeps
from .turn import (
    run_companion_implicit_sign_on_greeting_turn,
    run_companion_inner_tick_monolog_turn,
    run_companion_inner_tick_proactive_chat_turn,
    run_companion_inner_tick_scheduled_turn,
    run_companion_user_chat_turn,
    run_inner_tick_autonomy,
)
from app.core.companion_harness.memory.memory_store_scope import (
    ensure_minimal_documents_in_store,
    is_scope_initialized_in_store,
)
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputQueue,
    get_output_queue_for_scope,
)
from app.core.companion_harness.agentic_companion.types import (
    UserMessageBatch,
    synthetic_user_message_batch,
)


class CompanionConfig(BaseModel):
    """集中管理 companion 所有可调参数。"""

    # LLM 配置
    llm: CompanionLLMConfig = Field(default_factory=CompanionLLMConfig)

    # PostgreSQL: non-empty DSN enables ORM-backed MemoryStore (companion_memory_document_versions).
    memory_pg_dsn: str = ""

    # Transcript/context/ai_private 等与约定 md 一律仅走 MemoryStore（见 companion_tool_runtime）
    repository_only_store_text: bool = True

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


class CompanionSession:
    """封装单个 user+companion 会话的 runtime state。"""

    def __init__(
        self,
        *,
        scope: CompanionScope,
        store: MemoryStore,
        llm_client: LlmClient,
        config: CompanionConfig,
    ) -> None:
        self.scope = scope
        self.user_id = scope.user_id
        self.companion_id = scope.companion_id
        self.chat_id = scope.chat_id
        self.store = store
        self.llm_client = llm_client
        self.config = config

    @property
    def tool_bg_idle(self) -> threading.Event:
        """Scope-level tool_background idle gate (singleton per ``CompanionScope``)."""
        return get_scope_tool_bg_idle(self.scope)

    @property
    def is_initialized(self) -> bool:
        return is_scope_initialized_in_store(self.store)

    @property
    def turn_lock(self) -> ScopeTurnLock:
        """Scope-level turn serializer (singleton per ``CompanionScope.registry_key()``)."""
        return get_scope_turn_lock(self.scope)


class CompanionManager:
    """管理所有活跃 companion session 的生命周期。

    TODO(companion-session-eviction): ``_sessions`` is append-only today; evict when scope — #3444
    has no active presence and no in-flight turns/tool_background.
    https://github.com/NascentCore/inty/issues/3444
    """

    def __init__(
        self,
        config: CompanionConfig,
        llm_client: LlmClient | None = None,
    ) -> None:
        self._config = config
        self._sessions: dict[str, CompanionSession] = {}
        self._lock = threading.Lock()
        self._llm_client = (
            llm_client if llm_client is not None else LlmClient(config.llm)
        )

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

            existing_ctx = store.read_document_if_exists(CONTEXT_JSON_REL)
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
                        ):
                            write_full_context = True
            if write_full_context:
                context_data: dict[str, object] = {
                    "user_id": user_id,
                    "companion_id": companion_id,
                    "chat_id": chat_id,
                    "context_mode": ExperienceContextMode.UNSPECIFIC.value,
                    "workspace_bootstrap_user_interactive_completed": False,
                    "companion_ws_session_system_written": False,
                }
                context_json = (
                    json.dumps(context_data, indent=2, ensure_ascii=False)
                    + "\n"
                )
                store.write_document(CONTEXT_JSON_REL, context_json)
            ensure_minimal_documents_in_store(store)
            ensure_techno_core_seeded(store)
            ensure_living_sphere_seeded(store)
            # TODO(#3471): ensure_token_budget_seeded(store, initial_budget=...) on session init (#3476 deferred).

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

    def _agent_scope_for_session(self, session: CompanionSession) -> AgentScope:
        companion_scope = session.store.scope
        return AgentScope(
            user_id=companion_scope.user_id,
            agent_id=companion_scope.companion_id,
        )

    def _resolve_agentic_queue_serving(
        self,
        session: CompanionSession,
        *,
        agentic_output_queue: OutputQueue | None,
        user_message_batch: UserMessageBatch | None,
        preset_user_msg_uuid: str | None,
        track_label: str,
    ) -> tuple[OutputQueue, UserMessageBatch | None]:
        """Ensure every turn has a scope ``OutputQueue``; synthesize batch when possible.

        Synthetic ``agent-initiated:`` batches from ``preset_user_msg_uuid`` are
        backup-only for agent-initiated and direct settled ``USER_CHAT`` turns.
        ``USER_CHAT_BOOTSTRAP`` must receive a real InputQueue-claimed batch from
        queue-serving callers (#3466).
        """
        assert track_label != ""
        resolved_queue = agentic_output_queue
        if resolved_queue is None:
            resolved_queue = get_output_queue_for_scope(
                self._agent_scope_for_session(session)
            )
        resolved_batch = user_message_batch
        if resolved_batch is None and preset_user_msg_uuid is not None:
            resolved_batch = synthetic_user_message_batch(
                user_msg_uuid=preset_user_msg_uuid,
                track_label=track_label,
            )
        return resolved_queue, resolved_batch

    def _build_turn_deps(
        self,
        session: CompanionSession,
        *,
        preset_user_msg_uuid: str | None,
        runtime_context: TurnRuntimeContext,
        agentic_output_queue: OutputQueue,
        user_message_batch: UserMessageBatch | None,
        input_batch=None,
    ) -> CompanionTurnDeps:
        return CompanionTurnDeps(
            store=session.store,
            llm_client=session.llm_client,
            transcript_compaction=session.config.transcript_compaction,
            transcript_llm_window_max_messages=session.config.transcript_llm_window_max_messages,
            repository_only_store_text=session.config.repository_only_store_text,
            preset_user_msg_uuid=preset_user_msg_uuid,
            runtime_context=runtime_context,
            langsmith_parent_run_enabled=self._langsmith_parent_run_enabled(
                session
            ),
            tool_bg_idle_event=session.tool_bg_idle,
            agentic_output_queue=agentic_output_queue,
            user_message_batch=user_message_batch,
            input_batch=input_batch,
        )

    # TODO(companion-multimodal-user-turn): Phase 1c — accept ``CompanionUserTurnInput`` — #3293
    # https://github.com/NascentCore/inty/issues/3293
    # instead of ``user_text: str``; forward to ``run_companion_user_chat_turn``.
    async def run_user_chat_turn(
        self,
        session: CompanionSession,
        user_text: str,
        *,
        preset_user_msg_uuid: str | None = None,
        runtime_context: TurnRuntimeContext = TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        agentic_output_queue: OutputQueue | None = None,
        user_message_batch: UserMessageBatch | None = None,
        input_batch=None,
    ) -> CompanionTurnResult:
        agentic_output_queue, user_message_batch = (
            self._resolve_agentic_queue_serving(
                session,
                agentic_output_queue=agentic_output_queue,
                user_message_batch=user_message_batch,
                preset_user_msg_uuid=preset_user_msg_uuid,
                track_label=CompanionTurnTrack.USER_CHAT.value,
            )
        )
        return await run_companion_user_chat_turn(
            user_text,
            deps=self._build_turn_deps(
                session,
                preset_user_msg_uuid=preset_user_msg_uuid,
                runtime_context=runtime_context,
                agentic_output_queue=agentic_output_queue,
                user_message_batch=user_message_batch,
                input_batch=input_batch,
            ),
        )

    async def run_implicit_sign_on_greeting_turn(
        self,
        session: CompanionSession,
        user_text: str,
        *,
        preset_user_msg_uuid: str | None = None,
        runtime_context: TurnRuntimeContext = TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        agentic_output_queue: OutputQueue | None = None,
        user_message_batch: UserMessageBatch | None = None,
    ) -> CompanionTurnResult:
        agentic_output_queue, user_message_batch = (
            self._resolve_agentic_queue_serving(
                session,
                agentic_output_queue=agentic_output_queue,
                user_message_batch=user_message_batch,
                preset_user_msg_uuid=preset_user_msg_uuid,
                track_label=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING.value,
            )
        )
        return await run_companion_implicit_sign_on_greeting_turn(
            user_text,
            deps=self._build_turn_deps(
                session,
                preset_user_msg_uuid=preset_user_msg_uuid,
                runtime_context=runtime_context,
                agentic_output_queue=agentic_output_queue,
                user_message_batch=user_message_batch,
            ),
        )

    async def run_inner_tick_proactive_chat_turn(
        self,
        session: CompanionSession,
        *,
        preset_user_msg_uuid: str | None = None,
        runtime_context: TurnRuntimeContext = TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        agentic_output_queue: OutputQueue | None = None,
        user_message_batch: UserMessageBatch | None = None,
    ) -> CompanionTurnResult:
        agentic_output_queue, user_message_batch = (
            self._resolve_agentic_queue_serving(
                session,
                agentic_output_queue=agentic_output_queue,
                user_message_batch=user_message_batch,
                preset_user_msg_uuid=preset_user_msg_uuid,
                track_label=CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT.value,
            )
        )
        return await run_companion_inner_tick_proactive_chat_turn(
            deps=self._build_turn_deps(
                session,
                preset_user_msg_uuid=preset_user_msg_uuid,
                runtime_context=runtime_context,
                agentic_output_queue=agentic_output_queue,
                user_message_batch=user_message_batch,
            ),
        )

    async def run_inner_tick_scheduled_turn(
        self,
        session: CompanionSession,
        scheduled_user_text: str,
        *,
        preset_user_msg_uuid: str | None = None,
        runtime_context: TurnRuntimeContext = TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        agentic_output_queue: OutputQueue | None = None,
        user_message_batch: UserMessageBatch | None = None,
    ) -> CompanionTurnResult:
        agentic_output_queue, user_message_batch = (
            self._resolve_agentic_queue_serving(
                session,
                agentic_output_queue=agentic_output_queue,
                user_message_batch=user_message_batch,
                preset_user_msg_uuid=preset_user_msg_uuid,
                track_label=CompanionTurnTrack.INNER_TICK_SCHEDULED.value,
            )
        )
        return await run_companion_inner_tick_scheduled_turn(
            scheduled_user_text,
            deps=self._build_turn_deps(
                session,
                preset_user_msg_uuid=preset_user_msg_uuid,
                runtime_context=runtime_context,
                agentic_output_queue=agentic_output_queue,
                user_message_batch=user_message_batch,
            ),
        )

    async def run_inner_tick_monolog_turn(
        self,
        session: CompanionSession,
        *,
        preset_user_msg_uuid: str | None = None,
        runtime_context: TurnRuntimeContext = TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        agentic_output_queue: OutputQueue | None = None,
        user_message_batch: UserMessageBatch | None = None,
    ) -> CompanionTurnResult:
        agentic_output_queue, user_message_batch = (
            self._resolve_agentic_queue_serving(
                session,
                agentic_output_queue=agentic_output_queue,
                user_message_batch=user_message_batch,
                preset_user_msg_uuid=preset_user_msg_uuid,
                track_label=CompanionTurnTrack.INNER_TICK_MONOLOG.value,
            )
        )
        return await run_companion_inner_tick_monolog_turn(
            deps=self._build_turn_deps(
                session,
                preset_user_msg_uuid=preset_user_msg_uuid,
                runtime_context=runtime_context,
                agentic_output_queue=agentic_output_queue,
                user_message_batch=user_message_batch,
            ),
        )

    async def run_inner_tick_autonomy_turn(
        self,
        session: CompanionSession,
        *,
        preset_user_msg_uuid: str | None = None,
        runtime_context: TurnRuntimeContext = TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        agentic_output_queue: OutputQueue | None = None,
        user_message_batch: UserMessageBatch | None = None,
    ) -> CompanionTurnResult:
        agentic_output_queue, user_message_batch = (
            self._resolve_agentic_queue_serving(
                session,
                agentic_output_queue=agentic_output_queue,
                user_message_batch=user_message_batch,
                preset_user_msg_uuid=preset_user_msg_uuid,
                track_label=CompanionTurnTrack.INNER_TICK_AUTONOMY.value,
            )
        )
        return await run_inner_tick_autonomy(
            deps=self._build_turn_deps(
                session,
                preset_user_msg_uuid=preset_user_msg_uuid,
                runtime_context=runtime_context,
                agentic_output_queue=agentic_output_queue,
                user_message_batch=user_message_batch,
            ),
        )
