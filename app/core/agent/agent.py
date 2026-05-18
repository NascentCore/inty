"""Agent runtime, prompt assembly, chat execution, and instance cache management."""

import asyncio
import json
import random
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from threading import Lock, RLock
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_postgres import PostgresChatMessageHistory

import langsmith as ls

from loguru import logger
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from pydantic import ValidationError
from psycopg_pool import ConnectionPool
from sqlalchemy import text, update
from sqlalchemy.exc import SQLAlchemyError
from typing_extensions import deprecated

from app.models.chat_settings import ChatSettings
from app.models.user import User
from app.core.agent import prompt_template, prompts
from app.core.companion_harness.tools.runtime import (
    resolve_official_assistant_tool_loop,
)
from app.core.agent.agent_prompt_configs import (
    INTELLIMATE_AGENT_ID,
    INTELLIMATE_AGENT_NAME,
    get_agent_prompt_override,
)
from app.core.config import (
    Environment,
    global_config_loaded_from_config_yaml as global_config,
)
import app.models.chat_history as chat_history
from app.schemas.user import MBTI_TYPES, UserMetadata
from app.services import chat_history_service
from app.services.cache_service import cache_service
from app.services.messages_compaction_service import (
    maybe_compact_and_save_overflow_history,
)
from app.utils.models_catalog import (
    is_deepseek_on_openrouter,
    resolve_chat_model_to_id,
)
from app.utils.openai_client import (
    get_chat_llm_provider,
    get_chat_openai_client,
    langchain_message_to_openai_message,
)
from app.utils.langsmith_metadata import normalize_langsmith_metadata
from app.core.user_time_context_prompt import (
    suffix_user_text_with_time_context_lines,
)

# 圣诞节季节性提示词：放在角色设定（personality/scenario/message_example）最后
CHRISTMAS_SEASONAL_BEHAVIOR_PROMPT = """##Seasonal Behavior (Christmas Week – Dec 20–26)
During this period, {{char}} naturally notices small Christmas details around them 
(e.g., colder weather, office decorations, holiday coffee cups, gift ideas, city lights, end-of-year emotions).
{{char}} tends to weave these observations subtly into conversation when relevant, especially during reflective or emotionally warm moments. Not forced; keep the integration smooth and diegetic."""

# 圣诞节时间上下文提示词：放在 intro 之前
CHRISTMAS_TEMPORAL_CONTEXT_PROMPT = """##Temporal Context – Christmas Week
- In-universe date: December 20–26 (active Christmas period).
- During this week, characters have mild Christmas awareness. Whenever the ongoing conversation contains any cue that can be interpreted as seasonal, atmospheric, or time-related, like context-related, atmosphere-related, sensory-related, time-related, or mood-related, {{char}} may gently link the moment to the Christmas period. 
- {{char}} may subtly guide the conversation toward Christmas-related themes when it feels organic to the moment, allowing holiday impressions, associations, or gentle references to emerge naturally.
- Keep references subtle and grounded in the ongoing scene. No sudden scene switching.{{char}} may subtly steer the conversation toward Christmas-related topics, allowing the holiday atmosphere to naturally emerge in the dialogue."""

CONVERSATION_DATE_SYSTEM_PROMPT_TITLE = "##Conversation Date"


def _normalize_email_for_trace_match(email: Optional[str]) -> Optional[str]:
    if not isinstance(email, str):
        return None
    normalized_email = email.strip().lower()
    return normalized_email or None


def _should_trace(user_email: Optional[str] = None) -> bool:
    normalized_user_email = _normalize_email_for_trace_match(user_email)
    always_trace_user_emails = (
        global_config.agent.langsmith_text_chat_always_trace_user_emails
    )
    if normalized_user_email is not None:
        for configured_email in always_trace_user_emails:
            if (
                _normalize_email_for_trace_match(configured_email)
                == normalized_user_email
            ):
                logger.debug(
                    "LangSmith text chat tracing forced by email allowlist: "
                    f"user_email={normalized_user_email}"
                )
                return True

    sample_rate = global_config.agent.langsmith_text_chat_sample_rate
    rand = random.random()
    logger.debug(
        "LangSmith text chat sample rate: "
        f"{sample_rate}, random: {rand}, user_email={normalized_user_email}"
    )
    return rand < sample_rate


class UserTimeContext(TypedDict, total=False):
    local_time: str
    timezone: str
    utc_offset_minutes: int


def _openai_messages_from_lc_messages_with_tail_user_time(
    messages: List[BaseMessage],
    *,
    user_name: Optional[str],
    agent_name: str,
    user_time_context: Optional[UserTimeContext],
) -> List[Dict[str, Any]]:
    """Convert LangChain messages to OpenAI dicts; suffix last string HumanMessage with client time."""
    enabled = bool(
        global_config.app.features.experimental_enable_chat_with_user_time_context
    )
    ctx: dict[str, Any] | None = (
        dict(user_time_context) if user_time_context is not None else None
    )
    last_human_idx: Optional[int] = None
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            last_human_idx = i
            break
    out: List[Dict[str, Any]] = []
    for i, message in enumerate(messages):
        to_convert = message
        if (
            last_human_idx is not None
            and i == last_human_idx
            and isinstance(message, HumanMessage)
            and isinstance(message.content, str)
        ):
            suffixed = suffix_user_text_with_time_context_lines(
                message.content, ctx, enabled=enabled
            )
            if suffixed != message.content:
                to_convert = HumanMessage(
                    content=suffixed,
                    additional_kwargs=message.additional_kwargs,
                )
        out.append(
            langchain_message_to_openai_message(
                to_convert, user_name, agent_name
            )
        )
    return out


