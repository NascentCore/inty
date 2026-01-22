from datetime import datetime

from app.models.agent import AgentStatus, AgentVisibility
from app.schemas.agent import Agent


def test_agent_intro():
    """测试 Agent intro 字段在序列化时保持原始值。

    注意：{{ char }} 和 {{ user }} 变量的替换是在 chat service 渲染时进行的，
    而不是在 schema 序列化时。因此 model_dump() 返回的是原始模板值。
    """
    agent = Agent(
        id="1",
        name="test",
        gender="female",
        readable_id="test-agent",
        status=AgentStatus.APPROVED,
        created_at=datetime.now(),
        version=1,
        intro="Hello, I am {{ char }}",
    )
    # 直接访问 intro 属性返回原始值（包含变量）
    assert agent.intro == "Hello, I am {{ char }}"
    # 序列化时也返回原始值，变量替换在聊天渲染时进行
    serialized = agent.model_dump()
    assert (
        serialized["intro"] == "Hello, I am {{ char }}"
    ), "model_dump 返回原始模板值，变量替换在聊天渲染时进行"
    serialized_json = agent.model_dump_json()
    assert (
        '"intro":"Hello, I am {{ char }}"' in serialized_json
    ), "model_dump_json 返回原始模板值"
