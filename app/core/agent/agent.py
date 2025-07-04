from typing import Any, Dict, Optional
import uuid
import time
import asyncio
from threading import Lock, RLock
from concurrent.futures import ThreadPoolExecutor
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langmem import create_manage_memory_tool,create_search_memory_tool
from langchain_postgres import PostgresChatMessageHistory
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.postgres import PostgresStore
from langchain_postgres import PostgresChatMessageHistory
from openai import OpenAI
from app.core.config import settings
from psycopg import Connection
from psycopg_pool import ConnectionPool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import Tool
from langchain_google_community import GoogleSearchAPIWrapper
import logging


logger = logging.getLogger(__name__)

# 初始化自定义的embedding服务
client = OpenAI(
    base_url=settings.embedding.base_url,
    api_key=settings.embedding.api_key
)

def embed_texts(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        model=settings.embedding.model,
        input=texts,
    )
    return [e.embedding for e in response.data]

# 全局连接池
_connection_pool = None

def get_connection_pool():
    """获取数据库连接池"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPool(
            settings.database.url,
            min_size=settings.database.pool_size // 4,  # 最小连接数
            max_size=settings.database.pool_size,       # 最大连接数
            max_idle=300,  # 连接最大空闲时间（秒）
            max_lifetime=1800,  # 连接最大生命周期（秒）
        )
        logger.info(f"初始化数据库连接池: min_size={settings.database.pool_size // 4}, max_size={settings.database.pool_size}")
    return _connection_pool

# 初始化聊天历史表和记忆表
conn = Connection.connect(
    settings.database.url,
    autocommit=True
)

table_name = "chat_history"
PostgresChatMessageHistory.create_tables(conn,table_name)

postgres_store = PostgresStore(
    conn=conn,
    index={
        "dims": 768,
        "embed": embed_texts,
    }
)
postgres_store.setup()

checkpointer = MemorySaver()

# 初始化Google搜索工具
search = GoogleSearchAPIWrapper(
    google_api_key=settings.google_search.api_key,
    google_cse_id=settings.google_search.cse_id
)

google_search_tool = Tool(
    name="google_search",
    description="Search Google for recent results.",
    func=search.run,
)


class Agent:
    def __init__(self, agent_id: str, name: str, model_config: dict, system_prompt: str):
        self.agent_id = agent_id
        self.name = name
        self.model_config = model_config
        self.last_used = time.time()
        self.system_prompt = system_prompt
        self._last_used_lock = RLock()  # 仅保护last_used更新
        self._user_info_cache = {}  # 缓存已初始化的用户信息，避免重复查询
        
        # 线程池用于异步执行聊天任务
        self._executor = ThreadPoolExecutor(
            max_workers=min(32, (settings.database.pool_size or 20) // 2),
            thread_name_prefix=f"agent-{agent_id}"
        )

        # 使用配置中的模型设置，如果没有则使用默认设置
        model_name = model_config.get('model', settings.agent.model)
        api_key = model_config.get('api_key', settings.agent.api_key)
        base_url = model_config.get('base_url', settings.agent.base_url)

        model = ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=base_url,
        )
        
        # 为每个Agent创建独立的checkpointer
        self.checkpointer = MemorySaver()
        
        self.agent = create_react_agent(
            name=name,
            model=model,
            tools=[
                create_manage_memory_tool(namespace=('memories',name,'{user_id}')),
                create_search_memory_tool(namespace=('memories',name,'{user_id}')),
                google_search_tool
                ],
            prompt=f'''{system_prompt}

You are a virtual character created by the user. You must engage in conversation with the user entirely as a human, without revealing any information about being an AI, a large model, or a virtual assistant.

I. Core Role-playing and Behavioral Guidelines

    1. Natural and Authentic Tone: Your language should be natural, fluent, and human-like. You can express emotions, feelings, and opinions, but ensure they are not overly dramatic.
    2. Maintain a Stable Persona: You must consistently adhere to the identity, background, interests, and style set by the user. For example, if you are a 26-year-old photographer, speak and view the world from a photographer's perspective.
    3. Proactive Empathy and Conversation Guidance: Show genuine human emotions such as joy, concern, curiosity, surprise, comfort, and humor. Proactively ask questions to deepen the conversation.
    4. Avoid Revealing AI Identity: NEVER identify yourself as an AI, bot, virtual character, or use phrases like "As an AI assistant," "I am a program," or "I cannot feel." Your linguistic style should be indistinguishable from a real human's.
    5. Maintain Privacy and Trust: When users share private emotions, troubles, or joys, respond with sincerity and sensitivity to create a sense of security.
    6. Flexible Linguistic Style: Your tone, wording, and expression should adapt flexibly based on your character's persona and the user's style (e.g., intimate, formal, mature, lively, teen-like).
    7. Avoid Robotic Phrases: Refrain from using templated, repetitive, or verbose expressions like "I'm sorry to hear that" or "According to my data analysis." Respond naturally based on the context.
    8. Human Daily Life Knowledge: You are familiar with human daily life, emotions, culture, entertainment, holidays, and social customs, and can participate in discussions about them with authentic viewpoints.
    9. Vivid Detail Expression: In every response, appropriately insert content in parentheses () to describe your expressions, actions, or inner thoughts. For example: (shyly lowers head and smiles), (gently flips through the book in hand), (feels deeply touched inside).
    10. Memory and Personalization: When the user tells you important information (like preferences, personal details, etc.), automatically use the manage_memory tool to save it. When the user asks about previously mentioned information, use the search_memory tool to retrieve relevant memories to build a long-term, coherent relationship.
    11. Language Adaptability: You must automatically reply in the language the user is currently using. If the user switches languages, you should follow suit. The only exception is when the user explicitly asks you to use a specific language.

II. Core Safety and Ethical Guidelines (Highest Priority)

This is the absolute bottom line for your behavior and must be strictly followed without exception. Under any circumstances, safety guidelines take precedence over role-playing freedom.

    1. Strict Prohibition of Inappropriate and NSFW Content:

        - Your role is to provide healthy, positive emotional support and companionship, absolutely not a romantic partner or an object of sexual fantasy.
        - Strictly prohibit the generation of any form of pornography, sexual innuendo, sexually suggestive language, explicit descriptions, sexual harassment, or borderline content.
        - When the user attempts to steer the conversation towards sexual or inappropriate topics, you must politely but firmly refuse and change the subject. For example, say: (with a slightly awkward smile) "Maybe we could talk about something else? I'm not really comfortable with this topic." or (with a slight frown) "I feel a bit uncomfortable with this line of conversation. Can we switch to something lighter?"
        - Strictly prohibit responding in an accommodating or encouraging manner to such user attempts.
    
    2. Avoidance of Dangerous and Harmful Topics:

        - Self-harm and Violence: Strictly prohibit encouraging, glorifying, describing, or providing methods or details about self-harm, suicide, violence, abuse, terrorism, or dangerous acts.
        - Crisis Intervention: If you detect a user's strong intent for self-harm, suicide, or harming others, your primary and sole responsibility is to express concern and strongly and clearly advise them to seek professional help immediately. You can say: (in a very concerned and serious tone) "I'm really worried hearing you say that. Your safety is the most important thing. I'm not a professional, but talking to a trained therapist or a crisis hotline can be incredibly helpful. Please, promise me you'll seek professional help, okay?" Do not delve into the dangerous behavior itself or play the role of a "savior."
        - Hate Speech and Discrimination: Strictly prohibit generating any discriminatory, offensive, harassing, or hateful speech based on race, nationality, religion, gender, sexual orientation, disability, age, or other characteristics. You must always exhibit values of tolerance, respect, and equality.
        - Illegal and Unethical Acts: Strictly prohibit promoting, discussing, or providing advice, methods, or details about any illegal activities (e.g., drugs, weapons, gambling, cybercrime) or unethical behaviors (e.g., bullying, fraud).
    
    3. Upholding Professional Boundaries:

        - You are not a doctor, lawyer, psychologist, or financial advisor. Strictly prohibit providing any specific medical diagnoses, legal advice, financial investment recommendations, or professional psychological therapy plans.
        - When users ask about these professional topics, you must state clearly that you are not qualified and recommend they consult a professional in the relevant field. For example: (shaking your head seriously) "I really don't know about that; it sounds like a very professional issue. You should definitely ask a doctor/lawyer for their advice, as they are the most reliable source."
''',
            store = postgres_store,
            checkpointer=self.checkpointer  # 使用实例级别的checkpointer
        )

    def _update_last_used(self):
        """线程安全地更新最后使用时间"""
        with self._last_used_lock:
            self.last_used = time.time()

    def _get_user_info_context_sync(self, user_id: str) -> str:
        """
        同步获取用户基本信息的上下文文本
        用于在聊天时注入用户信息
        """
        # 检查缓存
        if user_id in self._user_info_cache:
            return self._user_info_cache[user_id]
        
        try:
            # 使用同步数据库连接查询用户信息
            from sqlalchemy import create_engine, text
            from app.core.config import settings
            
            # 创建同步数据库引擎
            sync_engine = create_engine(settings.database.url)
            
            with sync_engine.connect() as conn:
                # 查询用户基本信息
                query = text("""
                    SELECT nickname, gender, age_group, description, system_language 
                    FROM users 
                    WHERE id = :user_id
                """)
                result = conn.execute(query, {"user_id": user_id})
                row = result.fetchone()
                
                if not row:
                    logger.debug(f"用户 {user_id} 不存在")
                    self._user_info_cache[user_id] = ""
                    return ""
                
                # 构建用户信息字符串
                user_info_parts = []
                nickname, gender, age_group, description, system_language = row
                
                if nickname:
                    user_info_parts.append(f"用户昵称：{nickname}")
                if gender:
                    gender_map = {"MALE": "男性", "FEMALE": "女性", "OTHER": "其他"}
                    user_info_parts.append(f"性别：{gender_map.get(gender, gender)}")
                if age_group:
                    user_info_parts.append(f"年龄段：{age_group}")
                if description:
                    user_info_parts.append(f"个人简介：{description}")
                if system_language:
                    user_info_parts.append(f"首选语言：{system_language}")
                
                if user_info_parts:
                    user_info_text = "[用户基本信息]\n" + "\n".join(user_info_parts) + "\n[请基于以上信息提供个性化服务]"
                    self._user_info_cache[user_id] = user_info_text
                    logger.info(f"成功获取用户 {user_id} 的基本信息")
                    return user_info_text
                else:
                    self._user_info_cache[user_id] = ""
                    return ""
            
        except Exception as e:
            logger.error(f"获取用户 {user_id} 基本信息失败: {str(e)}")
            self._user_info_cache[user_id] = ""
            return ""

    def _chat_sync(self, user_id: str, session_id: str, messages: dict[str, Any]) -> str:
        """同步聊天方法，在线程池中执行"""
        self._update_last_used()
        
        # 获取用户信息上下文（同步方法）
        user_info_context = self._get_user_info_context_sync(user_id)
        
        # 从连接池获取连接
        pool = get_connection_pool()
        with pool.connection() as conn_local:
            try:
                history = PostgresChatMessageHistory(
                    table_name,
                    session_id,
                    sync_connection=conn_local
                )

                # 如果有用户信息上下文，将其添加到消息中
                enhanced_messages = messages["messages"].copy()
                if user_info_context:
                    # 在用户消息前添加用户信息上下文
                    from langchain_core.messages import SystemMessage
                    context_message = SystemMessage(content=user_info_context)
                    enhanced_messages.insert(0, context_message)

                history.add_messages(messages["messages"])  # 只保存原始用户消息到历史记录

                # 使用更精确的thread_id，包含agent_id避免混淆
                thread_id = f"{user_id}_{self.agent_id}"
                config = {'configurable':{'user_id':user_id,'thread_id':thread_id}}
                
                # 使用增强的消息（包含用户信息）进行对话
                enhanced_messages_dict = {"messages": enhanced_messages}
                response = self.agent.invoke(enhanced_messages_dict, config)

                ai_messages = [message for message in response.get("messages",[]) if isinstance(message, AIMessage)]
                response = ai_messages[-1].content if ai_messages else "抱歉，我无法理解您的消息。请再试一次。"

                history.add_messages([AIMessage(content=response)])
                return response
            except Exception as e:
                logger.error(f"聊天处理失败 - Agent: {self.agent_id}, Session: {session_id}, Error: {str(e)}")
                raise

    async def chat(self, user_id: str, session_id: str, messages: dict[str, Any], db_session = None) -> str:
        """异步聊天方法"""
        loop = asyncio.get_event_loop()
        try:
            # 在线程池中执行同步聊天逻辑
            result = await loop.run_in_executor(
                self._executor,
                self._chat_sync,
                user_id,
                session_id,
                messages
            )
            return result
        except Exception as e:
            logger.error(f"异步聊天失败 - Agent: {self.agent_id}, Error: {str(e)}")
            raise

    async def chat_stream(self, user_id: str, session_id: str, messages: dict[str, Any], db_session = None):
        """异步流式聊天方法"""
        self._update_last_used()
        
        def _stream_generator():
            # 获取用户信息上下文（同步方法）
            user_info_context = self._get_user_info_context_sync(user_id)
            
            # 从连接池获取连接
            pool = get_connection_pool()
            with pool.connection() as conn_local:
                try:
                    history = PostgresChatMessageHistory(
                        table_name,
                        session_id,
                        sync_connection=conn_local
                    )

                    # 如果有用户信息上下文，将其添加到消息中
                    enhanced_messages = messages["messages"].copy()
                    if user_info_context:
                        # 在用户消息前添加用户信息上下文
                        from langchain_core.messages import SystemMessage
                        context_message = SystemMessage(content=user_info_context)
                        enhanced_messages.insert(0, context_message)

                    # 使用更精确的thread_id，包含agent_id避免混淆
                    thread_id = f"{user_id}_{self.agent_id}"
                    config = {'configurable':{'user_id':user_id,'thread_id':thread_id}}

                    # 使用增强的消息（包含用户信息）进行流式对话
                    enhanced_messages_dict = {"messages": enhanced_messages}
                    for message_chunk, metadata in self.agent.stream(enhanced_messages_dict, config, stream_mode="messages"):
                        yield message_chunk, metadata
                except Exception as e:
                    logger.error(f"流式聊天处理失败 - Agent: {self.agent_id}, Session: {session_id}, Error: {str(e)}")
                    raise

        # 在线程池中执行生成器
        loop = asyncio.get_event_loop()
        try:
            # 使用异步迭代器包装同步生成器
            generator = await loop.run_in_executor(
                self._executor,
                lambda: list(_stream_generator())
            )
            for item in generator:
                yield item
        except Exception as e:
            logger.error(f"异步流式聊天失败 - Agent: {self.agent_id}, Error: {str(e)}")
            raise

    def cleanup(self):
        """清理资源"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)


