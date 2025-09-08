import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, RLock
from typing import Any, Dict, List, Optional, TypedDict

from jinja2 import Template as Jinja2Template
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_postgres import PostgresChatMessageHistory
from langgraph.graph import MessagesState
from langgraph.managed import RemainingSteps
from loguru import logger
from openai import OpenAI
from psycopg_pool import ConnectionPool
from sqlalchemy import text
from typing_extensions import deprecated

from app import models
from app.core.agent import prompt_template, prompts
from app.core.config import global_config_loaded_from_config_yaml
from app.models import chat_history
from app.services.background_task_service import background_task_service
from app.services.cache_service import cache_service
from app.utils.openai_client import (
    create_openai_client,
    langchain_message_to_openai_message,
)

from loguru import logger


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
        model_config = agent_data["settings"].get("llm_config", {})
        # 向后兼容：也检查旧的model_config字段
        if not model_config and "model_config" in agent_data["settings"]:
            model_config = agent_data["settings"]["model_config"]

    # 如果没有自定义配置，使用默认配置
    if not model_config:
        model_config = {
            "model": global_config_loaded_from_config_yaml.agent.model,
            "api_key": global_config_loaded_from_config_yaml.agent.api_key,
            "base_url": global_config_loaded_from_config_yaml.agent.base_url,
            "temperature": getattr(
                global_config_loaded_from_config_yaml.agent, "temperature", 0.5
            ),
            "max_tokens": getattr(
                global_config_loaded_from_config_yaml.agent, "max_tokens", 1000
            ),
            "top_p": getattr(global_config_loaded_from_config_yaml.agent, "top_p", 1.0),
            "frequency_penalty": getattr(
                global_config_loaded_from_config_yaml.agent, "frequency_penalty", 0.0
            ),
            "presence_penalty": getattr(
                global_config_loaded_from_config_yaml.agent, "presence_penalty", 0.0
            ),
        }
    else:
        # 如果有自定义配置，但某些字段为空，则使用默认配置补充
        if not model_config.get("base_url"):
            model_config["base_url"] = (
                global_config_loaded_from_config_yaml.agent.base_url
            )
        if not model_config.get("api_key"):
            model_config["api_key"] = (
                global_config_loaded_from_config_yaml.agent.api_key
            )
        if not model_config.get("model"):
            model_config["model"] = global_config_loaded_from_config_yaml.agent.model

    return model_config


# 全局连接池
_connection_pool = None
_sync_engine = None


def get_sync_engine():
    """获取全局同步数据库引擎（避免重复创建）"""
    global _sync_engine
    if _sync_engine is None:
        from sqlalchemy import create_engine

        _sync_engine = create_engine(
            global_config_loaded_from_config_yaml.database.url,
            pool_size=global_config_loaded_from_config_yaml.database.pool_size
            // 2,  # 同步引擎使用一半的连接池
            max_overflow=global_config_loaded_from_config_yaml.database.max_overflow,
            pool_timeout=global_config_loaded_from_config_yaml.database.pool_timeout,
            pool_recycle=global_config_loaded_from_config_yaml.database.pool_recycle,
            pool_pre_ping=global_config_loaded_from_config_yaml.database.pool_pre_ping,
            connect_args={
                "connect_timeout": global_config_loaded_from_config_yaml.database.connect_timeout,
                "options": "-c jit=off -c application_name=inty_sync",
            },
            echo=False,  # 禁用SQL日志
        )
        logger.info(
            f"全局同步数据库引擎已初始化 - pool_size: {global_config_loaded_from_config_yaml.database.pool_size // 2}"
        )
    return _sync_engine


