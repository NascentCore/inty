import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_async_db
from app.core.agent.agent import agent_manager
from app.core.config import settings
from app.models.agent import Agent
from app.models.chat import Chat
from app.models.chat_settings import ChatSettings
from app.services import chat_history_service
from app.services.chat_service import generate_session_id

logger = logging.getLogger(__name__)


class KeepTalkingService:
    def __init__(
        self,
        check_interval: Optional[int] = None,
        max_idle_time: Optional[int] = None,
        max_keep_talking_messages: Optional[int] = None,
    ):
        """
        初始化Keep Talking服务

        Args:
            check_interval: 检查间隔（秒），None时使用配置文件值
            max_idle_time: 最大空闲时间（秒），超过此时间发送keep_talking消息，None时使用配置文件值
            max_keep_talking_messages: 单次会话中最多发送的keep_talking消息数量，None时使用配置文件值
        """
        self.check_interval = (
            check_interval
            if check_interval is not None
            else settings.keep_talking.check_interval
        )
        self.max_idle_time = (
            max_idle_time
            if max_idle_time is not None
            else settings.keep_talking.max_idle_time
        )
        self.max_keep_talking_messages = (
            max_keep_talking_messages
            if max_keep_talking_messages is not None
            else settings.keep_talking.max_keep_talking_messages
        )
        self._running = False
        self._task = None
        # 跟踪每个会话已发送的keep_talking消息数量
        self._keep_talking_counts: Dict[str, int] = {}

    async def start(self):
        """启动Keep Talking服务"""
        if self._running:
            logger.warning("Keep Talking服务已经在运行")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Keep Talking服务已启动")

    async def stop(self):
        """停止Keep Talking服务"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Keep Talking服务已停止")

    def reset_keep_talking_count(self, chat_id: str):
        """重置会话的keep_talking消息计数（当用户发送新消息时调用）"""
        if chat_id in self._keep_talking_counts:
            del self._keep_talking_counts[chat_id]

    async def _monitor_loop(self):
        """监控循环"""
        logger.info("Keep Talking监控循环已启动")

        while self._running:
            try:
                await self._check_idle_chats()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Keep Talking监控循环出错: {str(e)}")
                await asyncio.sleep(self.check_interval)

    async def _check_idle_chats(self):
        """检查空闲的聊天会话"""
        async for db in get_async_db():
            try:
                # 查询开启了keep_talking功能的活跃聊天会话
                result = await db.execute(
                    select(Chat)
                    .options(
                        selectinload(Chat.settings),
                        selectinload(Chat.agent),
                        selectinload(Chat.user),
                    )
                    .join(ChatSettings, Chat.id == ChatSettings.chat_id)
                    .where(
                        and_(Chat.is_active == True, ChatSettings.keep_talking == True)
                    )
                )
                chats = result.scalars().all()

                logger.info(f"检查到 {len(chats)} 个开启keep_talking的活跃会话")

                # 使用UTC时间进行比较
                current_time = datetime.now(timezone.utc)
                idle_chats = []

                # 检查每个会话的最后消息时间
                for chat in chats:
                    try:
                        session_id = generate_session_id(chat.id)
                        last_message_data = (
                            chat_history_service.get_last_message_with_timestamp(
                                session_id
                            )
                        )

                        if not last_message_data:
                            # 没有消息历史，跳过
                            continue

                        last_message_time = last_message_data["timestamp"]
                        if not last_message_time:
                            continue

                        # 确保时区一致性
                        try:
                            if last_message_time.tzinfo is None:
                                # 如果数据库时间没有时区信息，假设为UTC
                                last_message_time = last_message_time.replace(
                                    tzinfo=timezone.utc
                                )
                            else:
                                # 如果有时区信息，转换为UTC进行比较
                                last_message_time = last_message_time.astimezone(
                                    timezone.utc
                                )
                        except Exception as tz_e:
                            logger.warning(
                                f"会话 {chat.id} 时区转换失败: {str(tz_e)}, 跳过此会话"
                            )
                            continue

                        # 检查是否超过空闲时间阈值
                        time_diff = current_time - last_message_time
                        idle_seconds = time_diff.total_seconds()

                        logger.debug(
                            f"会话 {chat.id} 空闲时间: {idle_seconds:.0f}秒, 阈值: {self.max_idle_time}秒"
                        )

                        if idle_seconds > self.max_idle_time:
                            # 检查是否已达到keep_talking消息上限（不再检查最后一条消息的发送者）
                            keep_talking_count = self._keep_talking_counts.get(
                                chat.id, 0
                            )
                            if keep_talking_count < self.max_keep_talking_messages:
                                idle_chats.append(chat)
                                logger.debug(
                                    f"会话 {chat.id} 符合keep_talking条件，已发送消息数: {keep_talking_count}"
                                )
                            else:
                                logger.debug(
                                    f"会话 {chat.id} 已达到keep_talking消息上限: {keep_talking_count}"
                                )

                    except Exception as e:
                        logger.error(f"检查会话 {chat.id} 时出错: {str(e)}")
                        continue

                logger.info(f"发现 {len(idle_chats)} 个需要发送keep_talking消息的会话")

                # 为空闲会话发送keep_talking消息
                for chat in idle_chats:
                    try:
                        await self._send_keep_talking_message(chat)
                    except Exception as e:
                        logger.error(
                            f"为会话 {chat.id} 发送keep_talking消息时出错: {str(e)}"
                        )

            except Exception as e:
                logger.error(f"检查空闲会话时出错: {str(e)}")
            finally:
                break  # 只需要一个数据库会话

    async def _send_keep_talking_message(self, chat: Chat):
        """为指定会话发送keep_talking消息"""
        try:
            logger.info(f"为会话 {chat.id} 发送keep_talking消息")

            # 获取agent实例
            agent_data = {
                "id": chat.agent.id,
                "name": chat.agent.name or f"Agent_{chat.agent.id[:8]}",  # 防护性检查
                "settings": chat.agent.settings,
                # 主提示词和模式提示词字段
                "main_prompt": getattr(chat.agent, "main_prompt", ""),
                "mode_prompt": getattr(chat.agent, "mode_prompt", ""),
                # 添加角色卡字段支持
                "personality": getattr(chat.agent, "personality", ""),
                "scenario": getattr(chat.agent, "scenario", ""),
                "message_example": getattr(chat.agent, "message_example", ""),
                "creator_notes": getattr(chat.agent, "creator_notes", ""),
                "tags": getattr(chat.agent, "tags", []),
                "character_version": getattr(chat.agent, "character_version", "1.0"),
                "extensions": getattr(chat.agent, "extensions", {}),
            }
            agent = await agent_manager.get_agent(agent_data)

            # 生成session_id
            session_id = generate_session_id(chat.id)

            # 获取聊天历史作为上下文
            chat_history = chat_history_service.get_messages_paginated(
                session_id=session_id, limit=10, offset=0  # 获取最近10条消息作为上下文
            )

            messages_context = chat_history.get("messages", [])

            # 构建keep_talking提示词
            keep_talking_prompt = self._generate_keep_talking_prompt(
                messages_context, chat.agent.name
            )

            # 构建消息格式
            messages = {"messages": [HumanMessage(content=keep_talking_prompt)]}

            # 调用agent生成响应
            response = await agent.chat(
                user_id=chat.user_id,
                session_id=session_id,
                messages=messages,
                # 注意：Keep Talking服务中暂不传递db_session，避免复杂性
                # 用户信息在正常聊天中已经被缓存，keep_talking可以使用缓存的信息
            )

            # 更新keep_talking计数
            self._keep_talking_counts[chat.id] = (
                self._keep_talking_counts.get(chat.id, 0) + 1
            )

            logger.info(
                f"成功为会话 {chat.id} 发送keep_talking消息: {response[:100]}..."
            )

        except Exception as e:
            logger.error(f"发送keep_talking消息失败 - 会话 {chat.id}: {str(e)}")
            raise

    def _generate_keep_talking_prompt(
        self, messages_context: List[Dict], agent_name: str
    ) -> str:
        """生成keep_talking提示词"""

        # 检查最后一条消息的发送者
        last_message_from_user = False
        if messages_context:
            last_message = messages_context[-1]
            last_message_from_user = last_message.get("role") == "user"

        # 根据最后消息发送者选择不同的提示词策略
        if last_message_from_user:
            # 用户最后发言但没有回复的情况
            base_prompts = [
                "请基于前面的对话内容，主动延续这个话题或者提出一个相关的问题来继续我们的聊天。",
                "请根据之前的聊天内容，主动分享一些相关的想法或者询问用户的看法。",
                "请基于我们刚才的对话，提供一些额外的信息或建议。",
                "请主动根据前面的对话内容，继续这个话题或者提出新的相关问题。",
                "请基于之前的聊天内容，主动分享一些有趣的观点或者询问相关问题。",
            ]
        else:
            # agent最后发言的情况，需要更自然地继续对话
            base_prompts = [
                "请基于当前的对话话题，继续分享一些相关的内容或者换个角度来聊这个话题。",
                "请延续刚才的话题，提供一些补充信息或者询问用户的想法。",
                "请基于我们正在讨论的内容，进一步展开话题或者分享相关的见解。",
                "请继续当前的对话主题，可以分享一些有趣的细节或者相关的思考。",
                "请自然地延续我们的对话，可以从不同的角度来探讨这个话题。",
            ]

        # 根据对话历史的长度选择不同的提示词
        if len(messages_context) == 0:
            return "请主动开始一个友好的对话。"
        elif len(messages_context) <= 2:
            prompt = "请基于刚开始的对话，主动提出一个相关的话题或问题来继续聊天。"
        else:
            # 从基础提示词中随机选择一个
            import random

            prompt = random.choice(base_prompts)

        # 添加对话历史摘要（如果有的话）
        if messages_context:
            recent_messages = messages_context[-4:]  # 最近4条消息，获取更多上下文
            context_summary = "最近的对话内容：\n"
            for msg in recent_messages:
                role_name = "用户" if msg.get("role") == "user" else agent_name
                content = msg.get("content", "")[:120]  # 稍微增加长度限制
                context_summary += f"{role_name}: {content}\n"

            prompt = f"{context_summary}\n{prompt}"

        # 根据最后消息发送者添加不同的行为指导
        if last_message_from_user:
            guidance = "\n\n请注意：这是一个主动延续对话的消息，请保持自然、友好的语调，不要提及没有回复这件事。"
        else:
            guidance = "\n\n请注意：请自然地继续对话，就像是正常聊天的延续，保持话题的连贯性和趣味性。"

        prompt += guidance

        return prompt


# 全局keep_talking服务实例
keep_talking_service = KeepTalkingService()
