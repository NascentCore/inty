import asyncio
import time
from threading import Lock
from typing import Any, Dict, Optional

from app.core.agent.agent import Agent, get_agent_model_config

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml


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

    def get_agent_template_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定Agent的模版信息

        Args:
            agent_id: Agent ID

        Returns:
            包含模版信息的字典，如果Agent不存在则返回None
        """
        with self._read_lock:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                return agent.get_template_info()
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
