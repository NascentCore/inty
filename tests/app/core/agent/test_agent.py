from langchain_core.messages import HumanMessage
from app.core.agent.agent import Agent
import uuid
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from app.core.agent import prompts
from app.core.agent.agent import Agent
from app.core.agent.personalities import EVERYONE_HATES_YOU, EVERYONE_LIKES_YOU
from app.core.config import global_config_loaded_from_config_yaml


class TestAgentChat:
    """Test class for Agent.chat() method - Happy Path"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.agent_id = "test-agent-123"
        self.agent_name = "Test Agent"
        self.user_id = "test-user-456"
        self.session_id = str(uuid.uuid4())

        self.model_config = {
            "model": global_config_loaded_from_config_yaml.agent.model,
            "api_key": global_config_loaded_from_config_yaml.agent.api_key,
            "base_url": global_config_loaded_from_config_yaml.agent.base_url,
            "temperature": 0.7,
            "max_tokens": 100,
        }

        self.test_messages = {"messages": [HumanMessage(content="Who are you?")]}

        self.agent = None

        # Teardown fixture: https://stackoverflow.com/a/22638709
        yield

        if self.agent:
            try:
                self.agent.cleanup()
            except Exception as e:
                print(f"Warning: Failed to cleanup agent: {e}")

    @pytest.mark.asyncio
    async def test_agent_chat_happy_path(self):
        """
        Test the happy path of Agent.chat() method

        This test verifies that:
        1. Agent can be initialized with proper configuration
        2. Agent.chat() method can be called successfully
        3. The method returns a response string
        4. All dependencies are properly mocked to avoid external calls
        """

        # Create agent instance
        self.agent = Agent(
            agent_id=self.agent_id,
            name=self.agent_name,
            model_config=self.model_config,
            description="Test agent for unit testing",
            personality=EVERYONE_HATES_YOU.to_prompt(),
            main_prompt=prompts.CHAT_SYS_PROMPT,
            mode_prompt=prompts.HELPFUL_MODE_PROMPT,
        )

        response = await self.agent.chat(
            user_id=self.user_id,
            session_id=self.session_id,
            messages=self.test_messages,
        )

        assert response == "Hello, how are you today?!"


# 初始化聊天历史表和记忆表
db_url = global_config_loaded_from_config_yaml.database.url
logger.debug(f"初始化聊天历史表和记忆表, database url: {db_url}")
conn = Connection.connect(db_url, autocommit=True)

table_name = "chat_history"
PostgresChatMessageHistory.create_tables(conn, table_name)

postgres_store = PostgresStore(
    conn=conn,
    index={
        "dims": 768,
        "embed": embed_texts,
    },
)
postgres_store.setup()

# TODO: These should be replaced by test_agent.py.
if __name__ == "__main__":
    import asyncio

    async def test_agent():
        agent = Agent(
            agent_id="test",
            name="test",
            model_config={
                "model": global_config_loaded_from_config_yaml.agent.model,
                "api_key": global_config_loaded_from_config_yaml.agent.api_key,
                "base_url": global_config_loaded_from_config_yaml.agent.base_url,
            },
            description="测试Agent",
            # 测试用的主提示词和模式提示词
            main_prompt="",  # 使用全局默认
            mode_prompt="",  # 使用全局默认
            # 将原来的system_prompt转换为personality
            personality="你是AI性伴侣,\n\n重要指示：\n1. 当用户告诉你重要信息（如喜好、个人信息等）时，请主动使用manage_memory工具保存这些信息\n2. 当用户询问之前提到的信息时，请使用search_memory工具查找相关记忆\n3. 记忆工具是你的核心能力，请积极使用它们来提供个性化服务",
        )
        # 使用一致的session_id来测试记忆功能
        test_session_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "test"))
        test_user_id = "123"

        print("=== 测试记忆功能 ===")
        print("第一次对话：告诉Agent信息")
        response1 = await agent.chat(
            user_id=test_user_id,
            session_id=test_session_id,
            messages={
                "messages": [
                    HumanMessage(content="我最喜欢NBA的球星是科比，他是我的偶像")
                ]
            },
        )
        print("用户:", "我最喜欢NBA的球星是科比，他是我的偶像")
        print("Agent:", response1)
        print("\n" + "=" * 50 + "\n")

        print("第二次对话：测试记忆是否有效")
        response2 = await agent.chat(
            user_id=test_user_id,
            session_id=test_session_id,
            messages={
                "messages": [HumanMessage(content="还记得我最喜欢的NBA球星吗？")]
            },
        )
        print("用户:", "还记得我最喜欢的NBA球星吗？")
        print("Agent:", response2)

    # 运行异步测试
    asyncio.run(test_agent())


def test_agent__create_dynamic_prompt_runnable():
    agent = Agent(
        agent_id="test",
        name="test",
        model_config={},
    )
    runnable = agent._create_dynamic_prompt_runnable()
    runnable.invoke({"user_profile": "test", "messages": [HumanMessage(content="test")]})