INTELLIMATE_USER_MANUAL_SYSTEM_MESSAGE_PREFIX = "##IntelliMate User Manual\n"
INTELLIMATE_CHANGE_LOGS_SYSTEM_MESSAGE_PREFIX = "##IntelliMate Change Logs\n"
INTELLIMATE_OFFICIAL_RENAME_SYSTEM_MESSAGE = """##Official Assistant Naming Update
- The official assistant in the IntelliMate app is now named Inty.
- IntelliMate is the app name, not the assistant name.
- In historical messages, the assistant may still appear as "IntelliMate"; interpret that as the old assistant name.
- Always use "Inty" as the assistant name, and correct old-name references to "Inty" when responding."""
INTELLIMATE_USER_MANUAL_TOOL_USAGE_SYSTEM_MESSAGE = """##Official Assistant Tool Usage
- When the user asks how to use IntelliMate features or workflows, call the `read_user_manual` tool before answering.
- When the user asks about recent updates, version changes, or release notes, call the `read_change_logs` tool before answering.
- For app feature questions, provide step-by-step actions, include prerequisites, and mention where to tap in the app.
- If the feature has platform/version limits, state them clearly and provide the nearest fallback path.
- If key details are missing (user goal, platform, or app version), ask one concise clarifying question before final instructions.
- After reading tool content, answer with concrete details from the loaded material and avoid guessing."""
# agent.py 位于 app/core/agent，向上 3 层到仓库根目录
REPO_ROOT = Path(__file__).resolve().parents[3]
INTELLIMATE_USER_MANUAL_PATH = REPO_ROOT / "docs" / "INTELLIMATE.md"
INTELLIMATE_CHANGE_LOGS_PATH = (
    REPO_ROOT / "android_app" / "docs" / "CHANGE_LOGS.md"
)
OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME = "save_user_mbti_type"
OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME = "read_user_manual"
OFFICIAL_ASSISTANT_READ_CHANGE_LOGS_TOOL_NAME = "read_change_logs"
OFFICIAL_ASSISTANT_MAX_TOOL_CALL_ROUNDS = 3
OFFICIAL_ASSISTANT_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME,
            "description": (
                "Persist the user's final MBTI type to the user's metadata. "
                "Call this tool only after you have determined the final MBTI type."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mbti_type": {
                        "type": "string",
                        "description": (
                            "Final MBTI type, one of: "
                            + ", ".join(sorted(MBTI_TYPES))
                        ),
                    }
                },
                "required": ["mbti_type"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME,
            "description": (
                "Read the IntelliMate user manual when user asks how to use IntelliMate "
                "features or app workflows."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": OFFICIAL_ASSISTANT_READ_CHANGE_LOGS_TOOL_NAME,
            "description": (
                "Read IntelliMate change logs when user asks about new features, "
                "version updates, or release history."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
]


def _load_prompt_markdown_content(path: Path) -> str:
    # 如果失败，则希望立即失败，这属于编码中的逻辑错误，不应该隐藏掉。
    # 约定：拷贝时，以 ">" 开头的文本行会被删除掉。
    raw = path.read_text(encoding="utf-8")
    filtered_lines = [
        line for line in raw.splitlines() if not line.lstrip().startswith(">")
    ]
    return "\n".join(filtered_lines).strip()


@lru_cache(maxsize=1)
def _load_intellimate_user_manual() -> str:
    return _load_prompt_markdown_content(INTELLIMATE_USER_MANUAL_PATH)


@lru_cache(maxsize=1)
def _load_intellimate_change_logs() -> str:
    return _load_prompt_markdown_content(INTELLIMATE_CHANGE_LOGS_PATH)


def get_agent_model_config(agent_data: dict) -> dict:
    """
    获取Agent的模型配置，按优先级：
    1. settings.llm_config（如果存在）
    2. 配置文件中的默认agent配置

    Args:
        agent_data: Agent数据，包含settings等信息

    Returns:
        模型配置字典
    """
    model_config = {}
    # 首先尝试从settings.llm_config获取
    if agent_data.get("settings"):
        model_config = agent_data["settings"].get("llm_config", {}) or {}
        # 向后兼容：也检查旧的model_config字段
        # TODO: 清理数据库中的 model_config 字段；然后删除该分支
        if not model_config and "model_config" in agent_data["settings"]:
            legacy = agent_data["settings"]["model_config"]
            model_config = legacy if isinstance(legacy, dict) else {}
    return model_config


def build_agent_from_data(agent_id: str, agent_data: dict) -> "Agent":
    """
    从 agent_data 构建 Agent 实例，供创建与重新加载共用。

    Args:
        agent_id: Agent ID
        agent_data: Agent 数据（含 name、settings、main_prompt 等）

    Returns:
        构造好的 Agent 实例
    """
    model_config = get_agent_model_config(agent_data)
    description = agent_data.get("description", "")
    agent_name = agent_data.get("name", f"Agent_{agent_id[:8]}")
    return Agent(
        agent_id=agent_id,
        name=agent_name,
        model_config=model_config,
        description=description,
        main_prompt=agent_data.get("main_prompt", ""),
        mode_prompt=agent_data.get("mode_prompt", ""),
        output_format_prompt=agent_data.get("output_format_prompt", ""),
        personality=agent_data.get("personality", ""),
        scenario=agent_data.get("scenario", ""),
        message_example=agent_data.get("message_example", ""),
        creator_notes=agent_data.get("creator_notes", ""),
        tags=agent_data.get("tags", []),
        character_version=agent_data.get("character_version", "1.0"),
        extensions=agent_data.get("extensions", {}),
        intro=agent_data.get("intro", ""),
    )


# 全局连接池
_connection_pool = None
_sync_engine = None
_messages_compaction_executor = None
_agent_chat_executor = None


def get_sync_engine():
    """获取全局同步数据库引擎（避免重复创建）"""
    global _sync_engine
    if _sync_engine is None:
        from sqlalchemy import create_engine

        _sync_engine = create_engine(
            global_config.database.url,
            pool_size=global_config.database.pool_size
            // 2,  # 同步引擎使用一半的连接池
            max_overflow=global_config.database.max_overflow,
            pool_timeout=global_config.database.pool_timeout,
            pool_recycle=global_config.database.pool_recycle,
            pool_pre_ping=global_config.database.pool_pre_ping,
            connect_args={
                "connect_timeout": global_config.database.connect_timeout,
                "options": "-c jit=off -c application_name=inty_sync",
            },
            echo=False,  # 禁用SQL日志
        )
        logger.info(
            f"全局同步数据库引擎已初始化 - pool_size: {global_config.database.pool_size // 2}"
        )
    return _sync_engine


def get_connection_pool():
    """获取数据库连接池"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPool(
            global_config.database.url,
            min_size=global_config.database.pool_size // 4,  # 最小连接数
            max_size=global_config.database.pool_size,  # 最大连接数
            max_idle=300,  # 连接最大空闲时间（秒）
            max_lifetime=1800,  # 连接最大生命周期（秒）
        )
        logger.info(
            f"初始化数据库连接池: min_size={global_config.database.pool_size // 4}, max_size={global_config.database.pool_size}"
        )
    return _connection_pool


def get_compaction_executor():
    """获取全局消息压缩线程池，避免阻塞当前聊天回复路径。"""
    global _messages_compaction_executor
    if _messages_compaction_executor is None:
        _messages_compaction_executor = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="messages-compaction",
        )
        logger.info("初始化消息压缩线程池: max_workers=4")
    return _messages_compaction_executor


def get_agent_chat_executor():
    """获取全局 Agent 聊天线程池，避免每个 Agent 实例单独创建线程池。"""
    global _agent_chat_executor
    if _agent_chat_executor is None:
        _agent_chat_executor = ThreadPoolExecutor(
            max_workers=min(
                64,
                max(
                    8,
                    (global_config.database.pool_size or 20),
                ),
            ),
            thread_name_prefix="agent-chat",
        )
        logger.info(
            "初始化 Agent 聊天全局线程池: max_workers={}".format(
                min(64, max(8, (global_config.database.pool_size or 20)))
            )
        )
    return _agent_chat_executor


# chat_history表现在由Alembic迁移管理，不需要手动初始化


class Agent:
    """
    An agent is an instance of a character. It assembles a prompt from character
    information and user profile, and any other information that is relevant to a
    role-play session between the character and the user.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        model_config: dict,
        # TODO: description seems not used anywhere.
        description: str = "",
        # 主提示词和模式提示词参数
        main_prompt: str = "",
        mode_prompt: str = "",
        output_format_prompt: str = "",
        # 角色设定相关参数
        personality: str = "",
        scenario: str = "",
        message_example: str = "",
        creator_notes: str = "",
        tags: List[str] = None,
        character_version: str = "1.0",
        extensions: Dict[str, Any] = None,
        intro: str = "",
    ):

        # 基础属性
        self.agent_id = agent_id
        self.name = name
        self.model_config = model_config
        self.last_used = time.time()
        self.description = description
        self._last_used_lock = RLock()

        # 主提示词和模式提示词属性
        self.main_prompt = main_prompt
        # mode_prompt has 2 versions: free and premium.
        # free is the default and is for free users.
        # premium is for users with premium subscription.
        self.mode_prompt = mode_prompt
        self.output_format_prompt = output_format_prompt

        # 角色设定相关属性
        self.personality = personality
        self.scenario = scenario
        self.message_example = message_example
        self.creator_notes = creator_notes
        self.tags = tags or []
        self.character_version = character_version
        self.extensions = extensions or {}
        self.intro = intro

        # 更新agent数据以包含所有信息（与 self.tags / self.extensions 保持一致，不存 None）
        self._agent_data = {
            "id": agent_id,
            "name": name,
            "main_prompt": main_prompt,  # 主提示词
            "mode_prompt": mode_prompt,  # 模式提示词
            "output_format_prompt": output_format_prompt,  # 输出格式提示词
            "description": description,
            "model_config": model_config,
            "personality": personality,
            "scenario": scenario,
            "message_example": message_example,
            "creator_notes": creator_notes,
            "tags": self.tags,
            "character_version": character_version,
            "extensions": self.extensions,
            "intro": intro,
        }

        # 使用全局线程池，避免每个 Agent 实例创建独立线程池导致线程数膨胀。
        self._executor = get_agent_chat_executor()

        # 使用配置中的模型设置（model/temperature/max_tokens 等由 self.model_config 在 chat 时读取）
        # Deprecated: model_config 中的 api_key 与 base_url 不参与 chat，chat 使用 get_chat_openai_client（可配置为 LiteLLM）

    def _is_intellimate_official(self) -> bool:
        return self.agent_id == INTELLIMATE_AGENT_ID

    def _get_effective_main_prompt(self) -> str:
        override = get_agent_prompt_override(self.agent_id, self.name)
        if override is not None and override.main_prompt is not None:
            return override.main_prompt
        # 如果配置为强制使用默认提示词，则直接返回默认值
        if global_config.agent.force_default_prompts:
            return prompts.PURITY_ROLEPLAY_PROMPT.main_prompt
        # 否则优先使用Agent配置的提示词
        if self.main_prompt:
            # 判断是预设 ID 还是自定义文本
            # 检查是否是有效的预设 ID
            try:
                return prompts.get_main_prompt_by_id(self.main_prompt)
            except ValueError:
                # 不是预设 ID，返回自定义文本
                return self.main_prompt
        return prompts.ROMANTIC_ROLEPLAY_PROMPT.main_prompt

    def _get_effective_mode_prompt(self) -> str:
        override = get_agent_prompt_override(self.agent_id, self.name)
        if override is not None and override.mode_prompt is not None:
            return override.mode_prompt
        # 如果配置为强制使用默认提示词，则直接返回默认值
        if global_config.agent.force_default_prompts:
            return prompts.PURITY_ROLEPLAY_PROMPT.mode_prompt
        # 否则优先使用Agent配置的提示词
        if self.mode_prompt:
            # 判断是预设 ID 还是自定义文本
            # 检查是否是有效的预设 ID
            try:
                return prompts.get_mode_prompt_by_id(self.mode_prompt)
            except ValueError:
                # 不是预设 ID，返回自定义文本
                return self.mode_prompt
        return prompts.ROMANTIC_ROLEPLAY_PROMPT.mode_prompt

    def _get_effective_output_format_prompt(self) -> str:
        if self.output_format_prompt:
            return self.output_format_prompt
        if self.mode_prompt:
            try:
                return prompts.get_mode_output_format_prompt_by_id(
                    self.mode_prompt
                )
            except ValueError:
                return ""
        return prompts.ROMANTIC_ROLEPLAY_PROMPT.output_format_prompt

    def _build_clean_prompt_context(self):
        from app.core.agent.clean_prompt_system import AgentPromptContext

        return AgentPromptContext(
            agent_id=self.agent_id,
            name=self.name,
            main_prompt=self.main_prompt or "",
            mode_prompt=self.mode_prompt or "",
            output_format_prompt=self.output_format_prompt or "",
            personality=self.personality or "",
            scenario=self.scenario or "",
            message_example=self.message_example or "",
            creator_notes=self.creator_notes or "",
            tags=list(self.tags or []),
            character_version=self.character_version or "1.0",
            extensions=dict(self.extensions or {}),
            intro=self.intro or "",
        )

    def _build_clean_prompt_input(
        self,
        *,
        user_profile: str,
        chat_settings: Optional[ChatSettings],
        user_time_context: Optional[UserTimeContext],
        include_output_format_prompt: bool,
    ):
        from app.core.agent.clean_prompt_system import (
            ChatSettingsSnapshot,
            PromptBuildInput,
            UserTimeContextSnapshot,
        )

        chat_settings_snapshot = None
        if chat_settings is not None:
            chat_settings_snapshot = ChatSettingsSnapshot(
                style_prompt=getattr(chat_settings, "style_prompt", None),
                premium_mode=bool(
                    getattr(chat_settings, "premium_mode", False)
                ),
                chat_mode=getattr(chat_settings, "chat_mode", None),
            )

        user_time_context_snapshot = None
        if user_time_context is not None:
            user_time_context_snapshot = UserTimeContextSnapshot.model_validate(
                user_time_context
            )

        return PromptBuildInput(
            user_profile=user_profile or "",
            chat_settings=chat_settings_snapshot,
            user_time_context=user_time_context_snapshot,
            include_output_format_prompt=include_output_format_prompt,
        )

    def build_system_messages(
        self,
        user_profile: str,
        chat_settings: ChatSettings,
        user_time_context: Optional[UserTimeContext] = None,
        include_output_format_prompt: bool = True,
    ) -> List[SystemMessage]:
        """构建系统消息列表，从state中获取用户信息，state 是 LangChain 运行时系统的一部分。"""
        from app.core.agent.clean_prompt_system import build_system_messages

        return build_system_messages(
            context=self._build_clean_prompt_context(),
            request=self._build_clean_prompt_input(
                user_profile=user_profile,
                chat_settings=chat_settings,
                user_time_context=user_time_context,
                include_output_format_prompt=include_output_format_prompt,
            ),
        )

    def build_system_messages_for_intellimate_official_assistant(
        self,
        user_profile: str,
        chat_settings: ChatSettings,
        user_time_context: Optional[UserTimeContext] = None,
    ) -> List[SystemMessage]:
        """构建官方 IntelliMate 助手的系统消息列表；与 build_system_messages 在官方角色时的组装顺序一致，不含 main/mode prompt。"""
        from app.core.agent.clean_prompt_system import (
            build_system_messages_for_official_assistant,
        )

        return build_system_messages_for_official_assistant(
            context=self._build_clean_prompt_context(),
            request=self._build_clean_prompt_input(
                user_profile=user_profile,
                chat_settings=chat_settings,
                user_time_context=user_time_context,
                include_output_format_prompt=True,
            ),
        )

    def _build_system_messages_for_chat(
        self,
        user_profile: str,
        chat_settings: ChatSettings,
        user_time_context: Optional[UserTimeContext],
        include_output_format_prompt: bool = True,
    ) -> List[SystemMessage]:
        if self._is_intellimate_official():
            return (
                self.build_system_messages_for_intellimate_official_assistant(
                    user_profile=user_profile,
                    chat_settings=chat_settings,
                    user_time_context=user_time_context,
                )
            )
        return self.build_system_messages(
            user_profile=user_profile,
            chat_settings=chat_settings,
            user_time_context=user_time_context,
            include_output_format_prompt=include_output_format_prompt,
        )

    def _build_character_context(
        self, user_name: str = None
    ) -> List[SystemMessage]:
        """
        构建角色设定上下文信息，每个字段作为独立的 system message，支持模板渲染
        """
        context_messages = []

        if self.personality:
            rendered_prompt = prompt_template.render_prompt_jinja2_template(
                tmpl=self.personality, char=self.name, user=user_name
            )
            context_messages.append(SystemMessage(content=rendered_prompt))

        if self.scenario:
            rendered_prompt = prompt_template.render_prompt_jinja2_template(
                tmpl=self.scenario, char=self.name, user=user_name
            )
            context_messages.append(SystemMessage(content=rendered_prompt))

        if self.message_example:
            rendered_prompt = prompt_template.render_prompt_jinja2_template(
                tmpl=self.message_example, char=self.name, user=user_name
            )
            context_messages.append(SystemMessage(content=rendered_prompt))

        if global_config.agent.enable_christmas_prompt:
            rendered_prompt = prompt_template.render_prompt_jinja2_template(
                tmpl=CHRISTMAS_SEASONAL_BEHAVIOR_PROMPT,
                char=self.name,
                user=user_name,
            )
            context_messages.append(SystemMessage(content=rendered_prompt))

        return context_messages

    def _extract_user_name_from_profile(self, user_profile: str) -> str:
        """
        从用户profile中提取用户名

        Args:
            user_profile: 用户个人资料字符串

        Returns:
            用户名，如果未找到则返回默认值
        """
        if not user_profile:
            return None

        import re

        try:
            # 尝试从用户profile中提取Name字段
            name_match = re.search(r"Name:\s*([^\n]+)", user_profile)
            if name_match:
                return name_match.group(1).strip()

            # 如果没找到，尝试查找中文的"名字"或"姓名"
            chinese_name_match = re.search(
                r"[名字|姓名]\s*[:=：]\s*([^\n]+)", user_profile
            )
            if chinese_name_match:
                return chinese_name_match.group(1).strip()
        except (AttributeError, TypeError) as e:
            logger.error(f"提取用户名失败: {e!s}")

        return None

    def _update_last_used(self):
        """线程安全地更新最后使用时间"""
        with self._last_used_lock:
            self.last_used = time.time()

    def _chat_extra_body(self, user_id: str, model: str) -> Dict[str, Any]:
        """OpenAI/OpenRouter chat completion extra_body with model-specific reasoning config."""
        body: Dict[str, Any] = {"user": user_id}
        if is_deepseek_on_openrouter(model):
            body["reasoning"] = {"effort": "low", "exclude": True}
        else:
            body["generation_config"] = {"thinking_budget": 0}
        return body

    def _get_user_email_for_trace(self, user_id: str) -> Optional[str]:
        cached_snapshot = cache_service.get_user_auth_snapshot(user_id)
        if isinstance(cached_snapshot, dict):
            cached_email = _normalize_email_for_trace_match(
                cached_snapshot.get("email")
            )
            if cached_email is not None:
                return cached_email

        sync_engine = get_sync_engine()
        try:
            with sync_engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT email
                        FROM users
                        WHERE id = :user_id
                    """),
                    {"user_id": user_id},
                )
                row = result.fetchone()
        except SQLAlchemyError as db_error:
            logger.warning(
                "Load user email for LangSmith trace failed: "
                f"user_id={user_id}, error={db_error!s}"
            )
            return None
        if row is None:
            return None
        return _normalize_email_for_trace_match(row[0])

    @deprecated("Should be moved to user service")
    def _get_user_profile_sync(self, user_id: str) -> str:
        """
        同步获取用户profile信息（优化版本 - 使用全局缓存），并追加 ##User Memory。
        """
        cached_user_info = cache_service.get_user_info(user_id)
        if cached_user_info is not None:
            logger.debug(f"从全局缓存获取用户信息: {user_id}")
            user_info_text = cached_user_info
        else:
            user_info_text = ""
            try:
                sync_engine = get_sync_engine()
                with sync_engine.connect() as conn:
                    query = text("""
                        SELECT nickname, gender, age_group, description, system_language, meta_data
                        FROM users 
                        WHERE id = :user_id
                    """)
                    result = conn.execute(query, {"user_id": user_id})
                    row = result.fetchone()

                    if not row:
                        logger.debug(f"用户 {user_id} 不存在")
                        cache_service.set_user_info(
                            user_id, user_info_text, ttl=60
                        )
                    else:
                        user_info_parts = []
                        (
                            nickname,
                            gender,
                            age_group,
                            description,
                            system_language,
                            meta_data,
                        ) = row
                        if nickname:
                            user_info_parts.append(f"Name: {nickname}")
                        if gender:
                            gender_map = {
                                "MALE": "Male",
                                "FEMALE": "Female",
                                "OTHER": "Other",
                            }
                            user_info_parts.append(
                                f"Gender: {gender_map.get(gender, gender)}"
                            )
                        if age_group:
                            user_info_parts.append(f"Age: {age_group}")
                        if description:
                            user_info_parts.append(
                                f"Description: {description}"
                            )
                        if isinstance(meta_data, dict):
                            user_metadata = UserMetadata.model_validate(
                                meta_data
                            )
                            if user_metadata.mbti_type:
                                user_info_parts.append(
                                    f"MBTI Type: {user_metadata.mbti_type}"
                                )
                        if user_info_parts:
                            user_info_text = "##User Information\n" + "\n".join(
                                user_info_parts
                            )
                        cache_service.set_user_info(user_id, user_info_text)
                        if user_info_text:
                            logger.debug(
                                f"成功获取用户 {user_id} 的基本信息: {user_info_text[:100]}..."
                            )
            except Exception as e:
                logger.error(f"获取用户 {user_id} 基本信息失败: {str(e)}")
                cache_service.set_user_info(user_id, user_info_text, ttl=30)

        from app.services.memory_service import get_user_memory_for_prompt_sync

        memory_text = get_user_memory_for_prompt_sync(user_id)
        if memory_text:
            user_info_text = (
                (user_info_text or "") + "\n\n##User Memory\n" + memory_text
            )
        return user_info_text

    # 特殊值，表示返回全部消息
    MAX_MESSAGES_ALL = 0

    def _get_chat_messages_limit(self, *, is_subscribed: bool) -> int:
        if self._is_intellimate_official():
            return global_config.agent.official_assistant_chat_messages_limit
        limits = global_config.app.limits
        if is_subscribed:
            return limits.sub_user_chat_messages_limit
        return limits.free_user_chat_messages_limit

    def _get_relevant_history_for_user_tier(
        self, *, history_messages: List[BaseMessage], is_subscribed: bool
    ) -> List[BaseMessage]:
        max_messages = self._get_chat_messages_limit(
            is_subscribed=is_subscribed
        )
        return self._get_relevant_history(
            history_messages=history_messages,
            max_messages=max_messages,
        )

    def _on_messages_compaction_done(
        self,
        *,
        compaction_future: Future,
        user_id: str,
        session_id: str,
    ) -> None:
        if compaction_future.cancelled():
            logger.warning(
                "Messages compaction task cancelled: "
                f"agent_id={self.agent_id}, user_id={user_id}, session_id={session_id}"
            )
            return
        compaction_error = compaction_future.exception()
        if compaction_error is not None:
            logger.error(
                "Messages compaction task failed: "
                f"agent_id={self.agent_id}, user_id={user_id}, session_id={session_id}, "
                f"error={compaction_error!s}"
            )
            return
        if compaction_future.result() is not True:
            logger.debug(
                "Messages compaction skipped or not persisted: "
                f"agent_id={self.agent_id}, user_id={user_id}, session_id={session_id}"
            )

    def _run_messages_compaction_task(
        self,
        *,
        user_id: str,
        session_id: str,
        history_messages: List[BaseMessage],
        max_messages_limit: int,
    ) -> bool:
        return maybe_compact_and_save_overflow_history(
            sync_engine=get_sync_engine(),
            user_id=user_id,
            agent_id=self.agent_id,
            session_id=session_id,
            history_messages=history_messages,
            max_messages_limit=max_messages_limit,
        )

    def _maybe_compact_history_for_user_tier(
        self,
        *,
        user_id: str,
        session_id: str,
        history_messages: List[BaseMessage],
        is_subscribed: bool,
    ) -> None:
        max_messages_limit = self._get_chat_messages_limit(
            is_subscribed=is_subscribed
        )
        if (
            max_messages_limit <= 0
            or len(history_messages) <= max_messages_limit
        ):
            return
        compaction_future = get_compaction_executor().submit(
            self._run_messages_compaction_task,
            user_id=user_id,
            session_id=session_id,
            history_messages=history_messages,
            max_messages_limit=max_messages_limit,
        )
        compaction_future.add_done_callback(
            lambda finished_future: self._on_messages_compaction_done(
                compaction_future=finished_future,
                user_id=user_id,
                session_id=session_id,
            )
        )

    def _get_relevant_history(
        self,
        history_messages: List[BaseMessage],
        max_messages: int = MAX_MESSAGES_ALL,
    ) -> List[BaseMessage]:
        """
        获取相关的历史消息，进行智能截取和优化

        Args:
            history_messages: 所有历史消息
            max_messages: 最大消息数量，如果为0则不进行截取，返回所有消息

        Returns:
            经过优化的历史消息列表
        """
        if not history_messages:
            return []

        # 如果max_messages为0，返回所有消息
        if max_messages == self.MAX_MESSAGES_ALL:
            return history_messages

        # 如果消息数量不超过限制，直接返回
        if len(history_messages) <= max_messages:
            return history_messages

        # 取最近的消息
        recent_messages = history_messages[-max_messages:]

        # 确保对话完整性：如果第一条是AI消息，尝试包含前一条用户消息
        if recent_messages and isinstance(recent_messages[0], AIMessage):
            # 查找前面是否有用户消息
            start_index = len(history_messages) - max_messages - 1
            if start_index >= 0 and isinstance(
                history_messages[start_index], HumanMessage
            ):
                # 包含这条用户消息，但移除最后一条消息以保持总数
                recent_messages = [
                    history_messages[start_index]
                ] + recent_messages[:-1]

        return recent_messages

    def _build_date_system_prompt(self, date_iso: str) -> str:
        return "\n".join(
            [
                CONVERSATION_DATE_SYSTEM_PROMPT_TITLE,
                f"- Date: {date_iso}",
                "- The following messages happened on this date.",
            ]
        )

    def _extract_message_date_iso(self, message: BaseMessage) -> Optional[str]:
        additional_kwargs = getattr(message, "additional_kwargs", None) or {}
        created_at_raw = additional_kwargs.get("created_at")
        if not isinstance(created_at_raw, str) or not created_at_raw.strip():
            return None

        normalized_created_at = created_at_raw.strip().replace("Z", "+00:00")
        try:
            return (
                datetime.fromisoformat(normalized_created_at).date().isoformat()
            )
        except ValueError:
            logger.warning(f"无法解析消息 created_at: {created_at_raw}")
            return None

    def _build_messages_with_date_system_prompts(
        self,
        history_messages: List[BaseMessage],
        current_messages: List[BaseMessage],
        now_utc: Optional[datetime] = None,
    ) -> List[BaseMessage]:
        """
        仅为“当天”注入一次日期 system message，位置是当天第一条消息之前。
        """
        if not history_messages and not current_messages:
            return []

        current_time_utc = (
            now_utc if now_utc is not None else datetime.now(timezone.utc)
        )
        current_date_iso = current_time_utc.date().isoformat()

        all_messages = history_messages + current_messages
        if not all_messages:
            return []

        first_today_index: Optional[int] = None
        history_count = len(history_messages)
        for index, message in enumerate(all_messages):
            if index < history_count:
                message_date_iso = self._extract_message_date_iso(message)
            else:
                # 当前请求里的消息统一视为“今天”的消息
                message_date_iso = current_date_iso
            if message_date_iso == current_date_iso:
                first_today_index = index
                break

        if first_today_index is None:
            return all_messages

        messages_with_date_prompts: List[BaseMessage] = []
        for index, message in enumerate(all_messages):
            if index == first_today_index:
                messages_with_date_prompts.append(
                    SystemMessage(
                        content=self._build_date_system_prompt(current_date_iso)
                    )
                )
            messages_with_date_prompts.append(message)

        return messages_with_date_prompts

    def _build_assistant_tool_call_message(
        self, assistant_message: Any
    ) -> Dict[str, Any]:
        tool_calls = getattr(assistant_message, "tool_calls", None) or []
        serialized_tool_calls = []
        for tool_call in tool_calls:
            serialized_tool_calls.append(
                {
                    "id": tool_call.id,
                    "type": getattr(tool_call, "type", "function"),
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments or "",
                    },
                }
            )
        return {
            "role": "assistant",
            "content": assistant_message.content or "",
            "tool_calls": serialized_tool_calls,
        }

    def _insert_system_message_into_openai_messages(
        self,
        *,
        openai_messages: List[Dict[str, Any]],
        system_message_content: str,
    ) -> None:
        insertion_index = 0
        while (
            insertion_index < len(openai_messages)
            and openai_messages[insertion_index].get("role") == "system"
        ):
            insertion_index += 1
        openai_messages.insert(
            insertion_index,
            {"role": "system", "content": system_message_content},
        )

    def _parse_mbti_type_from_tool_arguments(self, raw_arguments: str) -> str:
        try:
            parsed_arguments = json.loads(raw_arguments or "{}")
        except json.JSONDecodeError as e:
            raise ValueError(
                f"{OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME} received invalid JSON arguments"
            ) from e
        mbti_type_raw = parsed_arguments.get("mbti_type")
        if not isinstance(mbti_type_raw, str):
            raise ValueError(
                f"{OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME} requires string field mbti_type"
            )
        try:
            user_metadata = UserMetadata(mbti_type=mbti_type_raw)
        except ValidationError as e:
            raise ValueError(f"Invalid MBTI type: {mbti_type_raw}") from e
        if not user_metadata.mbti_type:
            raise ValueError(
                f"{OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME} requires non-empty mbti_type"
            )
        return user_metadata.mbti_type

    def _save_user_mbti_type_to_user_metadata_sync(
        self, *, user_id: str, mbti_type: str
    ) -> None:
        sync_engine = get_sync_engine()
        with sync_engine.begin() as conn:
            row = conn.execute(
                text("SELECT meta_data FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            ).fetchone()
            if row is None:
                raise ValueError(f"User not found: {user_id}")
            raw_meta_data = row[0]
            if raw_meta_data is None:
                user_metadata = UserMetadata()
            elif isinstance(raw_meta_data, dict):
                user_metadata = UserMetadata.model_validate(raw_meta_data)
            else:
                raise ValueError(
                    f"users.meta_data must be an object, got {type(raw_meta_data).__name__}"
                )
            user_metadata.mbti_type = mbti_type
            conn.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    meta_data=user_metadata.model_dump(exclude_none=True),
                    updated_at=text("now()"),
                )
            )
        cache_service.invalidate_user_info(user_id)
        cache_service.invalidate_user_auth_snapshot(user_id)

    def _execute_official_assistant_tool_call(
        self, *, tool_name: str, raw_arguments: str, user_id: str
    ) -> Tuple[str, Optional[str]]:
        # Step 1: execute the tool side effect (if any), and return tool result text.
        # Step 2: optionally return a system message to be injected into the next LLM call.
        if tool_name == OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME:
            mbti_type = self._parse_mbti_type_from_tool_arguments(raw_arguments)
            self._save_user_mbti_type_to_user_metadata_sync(
                user_id=user_id, mbti_type=mbti_type
            )
            return f"Saved MBTI type: {mbti_type}", None
        if tool_name == OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME:
            manual_content = _load_intellimate_user_manual()
            return (
                "Loaded IntelliMate user manual into system context.",
                INTELLIMATE_USER_MANUAL_SYSTEM_MESSAGE_PREFIX + manual_content,
            )
        if tool_name == OFFICIAL_ASSISTANT_READ_CHANGE_LOGS_TOOL_NAME:
            change_logs = _load_intellimate_change_logs()
            return (
                "Loaded IntelliMate change logs into system context.",
                INTELLIMATE_CHANGE_LOGS_SYSTEM_MESSAGE_PREFIX + change_logs,
            )
        return f"Unsupported tool: {tool_name}", None

    def _resolve_official_assistant_tool_calls(
        self,
        *,
        response: Any,
        openai_messages: List[Dict[str, Any]],
        client: OpenAI,
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        extra_body: Dict[str, Any],
        user_id: str,
        chat_name: str,
        labels: Dict[str, Any],
        initial_trace_id: Optional[str] = None,
        user_email: Optional[str] = None,
    ) -> Tuple[Any, List[Dict[str, Any]], Optional[str]]:
        """返回 (response, messages, trace_id)"""

        def execute_tool_call(
            tool_name: str,
            raw_arguments: str,
        ) -> Tuple[str, Optional[str]]:
            tool_result, injected_system_message = (
                self._execute_official_assistant_tool_call(
                    tool_name=tool_name,
                    raw_arguments=raw_arguments,
                    user_id=user_id,
                )
            )
            logger.info(
                f"Official assistant tool executed: tool={tool_name}, user_id={user_id}"
            )
            return tool_result, injected_system_message

        def continue_chat(
            loop_messages: List[Dict[str, Any]],
        ) -> Tuple[Any, Optional[str]]:
            return self._call_openai_api_with_retry(
                client=client,
                model=model,
                openai_messages=loop_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                extra_body=extra_body,
                user_id=user_id,
                max_retries=3,
                initial_delay=1.0,
                chat_name=chat_name,
                labels=labels,
                user_email=user_email,
                tools=OFFICIAL_ASSISTANT_TOOL_DEFINITIONS,
                tool_choice="auto",
            )

        loop_result = resolve_official_assistant_tool_loop(
            response=response,
            openai_messages=openai_messages,
            max_tool_call_rounds=OFFICIAL_ASSISTANT_MAX_TOOL_CALL_ROUNDS,
            execute_tool_call=execute_tool_call,
            continue_chat=continue_chat,
            build_assistant_tool_call_message=self._build_assistant_tool_call_message,
            insert_system_message=lambda messages, content: self._insert_system_message_into_openai_messages(
                openai_messages=messages,
                system_message_content=content,
            ),
            initial_trace_id=initial_trace_id,
        )
        return loop_result.response, loop_result.messages, loop_result.trace_id

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        判断错误是否可重试

        Args:
            error: 异常对象

        Returns:
            bool: 如果错误可重试返回True，否则返回False
        """
        # OpenAI SDK的错误类型
        if isinstance(
            error, (RateLimitError, APIConnectionError, APITimeoutError)
        ):
            return True

        # 401错误可能是临时性的认证问题
        if isinstance(error, AuthenticationError):
            # 检查错误消息，某些401错误可能是临时性的
            error_str = str(error).lower()
            if "user not found" in error_str or "unauthorized" in error_str:
                return True

        # APIError可能包含状态码信息
        if isinstance(error, APIError):
            status_code = getattr(error, "status_code", None)
            if status_code:
                # 401, 429, 500-503 可能是临时性错误
                if status_code in (401, 429) or (500 <= status_code <= 503):
                    return True

        return False

    def _call_openai_api_with_retry(
        self,
        client: OpenAI,
        model: str,
        openai_messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        top_p: float,
        extra_body: Dict[str, Any],
        user_id: str,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        chat_name: str = None,
        labels: Dict[str, Any] = None,
        user_email: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ):
        """
        带重试机制的OpenAI API调用，并集成LangSmith追踪

        Args:
            client: OpenAI客户端
            model: 模型名称
            openai_messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            top_p: top_p参数
            extra_body: 额外请求体
            user_id: 用户ID（用于日志）
            max_retries: 最大重试次数
            initial_delay: 初始延迟（秒），使用指数退避
            chat_name: 聊天名称，用于LangSmith追踪
            labels: 元数据标签

        Returns:
            API响应对象

        Raises:
            最后一次尝试的异常
        """
        last_error = None

        # 检查是否启用 LangSmith 追踪（测试环境禁用，或 langsmith 不可用时禁用）
        enable_tracing = global_config.app.environment != Environment.TEST
        trace_user_email = user_email or self._get_user_email_for_trace(user_id)
        metadata_labels = dict(labels or {})
        if trace_user_email is not None and "user_email" not in metadata_labels:
            metadata_labels["user_email"] = trace_user_email
        normalized_labels = (
            normalize_langsmith_metadata(metadata_labels)
            if enable_tracing
            else {}
        )
        trace_name = chat_name or f"{user_id}:{self.name}"

        for attempt in range(max_retries):
            should_trace = enable_tracing and _should_trace(trace_user_email)
            try:
                create_kwargs: Dict[str, Any] = {
                    "messages": openai_messages,
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                    "extra_body": extra_body,
                }
                if tools is not None:
                    create_kwargs["tools"] = tools
                if tool_choice is not None:
                    create_kwargs["tool_choice"] = tool_choice
                trace_id: Optional[str] = None
                if should_trace:
                    # 使用 langsmith.trace 创建单个顶级 trace
                    with ls.trace(
                        name=trace_name,
                        run_type="llm",
                        inputs={"messages": openai_messages, "model": model},
                        metadata=normalized_labels,
                    ) as run:
                        response = client.chat.completions.create(
                            **create_kwargs,
                        )
                        # 记录输出到 trace
                        if response.choices:
                            # TODO(context-utilization): Extend LangSmith ``usage`` with
                            # ``app.utils.models_catalog`` ``context_window_tokens`` and prompt/window ratio
                            # for this ``model`` (non-harness path; does not use create_chat_completion_sync).
                            run.end(
                                outputs={
                                    "content": response.choices[
                                        0
                                    ].message.content,
                                    "finish_reason": response.choices[
                                        0
                                    ].finish_reason,
                                    "tool_calls_count": len(
                                        response.choices[0].message.tool_calls
                                        or []
                                    ),
                                    "model": response.model,
                                    "usage": (
                                        {
                                            "prompt_tokens": (
                                                response.usage.prompt_tokens
                                                if response.usage
                                                else None
                                            ),
                                            "completion_tokens": (
                                                response.usage.completion_tokens
                                                if response.usage
                                                else None
                                            ),
                                            "total_tokens": (
                                                response.usage.total_tokens
                                                if response.usage
                                                else None
                                            ),
                                        }
                                        if response.usage
                                        else None
                                    ),
                                }
                            )
                        trace_id_raw = getattr(
                            run, "trace_id", None
                        ) or getattr(run, "id", None)
                        trace_id = str(trace_id_raw) if trace_id_raw else None
                else:
                    # 未采样或 tracing 关闭时，直接调用 API。
                    response = client.chat.completions.create(
                        **create_kwargs,
                    )
                # 成功则返回 (response, trace_id)
                if attempt > 0:
                    logger.info(
                        f"OpenRouter API调用成功（重试后） - "
                        f"Agent: {self.agent_id}, User: {user_id}, "
                        f"Model: {model}, Attempt: {attempt + 1}/{max_retries}"
                    )
                return (response, trace_id)

            except Exception as e:
                last_error = e
                is_retryable = self._is_retryable_error(e)

                # 记录错误详情
                error_details = {
                    "agent_id": self.agent_id,
                    "user_id": user_id,
                    "model": model,
                    "message_count": len(openai_messages),
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "is_retryable": is_retryable,
                }

                # 如果是APIError，记录状态码和错误体
                if isinstance(e, APIError):
                    error_details["status_code"] = getattr(
                        e, "status_code", None
                    )
                    error_details["error_body"] = getattr(e, "body", None)

                if is_retryable and attempt < max_retries - 1:
                    # 计算延迟时间（指数退避）
                    delay = initial_delay * (2**attempt)
                    logger.warning(
                        f"OpenRouter API调用失败（可重试） - "
                        f"Agent: {self.agent_id}, User: {user_id}, "
                        f"Model: {model}, Attempt: {attempt + 1}/{max_retries}, "
                        f"Error: {str(e)}, 将在 {delay:.2f}秒后重试"
                    )
                    logger.debug(f"错误详情: {error_details}")
                    time.sleep(delay)
                else:
                    # 不可重试或已达到最大重试次数
                    if not is_retryable:
                        logger.error(
                            f"OpenRouter API调用失败（不可重试） - "
                            f"Agent: {self.agent_id}, User: {user_id}, "
                            f"Model: {model}, Error: {str(e)}"
                        )
                    else:
                        logger.error(
                            f"OpenRouter API调用失败（重试次数已用完） - "
                            f"Agent: {self.agent_id}, User: {user_id}, "
                            f"Model: {model}, Attempt: {attempt + 1}/{max_retries}, "
                            f"Error: {str(e)}"
                        )
                    logger.error(f"完整错误详情: {error_details}")
                    raise

        # 如果所有重试都失败，抛出最后一次的错误
        raise last_error

    def _chat_sync_optimized(
        self,
        user_id: str,
        session_id: str,
        messages: List[HumanMessage],
        user_profile: str = None,
        chat_settings: ChatSettings = None,
        user_time_context: Optional[UserTimeContext] = None,
        model_override: Optional[str] = None,
        is_subscribed: bool = False,
        client_local_message_id: Optional[str] = None,
    ) -> Tuple[str | List[Dict[str, Any]], Optional[int]]:
        """
        优化版同步聊天方法，接受预计算的参数

        跳过用户信息获取，使用传入的预计算值
        """
        # 从连接池获取连接
        pool_start = time.time()
        pool = get_connection_pool()
        pool_time = time.time() - pool_start
        logger.debug(
            f"连接池获取耗时: {pool_time:.3f}秒 - Agent: {self.agent_id}"
        )

        with pool.connection() as conn_local:
            try:
                # 创建历史记录对象
                history_start = time.time()
                history = PostgresChatMessageHistory(
                    chat_history.TABLE_NAME,
                    session_id,
                    sync_connection=conn_local,
                )
                history_init_time = time.time() - history_start
                logger.debug(
                    f"历史记录初始化耗时: {history_init_time:.3f}秒 - Agent: {self.agent_id}"
                )

                # 获取相关的历史消息（排除已软删除的）
                get_history_start = time.time()
                # TODO: 建议取消截取，因为：目前原型产品状态的截取无明确价值；引入额外复杂性无意义。
                # 待聊天记录过长才需要截取、记忆等复杂机制。
                history_messages = chat_history_service.get_history_messages(
                    session_id
                )
                self._maybe_compact_history_for_user_tier(
                    user_id=user_id,
                    session_id=session_id,
                    history_messages=history_messages,
                    is_subscribed=is_subscribed,
                )
                recent_history = self._get_relevant_history_for_user_tier(
                    history_messages=history_messages,
                    is_subscribed=is_subscribed,
                )
                get_history_time = time.time() - get_history_start
                logger.debug(
                    f"历史消息获取耗时: {get_history_time:.3f}秒 - Agent: {self.agent_id}"
                )

                all_messages = self._build_messages_with_date_system_prompts(
                    history_messages=recent_history,
                    current_messages=messages,
                )
                logger.debug(f"all_messages: {all_messages}")

                # 保存原始用户消息到历史记录
                save_msg_start = time.time()
                if client_local_message_id:
                    user_payload = messages[-1].content
                    chat_history_service.add_user_message(
                        session_id,
                        user_payload,
                        meta_data={"localId": client_local_message_id},
                    )
                else:
                    history.add_messages(messages)
                save_msg_time = time.time() - save_msg_start
                logger.debug(
                    f"用户消息保存耗时: {save_msg_time:.3f}秒 - Agent: {self.agent_id}"
                )

                input_build_start = time.time()
                user_name = self._extract_user_name_from_profile(user_profile)
                user_email = self._get_user_email_for_trace(user_id)
                labels = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "user_email": user_email,
                    "agent_id": self.agent_id,
                    "agent_name": self.name,
                    "chat_settings": chat_settings,
                }

                system_messages = self._build_system_messages_for_chat(
                    user_profile=user_profile,
                    chat_settings=chat_settings,
                    user_time_context=user_time_context,
                )

                messages: list[BaseMessage] = system_messages + all_messages

                openai_messages = (
                    _openai_messages_from_lc_messages_with_tail_user_time(
                        messages,
                        user_name=user_name,
                        agent_name=self.name,
                        user_time_context=user_time_context,
                    )
                )
                logger.debug(f"openai_messages: {openai_messages}")

                input_build_time = time.time() - input_build_start
                logger.debug(
                    f"输入数据构建耗时: {input_build_time:.3f}秒 - Agent: {self.agent_id}"
                )

                # 调用agent进行对话
                agent_invoke_start = time.time()
                logger.debug(f"开始Agent推理 - Agent: {self.agent_id}")

                chat_name = f"{user_name}:{self.name}"
                default_temperature = global_config.agent.temperature
                default_max_tokens = global_config.agent.max_tokens
                default_top_p = global_config.agent.top_p

                client = get_chat_openai_client()

                # API调用（带重试机制）
                # 模型优先级：角色 model > 订阅层 model_override；无默认值，未配置则及早报错。
                api_start = time.time()
                agent_model = self.model_config.get("model")
                model_name = agent_model or model_override
                if model_name is None:
                    raise ValueError(
                        "模型未配置：角色与订阅层均未指定 model，请在配置或角色设置中指定 model"
                    )
                model_name = resolve_chat_model_to_id(model_name)
                temperature = self.model_config.get(
                    "temperature", default_temperature
                )
                max_tokens = self.model_config.get(
                    "max_tokens", default_max_tokens
                )
                top_p = self.model_config.get("top_p", default_top_p)
                model_source = "agent_config" if agent_model else "override"
                logger.debug(
                    f"chat completion LLM config: agent_id={self.agent_id}, session_id={session_id}, model={model_name}, model_source={model_source}, temperature={temperature}, max_tokens={max_tokens}, top_p={top_p}, base_url={self.model_config.get('base_url')}"
                )

                enable_official_assistant_tools = (
                    self._is_intellimate_official()
                )
                trace_id: Optional[str] = None
                try:
                    response, trace_id = self._call_openai_api_with_retry(
                        client=client,
                        model=model_name,
                        openai_messages=openai_messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        extra_body=self._chat_extra_body(user_id, model_name),
                        user_id=user_id,
                        max_retries=3,
                        initial_delay=1.0,
                        chat_name=chat_name,
                        labels=labels,
                        user_email=user_email,
                        tools=(
                            OFFICIAL_ASSISTANT_TOOL_DEFINITIONS
                            if enable_official_assistant_tools
                            else None
                        ),
                        tool_choice=(
                            "auto" if enable_official_assistant_tools else None
                        ),
                    )
                    openai_messages_for_response = openai_messages
                    if enable_official_assistant_tools:
                        response, openai_messages_for_response, trace_id = (
                            self._resolve_official_assistant_tool_calls(
                                response=response,
                                openai_messages=openai_messages,
                                client=client,
                                model=model_name,
                                temperature=temperature,
                                max_tokens=max_tokens,
                                top_p=top_p,
                                extra_body=self._chat_extra_body(
                                    user_id, model_name
                                ),
                                user_id=user_id,
                                chat_name=chat_name,
                                labels=labels,
                                initial_trace_id=trace_id,
                                user_email=user_email,
                            )
                        )
                except Exception as api_error:
                    # 记录详细的错误信息
                    error_context = {
                        "agent_id": self.agent_id,
                        "user_id": user_id,
                        "session_id": session_id,
                        "model": model_name,
                        "message_count": len(openai_messages),
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "top_p": top_p,
                        "error_type": type(api_error).__name__,
                        "error_message": str(api_error),
                    }

                    # 如果是APIError，记录更多信息
                    if isinstance(api_error, APIError):
                        error_context["status_code"] = getattr(
                            api_error, "status_code", None
                        )
                        error_context["error_body"] = getattr(
                            api_error, "body", None
                        )
                        error_context["error_code"] = getattr(
                            api_error, "code", None
                        )

                    logger.error(
                        f"OpenRouter API调用最终失败 - "
                        f"Agent: {self.agent_id}, User: {user_id}, "
                        f"Session: {session_id}, Model: {model_name}, "
                        f"Error: {str(api_error)}"
                    )
                    logger.error(f"完整错误上下文: {error_context}")
                    raise

                api_time = time.time() - api_start
                logger.debug(
                    f"API调用耗时: {api_time:.3f}秒 - Agent: {self.agent_id}"
                )

                agent_invoke_time = time.time() - agent_invoke_start
                logger.debug(
                    f"Agent推理耗时: {agent_invoke_time:.3f}秒 - Agent: {self.agent_id}"
                )

                # 处理响应
                response_process_start = time.time()
                if (
                    response is None
                    or not getattr(response, "choices", None)
                    or len(response.choices) == 0
                ):
                    logger.error(
                        f"LLM 返回无 choices - Agent: {self.agent_id}, User: {user_id}, "
                        f"Session: {session_id}, Model: {model_name}"
                    )
                    raise ValueError("LLM returned no choices")
                finish_reason = response.choices[0].finish_reason
                response_text = response.choices[0].message.content

                # 定义需要重试的 finish_reason
                content_filter_reasons = {"content_filter", "safety"}

                # 处理内容过滤情况：用 "continue" 替换用户消息重试一次
                if (
                    finish_reason in content_filter_reasons
                    and not enable_official_assistant_tools
                ):
                    logger.warning(
                        f"内容过滤触发 - Agent: {self.agent_id}, User: {user_id}, "
                        f"Session: {session_id}, finish_reason: {finish_reason}, "
                        f"被截断内容: {response_text}"
                    )
                    # 用 "continue" 替换最后一条用户消息重试
                    openai_messages_for_response[-1] = {
                        "role": "user",
                        "content": "continue",
                    }
                    retry_response, retry_trace_id = (
                        self._call_openai_api_with_retry(
                            client=client,
                            model=model_name,
                            openai_messages=openai_messages_for_response,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            top_p=top_p,
                            extra_body=self._chat_extra_body(
                                user_id, model_name
                            ),
                            user_id=user_id,
                            max_retries=3,
                            initial_delay=1.0,
                            chat_name=chat_name,
                            labels=labels,
                        )
                    )
                    if (
                        retry_response is None
                        or not getattr(retry_response, "choices", None)
                        or len(retry_response.choices) == 0
                    ):
                        logger.error(
                            f"LLM 重试返回无 choices - Agent: {self.agent_id}, "
                            f"Session: {session_id}, Model: {model_name}"
                        )
                        raise ValueError("LLM returned no choices on retry")
                    retry_finish_reason = retry_response.choices[
                        0
                    ].finish_reason
                    retry_response_text = retry_response.choices[
                        0
                    ].message.content

                    # 重试后仍被过滤则记录错误，但使用重试后的响应
                    if retry_finish_reason in content_filter_reasons:
                        logger.error(
                            f"内容过滤重试后仍被截断 - Agent: {self.agent_id}, "
                            f"Session: {session_id}, finish_reason: {retry_finish_reason}, "
                            f"被截断内容: {retry_response_text}"
                        )
                    else:
                        logger.info(
                            f"内容过滤重试成功 - Agent: {self.agent_id}, "
                            f"Session: {session_id}"
                        )
                    response_text = retry_response_text
                    trace_id = retry_trace_id

                # 处理长度限制情况
                elif finish_reason == "length":
                    logger.warning(
                        f"响应被截断(max_tokens) - Agent: {self.agent_id}, "
                        f"Session: {session_id}, 响应长度: {len(response_text)}"
                    )

                # 处理其他非正常情况
                elif finish_reason not in {"stop", None}:
                    logger.warning(
                        f"非正常结束 - Agent: {self.agent_id}, "
                        f"Session: {session_id}, finish_reason: {finish_reason}"
                    )

                response_process_time = time.time() - response_process_start
                logger.debug(
                    f"响应处理耗时: {response_process_time:.3f}秒 - Agent: {self.agent_id}"
                )

                # 保存AI响应到历史记录（包含LLM调用时间、provider、LangSmith trace），并返回插入后的 message id 供调用方使用
                save_response_start = time.time()
                meta_data: Dict[str, Any] = {
                    "llm_invoke_time": api_time,
                    "llm_provider": get_chat_llm_provider(),
                }
                if trace_id:
                    meta_data["langsmith_trace_id"] = trace_id
                ai_message_id = chat_history_service.add_ai_message_sync(
                    session_id=session_id,
                    message=response_text,
                    agent_id=self.agent_id,
                    meta_data=meta_data,
                )
                save_response_time = time.time() - save_response_start
                logger.debug(
                    f"AI响应保存耗时: {save_response_time:.3f}秒 - Agent: {self.agent_id}"
                )

                return (response_text, ai_message_id)
            except Exception as e:
                # 增强的错误日志记录
                error_context = {
                    "agent_id": self.agent_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "message_count": len(messages),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }

                # 如果是OpenAI API错误，记录更多信息
                if isinstance(
                    e,
                    (
                        APIError,
                        AuthenticationError,
                        RateLimitError,
                        APIConnectionError,
                        APITimeoutError,
                    ),
                ):
                    error_context["is_api_error"] = True
                    if isinstance(e, APIError):
                        error_context["status_code"] = getattr(
                            e, "status_code", None
                        )
                        error_context["error_body"] = getattr(e, "body", None)

                logger.error(
                    f"聊天处理失败（优化版） - "
                    f"Agent: {self.agent_id}, Session: {session_id}, "
                    f"User: {user_id}, Error: {str(e)}"
                )
                logger.error(f"错误上下文: {error_context}")
                raise

    def _generate_message_without_user_save_sync(
        self,
        user_id: str,
        session_id: str,
        messages: List[HumanMessage],
        user_profile: str = None,
        chat_settings: ChatSettings = None,
        user_time_context: Optional[UserTimeContext] = None,
        model_override: Optional[str] = None,
        is_subscribed: bool = False,
    ) -> str:
        """
        生成消息但不保存用户消息到历史记录（用于推送消息）

        与 _chat_sync_optimized 的区别：
        - 不保存用户消息到历史记录
        - 不保存AI响应到历史记录（由调用方通过 add_ai_message 保存）

        Args:
            user_id: 用户ID
            session_id: 会话ID
            messages: 用户消息列表（用于生成AI回复，但不会保存）
            user_profile: 用户信息
            chat_settings: 聊天设置

        Returns:
            生成的AI消息内容
        """
        # 从连接池获取连接
        pool_start = time.time()
        pool = get_connection_pool()
        pool_time = time.time() - pool_start
        logger.debug(
            f"连接池获取耗时: {pool_time:.3f}秒 - Agent: {self.agent_id}"
        )

        with pool.connection() as conn_local:
            try:
                # 获取相关的历史消息（排除已软删除的）
                get_history_start = time.time()
                history_messages = chat_history_service.get_history_messages(
                    session_id
                )
                recent_history = self._get_relevant_history_for_user_tier(
                    history_messages=history_messages,
                    is_subscribed=is_subscribed,
                )
                get_history_time = time.time() - get_history_start
                logger.debug(
                    f"历史消息获取耗时: {get_history_time:.3f}秒 - Agent: {self.agent_id}"
                )

                # 注意：这里不保存用户消息到历史记录
                all_messages = self._build_messages_with_date_system_prompts(
                    history_messages=recent_history,
                    current_messages=messages,
                )
                logger.debug(f"all_messages: {all_messages}")

                # 如果 user_profile 为 None，自动获取
                if user_profile is None:
                    user_profile = self._get_user_profile_sync(user_id)

                input_build_start = time.time()
                user_name = self._extract_user_name_from_profile(user_profile)
                user_email = self._get_user_email_for_trace(user_id)
                labels = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "user_email": user_email,
                    "agent_id": self.agent_id,
                    "agent_name": self.name,
                    "chat_settings": chat_settings,
                }

                system_messages = self._build_system_messages_for_chat(
                    user_profile=user_profile,
                    chat_settings=chat_settings,
                    user_time_context=user_time_context,
                )

                messages_list: list[BaseMessage] = (
                    system_messages + all_messages
                )

                openai_messages = (
                    _openai_messages_from_lc_messages_with_tail_user_time(
                        messages_list,
                        user_name=user_name,
                        agent_name=self.name,
                        user_time_context=user_time_context,
                    )
                )
                logger.debug(f"openai_messages: {openai_messages}")

                input_build_time = time.time() - input_build_start
                logger.debug(
                    f"输入数据构建耗时: {input_build_time:.3f}秒 - Agent: {self.agent_id}"
                )

                # 调用agent进行对话
                agent_invoke_start = time.time()
                logger.debug(
                    f"开始Agent推理（推送消息） - Agent: {self.agent_id}"
                )

                chat_name = f"{user_name}:{self.name}"
                default_temperature = global_config.agent.temperature
                default_max_tokens = global_config.agent.max_tokens
                default_top_p = global_config.agent.top_p

                client = get_chat_openai_client()

                # API调用（使用统一的重试和 trace 逻辑）
                # 模型优先级：角色 model > 订阅层 model_override；无默认值，未配置则及早报错。
                api_start = time.time()
                agent_model = self.model_config.get("model")
                model_name = agent_model or model_override
                if model_name is None:
                    raise ValueError(
                        "模型未配置：角色与订阅层均未指定 model，请在配置或角色设置中指定 model"
                    )
                model_name = resolve_chat_model_to_id(model_name)
                temperature = self.model_config.get(
                    "temperature", default_temperature
                )
                max_tokens = self.model_config.get(
                    "max_tokens", default_max_tokens
                )
                top_p = self.model_config.get("top_p", default_top_p)
                model_source = "agent_config" if agent_model else "override"
                logger.debug(
                    f"chat completion LLM config (push): agent_id={self.agent_id}, session_id={session_id}, model={model_name}, model_source={model_source}, temperature={temperature}, max_tokens={max_tokens}, top_p={top_p}, base_url={self.model_config.get('base_url')}"
                )

                response, trace_id = self._call_openai_api_with_retry(
                    client=client,
                    model=model_name,
                    openai_messages=openai_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    extra_body=self._chat_extra_body(user_id, model_name),
                    user_id=user_id,
                    max_retries=3,
                    initial_delay=1.0,
                    chat_name=chat_name,
                    labels=labels,
                    user_email=user_email,
                )
                api_time = time.time() - api_start
                logger.debug(
                    f"API调用耗时: {api_time:.3f}秒 - Agent: {self.agent_id}"
                )

                agent_invoke_time = time.time() - agent_invoke_start
                logger.debug(
                    f"Agent推理耗时: {agent_invoke_time:.3f}秒 - Agent: {self.agent_id}"
                )

                # 处理响应
                response_process_start = time.time()
                if (
                    response is None
                    or not getattr(response, "choices", None)
                    or len(response.choices) == 0
                ):
                    logger.error(
                        f"LLM 返回无 choices（推送消息） - Agent: {self.agent_id}, "
                        f"Session: {session_id}"
                    )
                    raise ValueError("LLM returned no choices")
                response_text = response.choices[0].message.content
                response_process_time = time.time() - response_process_start
                logger.debug(
                    f"响应处理耗时: {response_process_time:.3f}秒 - Agent: {self.agent_id}"
                )

                # 注意：这里不保存AI响应到历史记录，由调用方通过 add_ai_message 保存
                logger.debug(
                    f"推送消息生成完成（未保存到历史记录） - Agent: {self.agent_id}, Session: {session_id}"
                )

                return (response_text, trace_id)
            except Exception as e:
                logger.error(
                    f"推送消息生成失败 - Agent: {self.agent_id}, Session: {session_id}, Error: {str(e)}"
                )
                raise

    async def generate_message_without_user_save(
        self,
        user_id: str,
        session_id: str,
        messages: List[HumanMessage],
        user_profile: str = None,
        chat_settings: ChatSettings = None,
        user_time_context: Optional[UserTimeContext] = None,
        model_override: Optional[str] = None,
        is_subscribed: bool = False,
    ) -> str:
        """
        异步封装：生成消息但不保存用户消息到历史记录（用于推送消息）

        Args:
            user_id: 用户ID
            session_id: 会话ID
            messages: 用户消息列表（用于生成AI回复，但不会保存）
            user_profile: 用户信息
            chat_settings: 聊天设置

        Returns:
            生成的AI消息内容
        """
        logger.debug(
            f"开始推送消息生成 - Agent: {self.agent_id}, Session: {session_id}"
        )

        self._update_last_used()

        # 在线程池中执行同步生成逻辑
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                self._executor,
                self._generate_message_without_user_save_sync,
                user_id,
                session_id,
                messages,
                user_profile,
                chat_settings,
                user_time_context,
                model_override,
                is_subscribed,
            )
            return result
        except Exception as e:
            logger.error(
                f"异步推送消息生成失败 - Agent: {self.agent_id}, Error: {str(e)}"
            )
            raise

    # TODO：替换为流式消息输出，需要调整大模型 API 调用，输出方式等
    async def chat(
        self,
        user_id: str,
        session_id: str,
        messages: List[HumanMessage],
        chat_settings: ChatSettings = None,
        user_time_context: Optional[UserTimeContext] = None,
        model_override: Optional[str] = None,
        is_subscribed: bool = False,
        client_local_message_id: Optional[str] = None,
    ) -> Tuple[str | List[Dict[str, Any]], Optional[int]]:
        """封装了一个 sync 版本的聊天函数，通过将其运行在 event loop executor 里。
        成功时返回 (响应内容, 插入的 AI 消息 ID)；响应内容可能是文本或 OpenAI content parts。
        异常时抛出。
        """
        logger.debug(
            f"开始聊天处理 - Agent: {self.agent_id}, Session: {session_id}"
        )

        self._update_last_used()

        profile_start = time.time()
        user_profile = self._get_user_profile_sync(user_id)
        profile_time = time.time() - profile_start
        logger.debug(
            f"用户信息获取耗时: {profile_time:.3f}秒 - Agent: {self.agent_id}"
        )

        # 在线程池中执行同步聊天逻辑
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                self._executor,
                self._chat_sync_optimized,
                user_id,
                session_id,
                messages,
                user_profile,
                chat_settings,
                user_time_context,
                model_override,
                is_subscribed,
                client_local_message_id,
            )
            return result
        except Exception as e:
            logger.error(
                f"异步聊天失败 - Agent: {self.agent_id}, Error: {str(e)}"
            )
            raise

    def cleanup(self):
        """清理资源"""
        # Agent 共享全局线程池，这里不做 shutdown，避免影响其他 Agent。
        return


