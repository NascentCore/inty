import asyncio
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from threading import Lock, RLock
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
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
from typing_extensions import deprecated

from app import models
from app.core.agent import prompt_template, prompts
from app.core.agent.agent_prompt_configs import (
    INTELLIMATE_AGENT_ID,
    INTELLIMATE_AGENT_NAME,
    get_agent_prompt_override,
)
from app.core.config import Environment, global_config_loaded_from_config_yaml as global_config
from app.models import chat_history
from app.schemas.user import MBTI_TYPES, UserMetadata
from app.services import chat_history_service
from app.services.cache_service import cache_service
from app.utils.openai_client import (
    get_base_openai_client,
    langchain_message_to_openai_message,
)
from app.utils.langsmith_metadata import normalize_langsmith_metadata

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

MINUTES_PER_HOUR = 60
USER_TIME_CONTEXT_SYSTEM_PROMPT_TITLE = "##User Time Context"
USER_TIME_CONTEXT_SYSTEM_PROMPT_GUIDANCE = [
    "- This time reflects the user's local time, not the assistant's.",
    "- Use it only as context for the user's situation and daily rhythm.",
    "- Do not claim to need sleep or be offline.",
]
CONVERSATION_DATE_SYSTEM_PROMPT_TITLE = "##Conversation Date"


def _should_trace() -> bool:
    sample_rate = global_config.agent.langsmith_text_chat_sample_rate
    rand = random.random()
    logger.debug(f"LangSmith text chat sample rate: {sample_rate}, random: {rand}")
    return rand < sample_rate


class UserTimeContext(TypedDict, total=False):
    local_time: str
    timezone: str
    utc_offset_minutes: int


INTELLIMATE_USER_MANUAL_SYSTEM_MESSAGE_PREFIX = "##IntelliMate User Manual\n"
INTELLIMATE_CHANGE_LOGS_SYSTEM_MESSAGE_PREFIX = "##IntelliMate Change Logs\n"
INTELLIMATE_OFFICIAL_RENAME_SYSTEM_MESSAGE = """##Official Assistant Naming Update
- The official assistant in the IntelliMate app is now named Inty.
- IntelliMate is the app name, not the assistant name.
- In historical messages, the assistant may still appear as "IntelliMate"; interpret that as the old assistant name.
- Always use "Inty" as the assistant name, and correct old-name references to "Inty" when responding."""
# agent.py 位于 app/core/agent，向上 3 层到仓库根目录
REPO_ROOT = Path(__file__).resolve().parents[3]
INTELLIMATE_USER_MANUAL_PATH = REPO_ROOT / "docs" / "INTELLIMATE.md"
INTELLIMATE_CHANGE_LOGS_PATH = REPO_ROOT / "android_app" / "docs" / "CHANGE_LOGS.md"
OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME = "save_user_mbti_type"
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
    }
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


