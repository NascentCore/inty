from typing import Any
import uuid
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

class Agent:
    def __init__(self, name: str, model_config: dict, system_prompt: str):
        self.name = name
        self.model_config = model_config

        model = ChatOpenAI(
            model=settings.agent.model,
            openai_api_key=settings.agent.api_key,
            openai_api_base=settings.agent.base_url,
        )
        self.checkpointer = MemorySaver()
        self.agent = create_react_agent(
            name=name,
            model=model,
            tools=[
                create_manage_memory_tool(namespace=('memories',name,'{user_id}')),
                create_search_memory_tool(namespace=('memories',name,'{user_id}'))
                ],
            prompt=system_prompt,
            store = postgres_store,
            checkpointer=checkpointer
        )

    def chat(self, user_id: str, session_id: str, messages: dict[str, Any]):

        history = PostgresChatMessageHistory(
            table_name,
            session_id,
            sync_connection=conn
        )

        history.add_messages(messages["messages"])

        config = {'configurable':{'user_id':user_id,'thread_id':user_id}}
        response = self.agent.invoke(messages, config)

        ai_messages = [message for message in response.get("messages",[]) if isinstance(message, AIMessage)]
        response = ai_messages[-1].content if ai_messages else "抱歉，我无法理解您的消息。请再试一次。"

        history.add_messages([AIMessage(content=response)])
        return response



    def chat_stream(self, user_id: str, session_id: str, messages: dict[str, Any]):
        history = PostgresChatMessageHistory(
            table_name,
            session_id,
            sync_connection=conn
        )

        config = {'configurable':{'user_id':user_id,'thread_id':user_id}}

        for message_chunk,metadata in self.agent.stream(messages,config,stream_mode="messages"):
            print(message_chunk,metadata)

class AgentManager:
    pass


if __name__ == "__main__":
    agent = Agent(
        name="test",
        model_config={},
        system_prompt="You are a helpful assistant.",
    )
    # response = agent.chat(user_id="123", session_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, "test")), messages={"messages": [HumanMessage(content="我的显示偏好是黑色")]})
    # print(response)
    response = agent.chat(user_id="123", session_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, "test")), messages={"messages": [HumanMessage(content="还记得我的显示偏好吗")]})
    print(response)