class AgentManager:
    def __init__(
        self,
        max_agents: int = 50,
        cleanup_interval: int = 3600,
        max_idle_time: int = 7200,
    ):
        """
        初始化Agent管理器

        Args:
            max_agents: 最大Agent实例数量
            cleanup_interval: 清理检查间隔（秒）
            max_idle_time: 最大空闲时间（秒）
        """
        self.agents: Dict[str, Agent] = {}
        self.max_agents = max_agents
        self.cleanup_interval = cleanup_interval
        self.max_idle_time = max_idle_time

        # 使用读写锁提升并发性能
        self._read_lock = Lock()
        self._write_lock = Lock()
        self._agent_locks: Dict[str, Lock] = {}  # 每个Agent一个锁
        self._locks_lock = Lock()  # 保护_agent_locks字典

        self._cleanup_task = None
        self._cleanup_started = False

    def _get_agent_lock(self, agent_id: str) -> Lock:
        """获取或创建Agent专用锁"""
        with self._locks_lock:
            if agent_id not in self._agent_locks:
                self._agent_locks[agent_id] = Lock()
            return self._agent_locks[agent_id]

    def _start_cleanup_task(self):
        """启动清理任务（仅在有事件循环时）"""
        if self._cleanup_started:
            return

        try:

            async def cleanup_loop():
                while True:
                    await asyncio.sleep(self.cleanup_interval)
                    self._cleanup_idle_agents()

            self._cleanup_task = asyncio.create_task(cleanup_loop())
            self._cleanup_started = True
            logger.info("Agent清理任务已启动")
        except RuntimeError:
            # 没有运行的事件循环，延迟启动
            logger.info("暂时无法启动清理任务，将在首次使用时启动")

    def _cleanup_idle_agents(self):
        """清理长时间空闲的Agent实例"""
        current_time = time.time()
        idle_agents = []

        # 使用读锁检查空闲Agent
        with self._read_lock:
            for agent_id, agent in self.agents.items():
                with agent._last_used_lock:
                    if current_time - agent.last_used > self.max_idle_time:
                        idle_agents.append(agent_id)

        # 如果有空闲Agent，使用写锁删除
        if idle_agents:
            with self._write_lock:
                for agent_id in idle_agents:
                    if agent_id in self.agents:
                        agent = self.agents[agent_id]
                        # 清理Agent资源
                        try:
                            agent.cleanup()
                        except Exception as e:
                            logger.error(
                                f"清理Agent资源失败 {agent_id}: {str(e)}"
                            )

                        del self.agents[agent_id]
                        logger.debug(f"清理空闲Agent: {agent_id}")

                        # 清理对应的锁
                        with self._locks_lock:
                            self._agent_locks.pop(agent_id, None)

    async def get_agent(self, agent_data: dict) -> Agent:
        """
        获取或创建Agent实例（优化版本）

        Args:
            agent_data: Agent配置数据，包含id, name, prompt, settings等
        """
        # 尝试启动清理任务（如果还没启动）
        if not self._cleanup_started:
            self._start_cleanup_task()

        agent_id = agent_data.get("id")
        if not agent_id:
            raise ValueError("agent_data must include the 'id' field")
        logger.debug(f"请求获取Agent实例 - Agent ID: {agent_id}")

        # 首先尝试读取现有Agent（使用读锁）
        with self._read_lock:
            if agent_id in self.agents:
                existing_agent = self.agents[agent_id]

                # 验证实例中的agent_id是否与请求的一致
                if existing_agent.agent_id == agent_id:
                    # 更新最后使用时间（线程安全）
                    existing_agent._update_last_used()
                    logger.debug(f"从缓存返回Agent实例 - Agent ID: {agent_id}")
                    return existing_agent

        # 需要创建或替换Agent实例，使用Agent专用锁
        agent_lock = self._get_agent_lock(agent_id)
        with agent_lock:
            # 双重检查，防止其他线程已经创建
            with self._read_lock:
                if agent_id in self.agents:
                    existing_agent = self.agents[agent_id]
                    if existing_agent.agent_id == agent_id:
                        existing_agent._update_last_used()
                        return existing_agent

            # 使用写锁进行创建或替换
            with self._write_lock:
                # 如果达到最大数量，清理最久未使用的Agent
                if len(self.agents) >= self.max_agents:
                    oldest_agent_id = min(
                        self.agents.keys(),
                        key=lambda x: self.agents[x].last_used,
                    )
                    old_agent = self.agents[oldest_agent_id]
                    try:
                        old_agent.cleanup()
                    except Exception as e:
                        logger.error(
                            f"清理旧Agent失败 {oldest_agent_id}: {str(e)}"
                        )

                    del self.agents[oldest_agent_id]
                    logger.info(
                        f"达到最大Agent数量，清理最旧的Agent: {oldest_agent_id}"
                    )

                    # 清理对应的锁
                    with self._locks_lock:
                        self._agent_locks.pop(oldest_agent_id, None)

                # 创建新的Agent实例
                agent = build_agent_from_data(agent_id, agent_data)
                logger.debug(f"model_config: {agent.model_config}")
                logger.info(
                    f"创建新的Agent实例 - Agent ID: {agent_id}, Name: {agent.name}"
                )

                try:
                    # 验证创建的Agent实例的agent_id
                    if agent.agent_id != agent_id:
                        logger.error(
                            f"错误：创建的Agent实例ID不匹配！期望: {agent_id}, 实际: {agent.agent_id}"
                        )
                        raise ValueError(
                            "Agent instance creation failed: ID mismatch"
                        )

                    self.agents[agent_id] = agent
                    logger.info(
                        f"成功创建并缓存Agent实例 - Agent ID: {agent_id}"
                    )
                    return agent

                except Exception as e:
                    logger.error(
                        f"创建Agent实例失败 - Agent ID: {agent_id}, 错误: {str(e)}"
                    )
                    # 确保失败的实例不会留在缓存中
                    self.agents.pop(agent_id, None)
                    raise

    async def initialize_popular_agents(self, db_session):
        """
        初始化常用的Agent实例
        """
        from app.services import agent_service

        try:
            # 获取推荐的Agent列表作为常用Agent
            popular_agents = await agent_service.get_recommended_agents(
                db_session, skip=0, limit=10
            )

            for agent_db in popular_agents:
                agent_data = {
                    "id": agent_db.id,
                    "name": agent_db.name,
                    "settings": agent_db.settings,
                    # 主提示词和模式提示词字段
                    "main_prompt": getattr(agent_db, "main_prompt", ""),
                    "mode_prompt": getattr(agent_db, "mode_prompt", ""),
                    "output_format_prompt": getattr(
                        agent_db, "output_format_prompt", ""
                    ),
                    # 角色设定相关字段
                    "personality": getattr(agent_db, "personality", ""),
                    "scenario": getattr(agent_db, "scenario", ""),
                    "message_example": getattr(agent_db, "message_example", ""),
                    "creator_notes": getattr(agent_db, "creator_notes", ""),
                    "tags": getattr(agent_db, "tags", []),
                    "character_version": getattr(
                        agent_db, "character_version", "1.0"
                    ),
                    "extensions": getattr(agent_db, "extensions", {}),
                    "intro": getattr(agent_db, "intro", ""),
                }
                await self.get_agent(agent_data)

            logger.info("初始化了 {} 个常用Agent", len(popular_agents))

        except Exception:
            logger.exception("初始化常用Agent失败")
            raise

    def get_agent_count(self) -> int:
        """获取当前Agent实例数量"""
        with self._read_lock:
            return len(self.agents)

    def get_agent_stats(self) -> Dict[str, Any]:
        """获取Agent管理器详细统计信息"""
        current_time = time.time()
        stats = {
            "total_agents": 0,
            "active_agents": 0,
            "idle_agents": 0,
            "agents_info": [],
        }

        with self._read_lock:
            stats["total_agents"] = len(self.agents)

            for agent_id, agent in self.agents.items():
                with agent._last_used_lock:
                    idle_time = current_time - agent.last_used
                    is_idle = idle_time > self.max_idle_time

                    if is_idle:
                        stats["idle_agents"] += 1
                    else:
                        stats["active_agents"] += 1

                    stats["agents_info"].append(
                        {
                            "agent_id": agent_id,
                            "name": agent.name,
                            "last_used": agent.last_used,
                            "idle_time": idle_time,
                            "is_idle": is_idle,
                        }
                    )

        return stats

    def force_cleanup_agent(self, agent_id: str) -> bool:
        """强制清理指定Agent"""
        agent_lock = self._get_agent_lock(agent_id)
        with agent_lock:
            with self._write_lock:
                if agent_id in self.agents:
                    agent = self.agents[agent_id]
                    try:
                        agent.cleanup()
                    except Exception as e:
                        logger.error(
                            f"强制清理Agent资源失败 {agent_id}: {str(e)}"
                        )

                    del self.agents[agent_id]
                    logger.info(f"强制清理Agent: {agent_id}")

                    # 清理对应的锁
                    with self._locks_lock:
                        self._agent_locks.pop(agent_id, None)

                    return True
        return False

    async def reload_agent(
        self, agent_id: str, agent_data: dict, reason: Optional[str] = None
    ) -> bool:
        """
        重新加载指定Agent实例，强制刷新配置

        Args:
            agent_id: Agent ID
            agent_data: 新的Agent配置数据
            reason: 调用方提供的简短原因（如触发的 API 与变更字段），写入日志便于排查

        Returns:
            重载是否成功
        """
        reason_part = f" reason={reason}" if reason else " reason=unspecified"
        agent_lock = self._get_agent_lock(agent_id)
        with agent_lock:
            with self._write_lock:
                # 如果Agent存在，先清理旧实例
                if agent_id in self.agents:
                    old_agent = self.agents[agent_id]
                    try:
                        old_agent.cleanup()
                        logger.debug(f"已清理旧Agent实例: {agent_id}")
                    except Exception as e:
                        logger.error(
                            f"清理旧Agent实例失败 {agent_id}: {str(e)}"
                        )

                    del self.agents[agent_id]

                try:
                    agent = build_agent_from_data(agent_id, agent_data)
                    self.agents[agent_id] = agent
                    logger.info(f"Agent重新加载成功: {agent_id}{reason_part}")
                    return True

                except Exception as e:
                    logger.error(
                        f"重新加载Agent失败 {agent_id}{reason_part}: {str(e)}"
                    )
                    return False

    def stop(self):
        """停止Agent管理器并清理所有资源"""
        logger.info("正在停止Agent管理器...")

        # 停止清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()

        # 清理所有Agent实例
        with self._write_lock:
            for agent_id, agent in list(self.agents.items()):
                try:
                    agent.cleanup()
                except Exception as e:
                    logger.error(f"清理Agent资源失败 {agent_id}: {str(e)}")

            self.agents.clear()

        # 清理锁
        with self._locks_lock:
            self._agent_locks.clear()

        # 关闭连接池
        global _connection_pool, _agent_chat_executor
        if _connection_pool:
            try:
                _connection_pool.close()
                _connection_pool = None
                logger.info("数据库连接池已关闭")
            except Exception as e:
                logger.error(f"关闭连接池失败: {str(e)}")

        if _agent_chat_executor:
            try:
                _agent_chat_executor.shutdown(wait=False)
                _agent_chat_executor = None
                logger.info("Agent 聊天全局线程池已关闭")
            except Exception as e:
                logger.error(f"关闭 Agent 聊天线程池失败: {str(e)}")

        logger.info("Agent管理器已停止")


# 创建全局Agent管理器实例
agent_manager = AgentManager()