def get_connection_pool():
    """获取数据库连接池"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPool(
            global_config_loaded_from_config_yaml.database.url,
            min_size=global_config_loaded_from_config_yaml.database.pool_size
            // 4,  # 最小连接数
            max_size=global_config_loaded_from_config_yaml.database.pool_size,  # 最大连接数
            max_idle=300,  # 连接最大空闲时间（秒）
            max_lifetime=1800,  # 连接最大生命周期（秒）
        )
        logger.info(
            f"初始化数据库连接池: min_size={global_config_loaded_from_config_yaml.database.pool_size // 4}, max_size={global_config_loaded_from_config_yaml.database.pool_size}"
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
        # 角色卡相关参数
        personality: str = "",
        scenario: str = "",
        message_example: str = "",
        creator_notes: str = "",
        tags: List[str] = None,
        character_version: str = "1.0",
        extensions: Dict[str, Any] = None,
    ):

        # 基础属性
        self.agent_id = agent_id
        self.name = name
        self.model_config = model_config
        self.last_used = time.time()
        self.description = description
        self._last_used_lock = RLock()
        self._user_info_cache = {}

        # 主提示词和模式提示词属性
        self.main_prompt = main_prompt
        # mode_prompt has 2 versions: free and premium.
        # free is the default and is for free users.
        # premium is for users with premium subscription.
        self.mode_prompt = mode_prompt
        self.output_format_prompt = output_format_prompt

        # 角色卡相关属性
        self.personality = personality
        self.scenario = scenario
        self.message_example = message_example
        self.creator_notes = creator_notes
        self.tags = tags or []
        self.character_version = character_version
        self.extensions = extensions or {}

        # 更新agent数据以包含所有信息
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
            "tags": tags,
            "character_version": character_version,
            "extensions": extensions,
        }

        # 线程池用于异步执行聊天任务
        self._executor = ThreadPoolExecutor(
            max_workers=min(
                32,
                (global_config_loaded_from_config_yaml.database.pool_size or 20) // 2,
            ),
            thread_name_prefix=f"agent-{agent_id}",
        )

        # 使用配置中的模型设置
        model_name = model_config.get(
            "model", global_config_loaded_from_config_yaml.agent.model
        )
        api_key = model_config.get(
            "api_key", global_config_loaded_from_config_yaml.agent.api_key
        )
        base_url = model_config.get(
            "base_url", global_config_loaded_from_config_yaml.agent.base_url
        )

        # 提取模型参数
        temperature = model_config.get(
            "temperature",
            getattr(global_config_loaded_from_config_yaml.agent, "temperature", 0.5),
        )
        max_tokens = model_config.get(
            "max_tokens",
            getattr(global_config_loaded_from_config_yaml.agent, "max_tokens", 1000),
        )
        top_p = model_config.get("top_p")
        frequency_penalty = model_config.get("frequency_penalty")
        presence_penalty = model_config.get("presence_penalty")

        # 构建ChatOpenAI参数
        chat_params = {
            "model": model_name,
            "openai_api_key": api_key,
            "openai_api_base": base_url,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # 只有当参数不为None时才添加
        if top_p is not None:
            chat_params["top_p"] = top_p
        if frequency_penalty is not None:
            chat_params["frequency_penalty"] = frequency_penalty
        if presence_penalty is not None:
            chat_params["presence_penalty"] = presence_penalty

    def _get_effective_main_prompt(self) -> str:
        return self.main_prompt or prompts.ROMANTIC_ROLEPLAY_PROMPT.main_prompt

    def _get_effective_mode_prompt(self) -> str:
        return self.mode_prompt or prompts.ROMANTIC_ROLEPLAY_PROMPT.mode_prompt

    def _get_effective_output_format_prompt(self) -> str:
        return (
            self.output_format_prompt
            or prompts.ROMANTIC_ROLEPLAY_PROMPT.output_format_prompt
        )

    def build_system_messages(
        self, user_profile: str, chat_settings: models.chat_settings.ChatSettings
    ) -> List[SystemMessage]:
        """构建系统消息列表，从state中获取用户信息，state 是 LangChain 运行时系统的一部分。"""
        user_name = self._extract_user_name_from_profile(user_profile)

        system_messages = []

        # 如缺少任一默认提示词，则认为是用户创建的角色。
        # 此为短期解决方案，未来任何对提示词组装机制的改造，都需要重新考虑这个判定的正确性。
        # 目前不考虑这个区分，未来可能要做一些变化。
        # is_char_user_created = not self.main_prompt or not self.mode_prompt
        # logger.debug(f"角色是否用户创建: {is_char_user_created}")

        main_prompt = self._get_effective_main_prompt()
        rendered_main_prompt = prompt_template.render_prompt_jinja2_template(
            tmpl=main_prompt, char=self.name, user=user_name
        )
        system_messages.append(SystemMessage(content=rendered_main_prompt))

        character_messages = self._build_character_context(user_name=user_name)
        system_messages.extend(character_messages)

        if chat_settings and chat_settings.premium_mode:
            logger.debug(f"Using premium mode prompt: {chat_settings.premium_mode}")
            mode_prompt = prompts.ROMANTIC_ROLEPLAY_PROMPT.mode_prompt
        else:
            logger.debug(f"Using normal mode prompt")
            mode_prompt = self._get_effective_mode_prompt()
        rendered_mode_prompt = prompt_template.render_prompt_jinja2_template(
            tmpl=mode_prompt, char=self.name, user=user_name
        )
        system_messages.append(SystemMessage(content=rendered_mode_prompt))

        if chat_settings and chat_settings.style_prompt:
            system_messages.append(SystemMessage(content=chat_settings.style_prompt))

        if user_profile:
            system_messages.append(SystemMessage(content=user_profile))

        return system_messages

    def _build_character_context(self, user_name: str = None) -> List[SystemMessage]:
        """
        构建角色卡上下文信息，每个字段作为独立的system message，支持模板渲染
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

        if self.tags:
            context_messages.append(SystemMessage(content=", ".join(self.tags)))

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

        try:
            # 尝试从用户profile中提取Name字段
            import re

            name_match = re.search(r"Name:\s*([^\n]+)", user_profile)
            if name_match:
                return name_match.group(1).strip()

            # 如果没找到，尝试查找中文的"名字"或"姓名"
            chinese_name_match = re.search(
                r"[名字|姓名]\s*[:=：]\s*([^\n]+)", user_profile
            )
            if chinese_name_match:
                return chinese_name_match.group(1).strip()

        except Exception as e:
            logger.error(f"提取用户名失败: {str(e)}")

        return None

    def _update_last_used(self):
        """线程安全地更新最后使用时间"""
        with self._last_used_lock:
            self.last_used = time.time()

    @deprecated("Should be moved to user service")
    def _get_user_profile_sync(self, user_id: str) -> str:
        """
        同步获取用户profile信息（优化版本 - 使用全局缓存）
        """
        # 先检查全局缓存
        cached_user_info = cache_service.get_user_info(user_id)
        if cached_user_info is not None:
            logger.debug(f"从全局缓存获取用户信息: {user_id}")
            return cached_user_info

        # 然后检查本地缓存（保留兼容性）
        if user_id in self._user_info_cache:
            user_info = self._user_info_cache[user_id]
            # 同时更新到全局缓存
            cache_service.set_user_info(user_id, user_info)
            return user_info

        try:
            # 使用全局同步数据库引擎（避免重复创建）
            sync_engine = get_sync_engine()

            with sync_engine.connect() as conn:
                # 查询用户基本信息
                query = text(
                    """
                    SELECT nickname, gender, age_group, description, system_language 
                    FROM users 
                    WHERE id = :user_id
                """
                )
                result = conn.execute(query, {"user_id": user_id})
                row = result.fetchone()

                if not row:
                    logger.debug(f"用户 {user_id} 不存在")
                    user_info_text = ""
                    # 缓存空结果，避免重复查询
                    self._user_info_cache[user_id] = user_info_text
                    cache_service.set_user_info(
                        user_id, user_info_text, ttl=60
                    )  # 空结果缓存时间短
                    return user_info_text

                # 构建用户信息字符串
                user_info_parts = []
                nickname, gender, age_group, description, system_language = row

                if nickname:
                    user_info_parts.append(f"Name: {nickname}")
                if gender:
                    gender_map = {"MALE": "Male", "FEMALE": "Female", "OTHER": "Other"}
                    user_info_parts.append(f"Gender: {gender_map.get(gender, gender)}")
                if age_group:
                    user_info_parts.append(f"Age: {age_group}")
                if description:
                    user_info_parts.append(f"Description: {description}")
                # if system_language:
                #     user_info_parts.append(f"Language: {system_language}")

                if user_info_parts:
                    user_info_text = "##User Information\n" + "\n".join(user_info_parts)
                else:
                    user_info_text = ""

                # 同时更新本地和全局缓存
                self._user_info_cache[user_id] = user_info_text
                cache_service.set_user_info(user_id, user_info_text)

                if user_info_text:
                    logger.debug(
                        f"成功获取用户 {user_id} 的基本信息: {user_info_text[:100]}..."
                    )

                return user_info_text

        except Exception as e:
            logger.error(f"获取用户 {user_id} 基本信息失败: {str(e)}")
            user_info_text = ""
            self._user_info_cache[user_id] = user_info_text
            cache_service.set_user_info(
                user_id, user_info_text, ttl=30
            )  # 失败结果缓存时间很短
            return user_info_text

    # 特殊值，表示返回全部消息
    MAX_MESSAGES_ALL = 0

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

    def _chat_sync_optimized(
        self,
        user_id: str,
        session_id: str,
        messages: List[HumanMessage],
        user_profile: str = None,
        chat_settings: models.chat_settings.ChatSettings = None,
    ) -> str:
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

                # 获取相关的历史消息
                get_history_start = time.time()
                # TODO: 建议取消截取，因为：目前原型产品状态的截取无明确价值；引入额外复杂性无意义。
                # 待聊天记录过长才需要截取、记忆等复杂机制。
                recent_history = self._get_relevant_history(history.messages)
                get_history_time = time.time() - get_history_start
                logger.debug(
                    f"历史消息获取耗时: {get_history_time:.3f}秒 - Agent: {self.agent_id}"
                )

                all_messages = recent_history + messages["messages"]
                logger.debug(f"all_messages: {all_messages}")

                # 保存原始用户消息到历史记录
                save_msg_start = time.time()
                history.add_messages(messages["messages"])
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
                    user_profile, chat_settings
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
                default_model = global_config_loaded_from_config_yaml.agent.model
                default_temperature = (
                    global_config_loaded_from_config_yaml.agent.temperature
                )
                default_max_tokens = (
                    global_config_loaded_from_config_yaml.agent.max_tokens
                )
                default_top_p = global_config_loaded_from_config_yaml.agent.top_p

                response = create_openai_client(
                    chat_name=chat_name, labels=labels
                ).chat.completions.create(
                    messages=openai_messages,
                    model=self.model_config.get("model", default_model),
                    temperature=self.model_config.get(
                        "temperature", default_temperature
                    ),
                    max_tokens=self.model_config.get("max_tokens", default_max_tokens),
                    top_p=self.model_config.get("top_p", default_top_p),
                    extra_body={
                        # This only works for Gemini models.
                        "generation_config": {
                            "thinking_budget": 0,
                        },
                        # This appears on Open Router Client User ID field.
                        # can be used to track end user's usage.
                        "user": user_id,
                    },
                )
                agent_invoke_time = time.time() - agent_invoke_start
                logger.debug(
                    f"Agent推理耗时: {agent_invoke_time:.3f}秒 - Agent: {self.agent_id}"
                )

                # 处理响应
                response_process_start = time.time()
                response_text = response.choices[0].message.content
                response_process_time = time.time() - response_process_start
                logger.debug(
                    f"响应处理耗时: {response_process_time:.3f}秒 - Agent: {self.agent_id}"
                )

                # 保存AI响应到历史记录
                save_response_start = time.time()
                history.add_messages([AIMessage(content=response_text)])
                save_response_time = time.time() - save_response_start
                logger.debug(
                    f"AI响应保存耗时: {save_response_time:.3f}秒 - Agent: {self.agent_id}"
                )

                return response_text
            except Exception as e:
                logger.error(
                    f"聊天处理失败（优化版） - Agent: {self.agent_id}, Session: {session_id}, Error: {str(e)}"
                )
                raise

    @deprecated("替换为流式消息输出，需要调整大模型 API 调用，输出方式等")
    async def chat(
        self,
        user_id: str,
        session_id: str,
        messages: List[HumanMessage],
        chat_settings: models.chat_settings.ChatSettings = None,
    ) -> str:
        """封装了一个 sync 版本的聊天函数，通过将其运行在 event loop executor 里"""
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
            )
            return result
        except Exception as e:
            logger.error(f"异步聊天失败 - Agent: {self.agent_id}, Error: {str(e)}")
            raise

    def get_final_prompt(self) -> str:
        """
        获取最终渲染的提示词

        Returns:
            渲染后的完整提示词
        """
        # 构建示例输入来展示完整提示词
        example_input = {
            "messages": [HumanMessage(content="示例消息")],
            "user_profile": "Name: 示例用户\nGender: Other\n[示例用户信息]",
            "user_id": "example_user_id",
        }

        try:
            # 通过Runnable生成示例提示词
            formatted_prompt = self.prompt_runnable.invoke(example_input)
            if hasattr(formatted_prompt, "messages"):
                return "\n\n".join(
                    [
                        msg.content
                        for msg in formatted_prompt.messages
                        if hasattr(msg, "content")
                    ]
                )
            else:
                return str(formatted_prompt)
        except Exception as e:
            logger.error(f"生成提示词示例失败: {str(e)}")
            # 回退到简单的组合提示词
            fallback_parts = []
            main_prompt = self._get_effective_main_prompt()
            if main_prompt:
                fallback_parts.append(main_prompt)
            if self.personality:
                fallback_parts.append(f"[角色性格]\n{self.personality}")
            mode_prompt = self._get_effective_mode_prompt()
            if mode_prompt:
                fallback_parts.append(mode_prompt)
            return "\n\n".join(fallback_parts) if fallback_parts else "AI助手"

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
            raise ValueError("agent_data必须包含'id'字段")
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
                model_config = get_agent_model_config(agent_data)
                logger.debug(f"model_config: {model_config}")

                description = agent_data.get("description", "")

                agent_name = agent_data.get("name", f"Agent_{agent_id[:8]}")
                logger.info(
                    f"创建新的Agent实例 - Agent ID: {agent_id}, Name: {agent_name}"
                )

                try:
                    agent = Agent(
                        agent_id=agent_id,
                        name=agent_name,
                        model_config=model_config,
                        description=description,
                        # 主提示词和模式提示词参数
                        main_prompt=agent_data.get("main_prompt", ""),
                        mode_prompt=agent_data.get("mode_prompt", ""),
                        # 角色卡相关参数
                        personality=agent_data.get("personality", ""),
                        scenario=agent_data.get("scenario", ""),
                        message_example=agent_data.get("message_example", ""),
                        creator_notes=agent_data.get("creator_notes", ""),
                        tags=agent_data.get("tags", []),
                        character_version=agent_data.get("character_version", "1.0"),
                        extensions=agent_data.get("extensions", {}),
                    )

                    # 验证创建的Agent实例的agent_id
                    if agent.agent_id != agent_id:
                        logger.error(
                            f"错误：创建的Agent实例ID不匹配！期望: {agent_id}, 实际: {agent.agent_id}"
                        )
                        raise ValueError(f"Agent实例创建失败: ID不匹配")

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
                    # 角色卡相关字段
                    "personality": getattr(agent_db, "personality", ""),
                    "scenario": getattr(agent_db, "scenario", ""),
                    "message_example": getattr(agent_db, "message_example", ""),
                    "creator_notes": getattr(agent_db, "creator_notes", ""),
                    "tags": getattr(agent_db, "tags", []),
                    "character_version": getattr(agent_db, "character_version", "1.0"),
                    "extensions": getattr(agent_db, "extensions", {}),
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
                    # 创建新的Agent实例
                    model_config = get_agent_model_config(agent_data)

                    description = agent_data.get("description", "")

                    agent_name = agent_data.get("name", f"Agent_{agent_id[:8]}")
                    agent = Agent(
                        agent_id=agent_id,
                        name=agent_name,
                        model_config=model_config,
                        description=description,
                        # 主提示词和模式提示词参数
                        main_prompt=agent_data.get("main_prompt", ""),
                        mode_prompt=agent_data.get("mode_prompt", ""),
                        # 角色卡相关参数
                        personality=agent_data.get("personality", ""),
                        scenario=agent_data.get("scenario", ""),
                        message_example=agent_data.get("message_example", ""),
                        creator_notes=agent_data.get("creator_notes", ""),
                        tags=agent_data.get("tags", []),
                        character_version=agent_data.get("character_version", "1.0"),
                        extensions=agent_data.get("extensions", {}),
                    )

                    self.agents[agent_id] = agent
                    logger.info(f"Agent重新加载成功: {agent_id}")
                    return True

                except Exception as e:
                    logger.error(f"重新加载Agent失败 {agent_id}: {str(e)}")
                    return False

    def get_agent_prompt(self, agent_id: str) -> Optional[str]:
        """
        获取指定Agent的最终提示词

        Args:
            agent_id: Agent ID

        Returns:
            最终渲染的提示词，如果Agent不存在则返回None
        """
        with self._read_lock:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                return agent.get_final_prompt()
        return None

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
