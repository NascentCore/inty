from datetime import datetime

from app.models.agent import AgentStatus, AgentVisibility
from app.schemas.agent import Agent


def test_agent_intro():
    agent = Agent(
        id="1",
        name="test",
        gender="female",
        readable_id="test-agent",
        status=AgentStatus.APPROVED,
        created_at=datetime.now(),
        intro="Hello, I am {{ char }}",
    )
    # 直接访问 intro 属性返回原始值（包含变量）
    assert agent.intro == "Hello, I am {{ char }}"
    # 序列化时 @field_serializer 生效，得到替换后的内容
    serialized = agent.model_dump()
    assert serialized["intro"] == "Hello, I am test"