def _format_utc_offset_minutes(offset_minutes: int) -> str:
    sign = "+" if offset_minutes >= 0 else "-"
    total_minutes = abs(offset_minutes)
    hours, minutes = divmod(total_minutes, MINUTES_PER_HOUR)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _build_user_time_context_prompt(
    user_time_context: Optional[UserTimeContext],
) -> Optional[str]:
    if not user_time_context:
        return None

    lines = [USER_TIME_CONTEXT_SYSTEM_PROMPT_TITLE]

    local_time = user_time_context.get("local_time")
    if local_time:
        lines.append(f"- User local time: {local_time}")

    timezone = user_time_context.get("timezone")
    if timezone:
        lines.append(f"- User timezone: {timezone}")

    utc_offset_minutes = user_time_context.get("utc_offset_minutes")
    if isinstance(utc_offset_minutes, int):
        lines.append(f"- UTC offset: {_format_utc_offset_minutes(utc_offset_minutes)}")

    if len(lines) == 1:
        return None

    lines.extend(USER_TIME_CONTEXT_SYSTEM_PROMPT_GUIDANCE)
    return "\n".join(lines)


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
            min_size=global_config.database.pool_size
            // 4,  # 最小连接数
            max_size=global_config.database.pool_size,  # 最大连接数
            max_idle=300,  # 连接最大空闲时间（秒）
            max_lifetime=1800,  # 连接最大生命周期（秒）
        )
        logger.info(
            f"初始化数据库连接池: min_size={global_config.database.pool_size // 4}, max_size={global_config.database.pool_size}"
        )
    return _connection_pool


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

        # 线程池用于异步执行聊天任务
        self._executor = ThreadPoolExecutor(
            max_workers=min(
                32,
                (global_config.database.pool_size or 20) // 2,
            ),
            thread_name_prefix=f"agent-{agent_id}",
        )

        # 使用配置中的模型设置（model/temperature/max_tokens 等由 self.model_config 在 chat 时读取）
        # Deprecated: model_config 中的 api_key 与 base_url 不参与 chat，chat 使用全局 client（app.utils.openai_client.get_base_openai_client）

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
        return (
            self.output_format_prompt
            or prompts.ROMANTIC_ROLEPLAY_PROMPT.output_format_prompt
        )

    def build_system_messages(
        self,
        user_profile: str,
        chat_settings: models.chat_settings.ChatSettings,
        user_time_context: Optional[UserTimeContext] = None,
    ) -> List[SystemMessage]:
        """构建系统消息列表，从state中获取用户信息，state 是 LangChain 运行时系统的一部分。"""
        user_name = self._extract_user_name_from_profile(user_profile)

        system_messages = []

        # 过往逻辑：如缺少任一默认提示词，则认为是用户创建的角色。
        # 此为短期解决方案，未来任何对提示词组装机制的改造，都需要重新考虑这个判定的正确性。
        # 目前不考虑这个区分，未来可能要做一些变化，目前的重点是预置角色而非用户自创角色，
        # 因此不做更深的考虑。由于预置角色也可能没有 mode_prompt，因此无法精确判断。
        # 而应该检查角色的 creator 字段是否是普通用户。
        # is_char_user_created = not self.main_prompt or not self.mode_prompt
        # logger.debug(f"角色是否用户创建: {is_char_user_created}")

        main_prompt = self._get_effective_main_prompt()
        if main_prompt:
            rendered_main_prompt = prompt_template.render_prompt_jinja2_template(
                tmpl=main_prompt, char=self.name, user=user_name
            )
            system_messages.append(SystemMessage(content=rendered_main_prompt))

        character_messages = self._build_character_context(user_name=user_name)
        system_messages.extend(character_messages)

        override = get_agent_prompt_override(self.agent_id, self.name)
        if override is not None and override.mode_prompt is not None:
            mode_prompt = override.mode_prompt
        elif chat_settings and chat_settings.premium_mode:
            logger.debug(f"Using premium mode prompt: {chat_settings.premium_mode}")
            mode_prompt = prompts.ROMANTIC_ROLEPLAY_PROMPT.mode_prompt
        else:
            logger.debug(f"Using normal mode prompt")
            mode_prompt = self._get_effective_mode_prompt()
        if mode_prompt:
            rendered_mode_prompt = prompt_template.render_prompt_jinja2_template(
                tmpl=mode_prompt, char=self.name, user=user_name
            )
            system_messages.append(SystemMessage(content=rendered_mode_prompt))

        if chat_settings and chat_settings.style_prompt:
            logger.debug(f"Using style prompt: {chat_settings.style_prompt} for agent: {self.agent_id} user: {user_name}")
            system_messages.append(SystemMessage(content=chat_settings.style_prompt))

        if user_profile:
            system_messages.append(SystemMessage(content=user_profile))

        if (
            user_time_context
            and global_config.app.features.experimental_enable_chat_with_user_time_context
        ):
            user_time_context_prompt = _build_user_time_context_prompt(
                user_time_context
            )
            if user_time_context_prompt:
                system_messages.append(SystemMessage(content=user_time_context_prompt))

        if global_config.agent.enable_christmas_prompt:
            rendered_prompt = prompt_template.render_prompt_jinja2_template(
                tmpl=CHRISTMAS_TEMPORAL_CONTEXT_PROMPT, char=self.name, user=user_name
            )
            system_messages.append(SystemMessage(content=rendered_prompt))

        if self.intro:
            system_messages.append(
                SystemMessage(
                    content="##Introduction The following Introduction is a text for {{user}}, used only to provide background: \n"
                    + self.intro
                )
            )

        if self._is_intellimate_official():
            # Keep rename guidance explicit so old history can be normalized.
            system_messages.append(
                SystemMessage(content=INTELLIMATE_OFFICIAL_RENAME_SYSTEM_MESSAGE)
            )
            user_manual = _load_intellimate_user_manual()
            system_messages.append(
                SystemMessage(
                    content=INTELLIMATE_USER_MANUAL_SYSTEM_MESSAGE_PREFIX + user_manual
                )
            )
            change_logs = _load_intellimate_change_logs()
            system_messages.append(
                SystemMessage(
                    content=INTELLIMATE_CHANGE_LOGS_SYSTEM_MESSAGE_PREFIX + change_logs
                )
            )

        return system_messages

    def build_system_messages_for_intellimate_official_assistant(
        self,
        user_profile: str,
        chat_settings: models.chat_settings.ChatSettings,
        user_time_context: Optional[UserTimeContext] = None,
    ) -> List[SystemMessage]:
        """构建官方 IntelliMate 助手的系统消息列表；与 build_system_messages 在官方角色时的组装顺序一致，不含 main/mode prompt。"""
        user_name = self._extract_user_name_from_profile(user_profile)
        system_messages: List[SystemMessage] = []

        character_messages = self._build_character_context(user_name=user_name)
        system_messages.extend(character_messages)

        if chat_settings and chat_settings.style_prompt:
            system_messages.append(SystemMessage(content=chat_settings.style_prompt))

        if user_profile:
            system_messages.append(SystemMessage(content=user_profile))

        if (
            user_time_context
            and global_config.app.features.experimental_enable_chat_with_user_time_context
        ):
            user_time_context_prompt = _build_user_time_context_prompt(
                user_time_context
            )
            if user_time_context_prompt:
                system_messages.append(SystemMessage(content=user_time_context_prompt))

        if global_config.agent.enable_christmas_prompt:
            rendered_prompt = prompt_template.render_prompt_jinja2_template(
                tmpl=CHRISTMAS_TEMPORAL_CONTEXT_PROMPT, char=self.name, user=user_name
            )
            system_messages.append(SystemMessage(content=rendered_prompt))

        system_messages.append(
            SystemMessage(
                content="##Introduction The following Introduction is a text for {{user}}, used only to provide background: \n"
                + self.intro
            )
        )
        system_messages.append(
            SystemMessage(content=INTELLIMATE_OFFICIAL_RENAME_SYSTEM_MESSAGE)
        )

        user_manual = _load_intellimate_user_manual()
        system_messages.append(
            SystemMessage(
                content=INTELLIMATE_USER_MANUAL_SYSTEM_MESSAGE_PREFIX + user_manual
            )
        )
        change_logs = _load_intellimate_change_logs()
        system_messages.append(
            SystemMessage(
                content=INTELLIMATE_CHANGE_LOGS_SYSTEM_MESSAGE_PREFIX + change_logs
            )
        )

        return system_messages

    def _build_character_context(self, user_name: str = None) -> List[SystemMessage]:
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
                tmpl=CHRISTMAS_SEASONAL_BEHAVIOR_PROMPT, char=self.name, user=user_name
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

    def _chat_extra_body(self, user_id: str) -> Dict[str, Any]:
        """OpenAI/OpenRouter chat completion extra_body: thinking_budget (Gemini), user (tracking)."""
        return {
            "generation_config": {"thinking_budget": 0},
            "user": user_id,
        }

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
                        cache_service.set_user_info(user_id, user_info_text, ttl=60)
                    else:
                        user_info_parts = []
                        nickname, gender, age_group, description, system_language, meta_data = row
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
                            user_info_parts.append(f"Description: {description}")
                        if isinstance(meta_data, dict):
                            user_metadata = UserMetadata.model_validate(meta_data)
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
        max_messages = self._get_chat_messages_limit(is_subscribed=is_subscribed)
        return self._get_relevant_history(
            history_messages=history_messages,
            max_messages=max_messages,
        )

    def _get_relevant_history(
        self, history_messages: List[BaseMessage], max_messages: int = MAX_MESSAGES_ALL
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
                recent_messages = [history_messages[start_index]] + recent_messages[:-1]

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
            return datetime.fromisoformat(normalized_created_at).date().isoformat()
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

        current_time_utc = now_utc if now_utc is not None else datetime.now(timezone.utc)
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
                    SystemMessage(content=self._build_date_system_prompt(current_date_iso))
                )
            messages_with_date_prompts.append(message)

        return messages_with_date_prompts

    def _build_assistant_tool_call_message(self, assistant_message: Any) -> Dict[str, Any]:
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
                update(models.User)
                .where(models.User.id == user_id)
                .values(
                    meta_data=user_metadata.model_dump(exclude_none=True),
                    updated_at=text("now()"),
                )
            )
        cache_service.invalidate_user_info(user_id)
        cache_service.invalidate_user_auth_snapshot(user_id)

    def _execute_official_assistant_tool_call(
        self, *, tool_name: str, raw_arguments: str, user_id: str
    ) -> str:
        if tool_name != OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME:
            return f"Unsupported tool: {tool_name}"
        mbti_type = self._parse_mbti_type_from_tool_arguments(raw_arguments)
        self._save_user_mbti_type_to_user_metadata_sync(
            user_id=user_id, mbti_type=mbti_type
        )
        return f"Saved MBTI type: {mbti_type}"

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
    ) -> Tuple[Any, List[Dict[str, Any]]]:
        messages_with_tool_results = [*openai_messages]
        current_response = response
        for tool_round in range(OFFICIAL_ASSISTANT_MAX_TOOL_CALL_ROUNDS):
            current_message = current_response.choices[0].message
            tool_calls = getattr(current_message, "tool_calls", None) or []
            if not tool_calls:
                return current_response, messages_with_tool_results

            messages_with_tool_results.append(
                self._build_assistant_tool_call_message(current_message)
            )
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                raw_arguments = tool_call.function.arguments or ""
                tool_result = self._execute_official_assistant_tool_call(
                    tool_name=tool_name,
                    raw_arguments=raw_arguments,
                    user_id=user_id,
                )
                logger.info(
                    f"Official assistant tool executed: tool={tool_name}, user_id={user_id}, round={tool_round + 1}"
                )
                messages_with_tool_results.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    }
                )
            current_response = self._call_openai_api_with_retry(
                client=client,
                model=model,
                openai_messages=messages_with_tool_results,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                extra_body=extra_body,
                user_id=user_id,
                max_retries=3,
                initial_delay=1.0,
                chat_name=chat_name,
                labels=labels,
                tools=OFFICIAL_ASSISTANT_TOOL_DEFINITIONS,
                tool_choice="auto",
            )
        raise ValueError(
            f"Official assistant tool call rounds exceeded limit={OFFICIAL_ASSISTANT_MAX_TOOL_CALL_ROUNDS}"
        )

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        判断错误是否可重试

        Args:
            error: 异常对象

        Returns:
            bool: 如果错误可重试返回True，否则返回False
        """
        # OpenAI SDK的错误类型
        if isinstance(error, (RateLimitError, APIConnectionError, APITimeoutError)):
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
        normalized_labels = normalize_langsmith_metadata(labels) if enable_tracing else {}
        trace_name = chat_name or f"{user_id}:{self.name}"

        for attempt in range(max_retries):
            should_trace = (
                enable_tracing and _should_trace()
            )
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
                            run.end(
                                outputs={
                                    "content": response.choices[0].message.content,
                                    "finish_reason": response.choices[0].finish_reason,
                                    "tool_calls_count": len(
                                        response.choices[0].message.tool_calls or []
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
                else:
                    # 未采样或 tracing 关闭时，直接调用 API。
                    response = client.chat.completions.create(
                        **create_kwargs,
                    )
                # 成功则返回
                if attempt > 0:
                    logger.info(
                        f"OpenRouter API调用成功（重试后） - "
                        f"Agent: {self.agent_id}, User: {user_id}, "
                        f"Model: {model}, Attempt: {attempt + 1}/{max_retries}"
                    )
                return response

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
                    error_details["status_code"] = getattr(e, "status_code", None)
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
        chat_settings: models.chat_settings.ChatSettings = None,
        user_time_context: Optional[UserTimeContext] = None,
        model_override: Optional[str] = None,
        is_subscribed: bool = False,
    ) -> Tuple[str | List[Dict[str, Any]], Optional[int]]:
        """
        优化版同步聊天方法，接受预计算的参数

        跳过用户信息获取，使用传入的预计算值
        """
        # 从连接池获取连接
        pool_start = time.time()
        pool = get_connection_pool()
        pool_time = time.time() - pool_start
        logger.debug(f"连接池获取耗时: {pool_time:.3f}秒 - Agent: {self.agent_id}")

        with pool.connection() as conn_local:
            try:
                # 创建历史记录对象
                history_start = time.time()
                history = PostgresChatMessageHistory(
                    chat_history.TABLE_NAME, session_id, sync_connection=conn_local
                )
                history_init_time = time.time() - history_start
                logger.debug(
                    f"历史记录初始化耗时: {history_init_time:.3f}秒 - Agent: {self.agent_id}"
                )

                # 获取相关的历史消息（排除已软删除的）
                get_history_start = time.time()
                # TODO: 建议取消截取，因为：目前原型产品状态的截取无明确价值；引入额外复杂性无意义。
                # 待聊天记录过长才需要截取、记忆等复杂机制。
                history_messages = chat_history_service.get_history_messages(session_id)
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
                history.add_messages(messages)
                save_msg_time = time.time() - save_msg_start
                logger.debug(
                    f"用户消息保存耗时: {save_msg_time:.3f}秒 - Agent: {self.agent_id}"
                )

                input_build_start = time.time()
                user_name = self._extract_user_name_from_profile(user_profile)
                labels = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "agent_id": self.agent_id,
                    "agent_name": self.name,
                    "chat_settings": chat_settings,
                }

                system_messages = self.build_system_messages(
                    user_profile, chat_settings, user_time_context
                )

                messages: list[BaseMessage] = system_messages + all_messages

                openai_messages = [
                    langchain_message_to_openai_message(message, user_name, self.name)
                    for message in messages
                ]
                logger.debug(f"openai_messages: {openai_messages}")

                input_build_time = time.time() - input_build_start
                logger.debug(
                    f"输入数据构建耗时: {input_build_time:.3f}秒 - Agent: {self.agent_id}"
                )

                # 调用agent进行对话
                agent_invoke_start = time.time()
                logger.debug(f"开始Agent推理 - Agent: {self.agent_id}")

                chat_name = f"{user_name}:{self.name}"
                default_temperature = (
                    global_config.agent.temperature
                )
                default_max_tokens = (
                    global_config.agent.max_tokens
                )
                default_top_p = global_config.agent.top_p

                client = get_base_openai_client()

                # API调用（带重试机制）
                # 模型优先级：角色 model > 订阅层 model_override；无默认值，未配置则及早报错。
                api_start = time.time()
                agent_model = self.model_config.get("model")
                model_name = agent_model or model_override
                if model_name is None:
                    raise ValueError(
                        "模型未配置：角色与订阅层均未指定 model，请在配置或角色设置中指定 model"
                    )
                temperature = self.model_config.get("temperature", default_temperature)
                max_tokens = self.model_config.get("max_tokens", default_max_tokens)
                top_p = self.model_config.get("top_p", default_top_p)
                model_source = (
                    "agent_config"
                    if (agent_model and model_name == agent_model)
                    else "override"
                )
                logger.debug(
                    f"chat completion LLM config: agent_id={self.agent_id}, session_id={session_id}, model={model_name}, model_source={model_source}, temperature={temperature}, max_tokens={max_tokens}, top_p={top_p}, base_url={self.model_config.get('base_url')}"
                )

                enable_official_assistant_tools = self._is_intellimate_official()
                try:
                    response = self._call_openai_api_with_retry(
                        client=client,
                        model=model_name,
                        openai_messages=openai_messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        extra_body=self._chat_extra_body(user_id),
                        user_id=user_id,
                        max_retries=3,
                        initial_delay=1.0,
                        chat_name=chat_name,
                        labels=labels,
                        tools=(
                            OFFICIAL_ASSISTANT_TOOL_DEFINITIONS
                            if enable_official_assistant_tools
                            else None
                        ),
                        tool_choice="auto" if enable_official_assistant_tools else None,
                    )
                    openai_messages_for_response = openai_messages
                    if enable_official_assistant_tools:
                        response, openai_messages_for_response = (
                            self._resolve_official_assistant_tool_calls(
                                response=response,
                                openai_messages=openai_messages,
                                client=client,
                                model=model_name,
                                temperature=temperature,
                                max_tokens=max_tokens,
                                top_p=top_p,
                                extra_body=self._chat_extra_body(user_id),
                                user_id=user_id,
                                chat_name=chat_name,
                                labels=labels,
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
                        error_context["error_body"] = getattr(api_error, "body", None)
                        error_context["error_code"] = getattr(api_error, "code", None)

                    logger.error(
                        f"OpenRouter API调用最终失败 - "
                        f"Agent: {self.agent_id}, User: {user_id}, "
                        f"Session: {session_id}, Model: {model_name}, "
                        f"Error: {str(api_error)}"
                    )
                    logger.error(f"完整错误上下文: {error_context}")
                    raise

                api_time = time.time() - api_start
                logger.debug(f"API调用耗时: {api_time:.3f}秒 - Agent: {self.agent_id}")

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
                if finish_reason in content_filter_reasons and not enable_official_assistant_tools:
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
                    retry_response = self._call_openai_api_with_retry(
                        client=client,
                        model=model_name,
                        openai_messages=openai_messages_for_response,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        extra_body=self._chat_extra_body(user_id),
                        user_id=user_id,
                        max_retries=3,
                        initial_delay=1.0,
                        chat_name=chat_name,
                        labels=labels,
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
                    retry_finish_reason = retry_response.choices[0].finish_reason
                    retry_response_text = retry_response.choices[0].message.content

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

                # 保存AI响应到历史记录（包含LLM调用时间），并返回插入后的 message id 供调用方使用
                save_response_start = time.time()
                ai_message_id = chat_history_service.add_ai_message_sync(
                    session_id=session_id,
                    message=response_text,
                    agent_id=self.agent_id,
                    meta_data={"llm_invoke_time": api_time},
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
                        error_context["status_code"] = getattr(e, "status_code", None)
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
        chat_settings: models.chat_settings.ChatSettings = None,
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
        logger.debug(f"连接池获取耗时: {pool_time:.3f}秒 - Agent: {self.agent_id}")

        with pool.connection() as conn_local:
            try:
                # 获取相关的历史消息（排除已软删除的）
                get_history_start = time.time()
                history_messages = chat_history_service.get_history_messages(session_id)
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
                labels = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "agent_id": self.agent_id,
                    "agent_name": self.name,
                    "chat_settings": chat_settings,
                }

                system_messages = self.build_system_messages(
                    user_profile, chat_settings, user_time_context
                )

                messages_list: list[BaseMessage] = system_messages + all_messages

                openai_messages = [
                    langchain_message_to_openai_message(message, user_name, self.name)
                    for message in messages_list
                ]
                logger.debug(f"openai_messages: {openai_messages}")

                input_build_time = time.time() - input_build_start
                logger.debug(
                    f"输入数据构建耗时: {input_build_time:.3f}秒 - Agent: {self.agent_id}"
                )

                # 调用agent进行对话
                agent_invoke_start = time.time()
                logger.debug(f"开始Agent推理（推送消息） - Agent: {self.agent_id}")

                chat_name = f"{user_name}:{self.name}"
                default_temperature = (
                    global_config.agent.temperature
                )
                default_max_tokens = (
                    global_config.agent.max_tokens
                )
                default_top_p = global_config.agent.top_p

                client = get_base_openai_client()

                # API调用（使用统一的重试和 trace 逻辑）
                # 模型优先级：角色 model > 订阅层 model_override；无默认值，未配置则及早报错。
                api_start = time.time()
                agent_model = self.model_config.get("model")
                model_name = agent_model or model_override
                if model_name is None:
                    raise ValueError(
                        "模型未配置：角色与订阅层均未指定 model，请在配置或角色设置中指定 model"
                    )
                temperature = self.model_config.get("temperature", default_temperature)
                max_tokens = self.model_config.get("max_tokens", default_max_tokens)
                top_p = self.model_config.get("top_p", default_top_p)
                model_source = (
                    "agent_config"
                    if (agent_model and model_name == agent_model)
                    else "override"
                )
                logger.debug(
                    f"chat completion LLM config (push): agent_id={self.agent_id}, session_id={session_id}, model={model_name}, model_source={model_source}, temperature={temperature}, max_tokens={max_tokens}, top_p={top_p}, base_url={self.model_config.get('base_url')}"
                )

                response = self._call_openai_api_with_retry(
                    client=client,
                    model=model_name,
                    openai_messages=openai_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    extra_body=self._chat_extra_body(user_id),
                    user_id=user_id,
                    max_retries=3,
                    initial_delay=1.0,
                    chat_name=chat_name,
                    labels=labels,
                )
                api_time = time.time() - api_start
                logger.debug(f"API调用耗时: {api_time:.3f}秒 - Agent: {self.agent_id}")

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

                return response_text
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
        chat_settings: models.chat_settings.ChatSettings = None,
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
        chat_settings: models.chat_settings.ChatSettings = None,
        user_time_context: Optional[UserTimeContext] = None,
        model_override: Optional[str] = None,
        is_subscribed: bool = False,
    ) -> Tuple[str | List[Dict[str, Any]], Optional[int]]:
        """封装了一个 sync 版本的聊天函数，通过将其运行在 event loop executor 里。
        成功时返回 (响应内容, 插入的 AI 消息 ID)；响应内容可能是文本或 OpenAI content parts。
        异常时抛出。
        """
        logger.debug(f"开始聊天处理 - Agent: {self.agent_id}, Session: {session_id}")

        self._update_last_used()

        profile_start = time.time()
        user_profile = self._get_user_profile_sync(user_id)
        profile_time = time.time() - profile_start
        logger.debug(f"用户信息获取耗时: {profile_time:.3f}秒 - Agent: {self.agent_id}")

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
            )
            return result
        except Exception as e:
            logger.error(f"异步聊天失败 - Agent: {self.agent_id}, Error: {str(e)}")
            raise

    def cleanup(self):
        """清理资源"""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)


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
                            logger.error(f"清理Agent资源失败 {agent_id}: {str(e)}")

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
                        self.agents.keys(), key=lambda x: self.agents[x].last_used
                    )
                    old_agent = self.agents[oldest_agent_id]
                    try:
                        old_agent.cleanup()
                    except Exception as e:
                        logger.error(f"清理旧Agent失败 {oldest_agent_id}: {str(e)}")

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
                        raise ValueError("Agent instance creation failed: ID mismatch")

                    self.agents[agent_id] = agent
                    logger.info(f"成功创建并缓存Agent实例 - Agent ID: {agent_id}")
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
                    # 角色设定相关字段
                    "personality": getattr(agent_db, "personality", ""),
                    "scenario": getattr(agent_db, "scenario", ""),
                    "message_example": getattr(agent_db, "message_example", ""),
                    "creator_notes": getattr(agent_db, "creator_notes", ""),
                    "tags": getattr(agent_db, "tags", []),
                    "character_version": getattr(agent_db, "character_version", "1.0"),
                    "extensions": getattr(agent_db, "extensions", {}),
                    "intro": getattr(agent_db, "intro", ""),
                }
                await self.get_agent(agent_data)

            print(f"初始化了 {len(popular_agents)} 个常用Agent")

        except Exception as e:
            print(f"初始化常用Agent失败: {str(e)}")

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
                        logger.error(f"强制清理Agent资源失败 {agent_id}: {str(e)}")

                    del self.agents[agent_id]
                    logger.info(f"强制清理Agent: {agent_id}")

                    # 清理对应的锁
                    with self._locks_lock:
                        self._agent_locks.pop(agent_id, None)

                    return True
        return False

    async def reload_agent(self, agent_id: str, agent_data: dict) -> bool:
        """
        重新加载指定Agent实例，强制刷新配置

        Args:
            agent_id: Agent ID
            agent_data: 新的Agent配置数据

        Returns:
            重载是否成功
        """
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
                        logger.error(f"清理旧Agent实例失败 {agent_id}: {str(e)}")

                    del self.agents[agent_id]

                try:
                    agent = build_agent_from_data(agent_id, agent_data)
                    self.agents[agent_id] = agent
                    logger.info(f"Agent重新加载成功: {agent_id}")
                    return True

                except Exception as e:
                    logger.error(f"重新加载Agent失败 {agent_id}: {str(e)}")
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
        global _connection_pool
        if _connection_pool:
            try:
                _connection_pool.close()
                _connection_pool = None
                logger.info("数据库连接池已关闭")
            except Exception as e:
                logger.error(f"关闭连接池失败: {str(e)}")

        logger.info("Agent管理器已停止")


# 创建全局Agent管理器实例
agent_manager = AgentManager()