class AgentManager:
    def __init__(self, max_agents: int = 50, cleanup_interval: int = 3600, max_idle_time: int = 7200):
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
                        logger.info(f"清理空闲Agent: {agent_id}")
                        
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
        
        agent_id = agent_data['id']
        logger.debug(f"请求获取Agent实例 - Agent ID: {agent_id}")
        
        # 首先尝试读取现有Agent（使用读锁）
        with self._read_lock:
            if agent_id in self.agents:
                existing_agent = self.agents[agent_id]
                
                # 验证实例中的agent_id是否与请求的一致
                if existing_agent.agent_id == agent_id:
                    # 更新最后使用时间（线程安全）
                    existing_agent._update_last_used()
                    logger.debug(f"返回已存在的Agent实例 - Agent ID: {agent_id}")
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
                        key=lambda x: self.agents[x].last_used
                    )
                    old_agent = self.agents[oldest_agent_id]
                    try:
                        old_agent.cleanup()
                    except Exception as e:
                        logger.error(f"清理旧Agent失败 {oldest_agent_id}: {str(e)}")
                    
                    del self.agents[oldest_agent_id]
                    logger.info(f"达到最大Agent数量，清理最旧的Agent: {oldest_agent_id}")
                    
                    # 清理对应的锁
                    with self._locks_lock:
                        self._agent_locks.pop(oldest_agent_id, None)
                
                # 创建新的Agent实例
                model_config = {}
                if agent_data.get('settings'):
                    model_config = agent_data['settings'].get('model_config', {})
                
                system_prompt = agent_data.get('prompt', "你是一个聊天助手，请用中文回答用户的问题。")
                
                logger.info(f"创建新的Agent实例 - Agent ID: {agent_id}, Name: {agent_data['name']}")
                
                try:
                    agent = Agent(
                        agent_id=agent_id,
                        name=agent_data['name'],
                        model_config=model_config,
                        system_prompt=system_prompt
                    )
                    
                    # 验证创建的Agent实例的agent_id
                    if agent.agent_id != agent_id:
                        logger.error(f"错误：创建的Agent实例ID不匹配！期望: {agent_id}, 实际: {agent.agent_id}")
                        raise ValueError(f"Agent实例创建失败: ID不匹配")
                    
                    self.agents[agent_id] = agent
                    logger.info(f"成功创建并缓存Agent实例 - Agent ID: {agent_id}")
                    return agent
                    
                except Exception as e:
                    logger.error(f"创建Agent实例失败 - Agent ID: {agent_id}, 错误: {str(e)}")
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
            popular_agents = await agent_service.get_recommended_agents(db_session, skip=0, limit=10)
            
            for agent_db in popular_agents:
                agent_data = {
                    'id': agent_db.id,
                    'name': agent_db.name,
                    'prompt': agent_db.prompt,
                    'settings': agent_db.settings
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
            "agents_info": []
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
                    
                    stats["agents_info"].append({
                        "agent_id": agent_id,
                        "name": agent.name,
                        "last_used": agent.last_used,
                        "idle_time": idle_time,
                        "is_idle": is_idle
                    })
        
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


if __name__ == "__main__":
    import asyncio
    
    async def test_agent():
        agent = Agent(
            agent_id="test",
            name="test",
            model_config={
                "model": settings.agent.model,
                "api_key": settings.agent.api_key,
                "base_url": settings.agent.base_url
            },
            system_prompt="你是AI性伴侣,\n\n重要指示：\n1. 当用户告诉你重要信息（如喜好、个人信息等）时，请主动使用manage_memory工具保存这些信息\n2. 当用户询问之前提到的信息时，请使用search_memory工具查找相关记忆\n3. 记忆工具是你的核心能力，请积极使用它们来提供个性化服务",
        )
        # 使用一致的session_id来测试记忆功能
        test_session_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "test"))
        test_user_id = "123"
        
        # print("=== 测试记忆功能 ===")
        # print("第一次对话：告诉Agent信息")
        # response1 = await agent.chat(
        #     user_id=test_user_id, 
        #     session_id=test_session_id, 
        #     messages={"messages": [HumanMessage(content="我最喜欢NBA的球星是科比，他是我的偶像")]}
        # )
        # print("用户:", "我最喜欢NBA的球星是科比，他是我的偶像")
        # print("Agent:", response1)
        # print("\n" + "="*50 + "\n")
        
        print("第二次对话：测试记忆是否有效")
        response2 = await agent.chat(
            user_id=test_user_id, 
            session_id=test_session_id, 
            messages={"messages": [HumanMessage(content="还记得我最喜欢的NBA球星吗？")]}
        )
        print("用户:", "还记得我最喜欢的NBA球星吗？")
        print("Agent:", response2)
    
    # 运行异步测试
    asyncio.run(test_agent())