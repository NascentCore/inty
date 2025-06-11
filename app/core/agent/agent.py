from typing import Any, Dict, Optional
import uuid
import time
import asyncio
from threading import Lock, RLock
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
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import Tool
from langchain_google_community import GoogleSearchAPIWrapper



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
        self._lock = RLock()  # 添加实例级别的锁

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
            prompt=system_prompt,
            store = postgres_store,
            checkpointer=self.checkpointer  # 使用实例级别的checkpointer
        )

    def chat(self, user_id: str, session_id: str, messages: dict[str, Any]):
        with self._lock:  # 保护并发访问
            self.last_used = time.time()

            # 创建独立的数据库连接
            conn_local = Connection.connect(
                settings.database.url,
                autocommit=True
            )
            
            try:
                history = PostgresChatMessageHistory(
                    table_name,
                    session_id,
                    sync_connection=conn_local
                )

                history.add_messages(messages["messages"])

                # 使用更精确的thread_id，包含agent_id避免混淆
                thread_id = f"{user_id}_{self.agent_id}"
                config = {'configurable':{'user_id':user_id,'thread_id':thread_id}}
                response = self.agent.invoke(messages, config)

                ai_messages = [message for message in response.get("messages",[]) if isinstance(message, AIMessage)]
                response = ai_messages[-1].content if ai_messages else "抱歉，我无法理解您的消息。请再试一次。"

                history.add_messages([AIMessage(content=response)])
                return response
            finally:
                conn_local.close()  # 确保连接关闭

    def chat_stream(self, user_id: str, session_id: str, messages: dict[str, Any]):
        with self._lock:  # 保护并发访问
            self.last_used = time.time()
            
            # 创建独立的数据库连接
            conn_local = Connection.connect(
                settings.database.url,
                autocommit=True
            )
            
            try:
                history = PostgresChatMessageHistory(
                    table_name,
                    session_id,
                    sync_connection=conn_local
                )

                # 使用更精确的thread_id，包含agent_id避免混淆
                thread_id = f"{user_id}_{self.agent_id}"
                config = {'configurable':{'user_id':user_id,'thread_id':thread_id}}

                for message_chunk,metadata in self.agent.stream(messages,config,stream_mode="messages"):
                    yield message_chunk, metadata
            finally:
                conn_local.close()  # 确保连接关闭


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
        self.lock = Lock()
        self._cleanup_task = None
        self._cleanup_started = False

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
            print("Agent清理任务已启动")
        except RuntimeError:
            # 没有运行的事件循环，延迟启动
            print("暂时无法启动清理任务，将在首次使用时启动")

    def _cleanup_idle_agents(self):
        """清理长时间空闲的Agent实例"""
        current_time = time.time()
        with self.lock:
            idle_agents = []
            for agent_id, agent in self.agents.items():
                if current_time - agent.last_used > self.max_idle_time:
                    idle_agents.append(agent_id)
            
            for agent_id in idle_agents:
                del self.agents[agent_id]
                print(f"清理空闲Agent: {agent_id}")

    async def get_agent(self, agent_data: dict) -> Agent:
        """
        获取或创建Agent实例
        
        Args:
            agent_data: Agent配置数据，包含id, name, prompt, settings等
        """
        # 尝试启动清理任务（如果还没启动）
        if not self._cleanup_started:
            self._start_cleanup_task()
        
        agent_id = agent_data['id']
        print(f"请求获取Agent实例 - Agent ID: {agent_id}")
        
        with self.lock:
            # 如果Agent已存在，直接返回
            if agent_id in self.agents:
                existing_agent = self.agents[agent_id]
                print(f"返回已存在的Agent实例 - Agent ID: {agent_id}, 实例ID: {existing_agent.agent_id}")
                
                # 验证实例中的agent_id是否与请求的一致
                if existing_agent.agent_id != agent_id:
                    print(f"警告：Agent实例ID不匹配！请求: {agent_id}, 实例: {existing_agent.agent_id}")
                    # 删除不匹配的实例，创建新的
                    del self.agents[agent_id]
                    # 继续到创建新实例的逻辑
                else:
                    # 更新最后使用时间（线程安全）
                    with existing_agent._lock:
                        existing_agent.last_used = time.time()
                    return existing_agent
            
            # 如果达到最大数量，清理最久未使用的Agent
            if len(self.agents) >= self.max_agents:
                oldest_agent_id = min(
                    self.agents.keys(),
                    key=lambda x: self.agents[x].last_used
                )
                del self.agents[oldest_agent_id]
                print(f"达到最大Agent数量，清理最旧的Agent: {oldest_agent_id}")
            
            # 创建新的Agent实例
            model_config = {}
            if agent_data.get('settings'):
                model_config = agent_data['settings'].get('model_config', {})
            
            system_prompt = agent_data.get('prompt', "你是一个聊天助手，请用中文回答用户的问题。")
            
            print(f"创建新的Agent实例 - Agent ID: {agent_id}, Name: {agent_data['name']}")
            
            try:
                agent = Agent(
                    agent_id=agent_id,  # 确保使用正确的agent_id
                    name=agent_data['name'],
                    model_config=model_config,
                    system_prompt=system_prompt
                )
                
                # 验证创建的Agent实例的agent_id
                if agent.agent_id != agent_id:
                    print(f"错误：创建的Agent实例ID不匹配！期望: {agent_id}, 实际: {agent.agent_id}")
                    raise ValueError(f"Agent实例创建失败: ID不匹配")
                
                self.agents[agent_id] = agent
                print(f"成功创建并缓存Agent实例 - Agent ID: {agent_id}, 实例ID: {agent.agent_id}")
                return agent
                
            except Exception as e:
                print(f"创建Agent实例失败 - Agent ID: {agent_id}, 错误: {str(e)}")
                # 确保失败的实例不会留在缓存中
                if agent_id in self.agents:
                    del self.agents[agent_id]
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
        return len(self.agents)

    def stop(self):
        """停止Agent管理器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()


# 创建全局Agent管理器实例
agent_manager = AgentManager()


if __name__ == "__main__":
    agent = Agent(
        agent_id="test",
        name="test",
        model_config={
            "model": "chatbot",
            "api_key": settings.agent.api_key,
            "base_url": settings.agent.base_url
        },
        system_prompt="你是AI性伴侣",
    )
    # response = agent.chat(user_id="123", session_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, "test")), messages={"messages": [HumanMessage(content="我最喜欢NBA的球星是kebe")]})
    # print(response)
    response = agent.chat(user_id="123", session_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, "test")), messages={"messages": [HumanMessage(content="fuck you !")]})
    print(response)