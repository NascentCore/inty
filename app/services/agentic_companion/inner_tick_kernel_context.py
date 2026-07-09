"""Build ``InnerTickKernelInput`` for presence and scope inner-tick glue."""

from __future__ import annotations

from app.core.agentic_companion.output_queue import (
    get_output_queue_for_scope,
)
from app.core.companion_harness.companion.manager import CompanionSession
from app.core.companion_harness.companion.runtime_channel import (
    TurnRuntimeContext,
)
from app.core.companion_harness.runtime.inner_tick_fire import (
    InnerTickKernelInput,
    InnerTickThrottleSnapshot,
)
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.services import companion_chat_service
from app.utils.models_catalog import GenAIModel


async def build_inner_tick_kernel_context(
    *,
    user_id: str,
    agent_id: str,
    chat_row_id: str | int,
    model_override: GenAIModel,
    throttle: InnerTickThrottleSnapshot,
    runtime_context: TurnRuntimeContext,
    preset_uid: str,
) -> tuple[InnerTickKernelInput, CompanionSession] | None:
    """Resolve MemoryStore + session and package kernel input for one inner-tick fire."""
    mem_store = companion_chat_service.companion_memory_store_if_ready(
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_row_id,
        resolved_chat_model=model_override,
    )
    if mem_store is None:
        return None

    manager, session = companion_chat_service._companion_manager_session_ref(
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_row_id,
        resolved_chat_model=model_override,
    )
    kernel_input = InnerTickKernelInput(
        manager=manager,
        session=session,
        mem_store=mem_store,
        throttle=throttle,
        runtime_context=runtime_context,
        preset_user_msg_uuid=preset_uid,
        agentic_output_queue=get_output_queue_for_scope(
            AgentScope(user_id=user_id, agent_id=agent_id)
        ),
    )
    return kernel_input, session
