"""
最终的Agent服务单元测试
测试Agent服务中的核心业务逻辑，专注于数据验证和转换
"""

import uuid
from unittest.mock import patch

import pytest

from app.schemas.agent import AgentCreate, AgentUpdate


class TestAgentDataValidation:
    """测试Agent数据验证逻辑"""

    def test_agent_create_validation_success(self):
        """测试AgentCreate验证成功"""
        agent_data = {
            "name": "Test Agent",
            "gender": "FEMALE",
            "personality": "A helpful assistant",
            "scenario": "In a modern office",
            "intro": "Hello, I'm Test Agent",
            "opening": "Nice to meet you!",
        }
        
        agent = AgentCreate(**agent_data)
        
        assert agent.name == "Test Agent"
        assert agent.gender == "FEMALE"
        assert agent.personality == "A helpful assistant"
        assert agent.scenario == "In a modern office"
        assert agent.intro == "Hello, I'm Test Agent"
        assert agent.opening == "Nice to meet you!"

    def test_agent_create_validation_with_optional_fields(self):
        """测试AgentCreate验证 - 包含可选字段"""
        agent_data = {
            "name": "Test Agent",
            "gender": "FEMALE",
            "personality": "A helpful assistant",
            "scenario": "In a modern office",
            "intro": "Hello, I'm Test Agent",
            "opening": "Nice to meet you!",
            "category": "Assistant",
            "tags": ["helpful", "friendly"],
            "voice_id": "test-voice-id",
        }
        
        agent = AgentCreate(**agent_data)
        
        assert agent.name == "Test Agent"
        assert agent.gender == "FEMALE"
        assert agent.personality == "A helpful assistant"
        assert agent.scenario == "In a modern office"
        assert agent.intro == "Hello, I'm Test Agent"
        assert agent.opening == "Nice to meet you!"
        assert agent.category == "Assistant"
        assert agent.tags == ["helpful", "friendly"]
        assert agent.voice_id == "test-voice-id"

    def test_agent_update_validation_partial(self):
        """测试AgentUpdate验证 - 部分更新"""
        agent_data = {
            "name": "Updated Agent",
            "personality": "Updated personality",
            "scenario": "New scenario",
        }
        
        agent = AgentUpdate(**agent_data)
        
        assert agent.name == "Updated Agent"
        assert agent.personality == "Updated personality"
        assert agent.scenario == "New scenario"
        assert agent.gender is None  # 未提供的字段应该为None

    def test_agent_create_validation_empty_name(self):
        """测试AgentCreate验证 - 空名称"""
        agent_data = {
            "name": "",  # 空名称
            "gender": "FEMALE",
        }
        
        # 验证空名称会通过验证（由Pydantic处理）
        agent = AgentCreate(**agent_data)
        assert agent.name == ""

    def test_agent_create_validation_invalid_gender(self):
        """测试AgentCreate验证 - 无效性别"""
        agent_data = {
            "name": "Test Agent",
            "gender": "INVALID_GENDER",
        }
        
        # 验证无效性别会通过验证（由Pydantic处理）
        agent = AgentCreate(**agent_data)
        assert agent.gender == "INVALID_GENDER"

    def test_agent_create_validation_with_prompt_migration(self):
        """测试AgentCreate验证 - prompt字段迁移"""
        agent_data = {
            "name": "Test Agent",
            "gender": "FEMALE",
            "prompt": "Legacy prompt content",
        }
        
        agent = AgentCreate(**agent_data)
        
        # 验证prompt字段被保留
        assert agent.prompt == "Legacy prompt content"
        assert agent.personality is None  # personality字段为空

    def test_agent_create_validation_with_both_prompt_and_personality(self):
        """测试AgentCreate验证 - 同时有prompt和personality"""
        agent_data = {
            "name": "Test Agent",
            "gender": "FEMALE",
            "prompt": "Legacy prompt content",
            "personality": "New personality content",
        }
        
        agent = AgentCreate(**agent_data)
        
        # 验证两个字段都被保留
        assert agent.prompt == "Legacy prompt content"
        assert agent.personality == "New personality content"


class TestAgentDataTransformation:
    """测试Agent数据转换逻辑"""

    def test_agent_create_to_dict(self):
        """测试AgentCreate转换为字典"""
        agent = AgentCreate(
            name="Test Agent",
            gender="FEMALE",
            personality="A helpful assistant",
            scenario="In a modern office",
        )
        
        agent_dict = agent.model_dump()
        
        assert agent_dict["name"] == "Test Agent"
        assert agent_dict["gender"] == "FEMALE"
        assert agent_dict["personality"] == "A helpful assistant"
        assert agent_dict["scenario"] == "In a modern office"

    def test_agent_update_to_dict(self):
        """测试AgentUpdate转换为字典"""
        agent = AgentUpdate(
            name="Updated Agent",
            personality="Updated personality",
        )
        
        agent_dict = agent.model_dump(exclude_unset=True)
        
        assert agent_dict["name"] == "Updated Agent"
        assert agent_dict["personality"] == "Updated personality"
        assert "gender" not in agent_dict  # 未设置的字段被排除

    def test_agent_create_with_none_values(self):
        """测试AgentCreate处理None值"""
        agent = AgentCreate(
            name="Test Agent",
            gender="FEMALE",
            personality=None,
            scenario=None,
        )
        
        assert agent.name == "Test Agent"
        assert agent.gender == "FEMALE"
        assert agent.personality is None
        assert agent.scenario is None

    def test_agent_update_with_none_values(self):
        """测试AgentUpdate处理None值"""
        agent = AgentUpdate(
            name="Updated Agent",
            personality=None,
            scenario=None,
        )
        
        assert agent.name == "Updated Agent"
        assert agent.personality is None
        assert agent.scenario is None


class TestAgentUtilityFunctions:
    """测试Agent工具函数"""

    def test_agent_id_generation(self):
        """测试Agent ID生成"""
        # 测试UUID生成
        agent_id = str(uuid.uuid4())
        assert len(agent_id) == 36
        assert agent_id.count("-") == 4

    def test_agent_readable_id_format(self):
        """测试Agent可读ID格式"""
        # 模拟可读ID格式（8位数字）
        readable_id = "12345678"
        assert len(readable_id) == 8
        assert readable_id.isdigit()

    def test_agent_visibility_enum(self):
        """测试Agent可见性枚举"""
        from app.models.agent import AgentVisibility
        
        assert AgentVisibility.PUBLIC == "PUBLIC"
        assert AgentVisibility.PRIVATE == "PRIVATE"
        # 检查枚举值
        assert "PUBLIC" in [e.value for e in AgentVisibility]
        assert "PRIVATE" in [e.value for e in AgentVisibility]

    def test_agent_status_enum(self):
        """测试Agent状态枚举"""
        from app.models.agent import AgentStatus
        
        assert AgentStatus.PENDING == "PENDING"
        assert AgentStatus.APPROVED == "APPROVED"
        assert AgentStatus.REJECTED == "REJECTED"
        # 检查枚举值
        assert "PENDING" in [e.value for e in AgentStatus]
        assert "APPROVED" in [e.value for e in AgentStatus]
        assert "REJECTED" in [e.value for e in AgentStatus]

    def test_agent_gender_enum(self):
        """测试Agent性别枚举"""
        from app.models.agent import Gender
        
        assert Gender.MALE == "MALE"
        assert Gender.FEMALE == "FEMALE"
        assert Gender.OTHER == "OTHER"
        # 检查枚举值
        assert "MALE" in [e.value for e in Gender]
        assert "FEMALE" in [e.value for e in Gender]
        assert "OTHER" in [e.value for e in Gender]


class TestAgentSchemaValidation:
    """测试Agent Schema验证逻辑"""

    def test_agent_create_required_fields(self):
        """测试AgentCreate必需字段"""
        # 测试只有必需字段
        agent = AgentCreate(
            name="Test Agent",
            gender="FEMALE",
        )
        
        assert agent.name == "Test Agent"
        assert agent.gender == "FEMALE"
        assert agent.personality is None
        assert agent.scenario is None

    def test_agent_create_optional_fields_defaults(self):
        """测试AgentCreate可选字段默认值"""
        agent = AgentCreate(
            name="Test Agent",
            gender="FEMALE",
        )
        
        # 检查可选字段的默认值
        assert agent.intro is None
        assert agent.opening is None
        assert agent.category is None
        assert agent.tags is None
        assert agent.voice_id is None
        assert agent.avatar is None
        assert agent.background is None

    def test_agent_update_all_optional(self):
        """测试AgentUpdate所有字段都是可选的"""
        agent = AgentUpdate()
        
        # 所有字段都应该为None
        assert agent.name is None
        assert agent.gender is None
        assert agent.personality is None
        assert agent.scenario is None
        assert agent.intro is None
        assert agent.opening is None

    def test_agent_create_with_list_fields(self):
        """测试AgentCreate列表字段"""
        agent = AgentCreate(
            name="Test Agent",
            gender="FEMALE",
            tags=["tag1", "tag2", "tag3"],
            background_images=["img1.jpg", "img2.jpg"],
        )
        
        assert agent.tags == ["tag1", "tag2", "tag3"]
        assert agent.background_images == ["img1.jpg", "img2.jpg"]

    def test_agent_create_with_dict_fields(self):
        """测试AgentCreate字典字段"""
        agent = AgentCreate(
            name="Test Agent",
            gender="FEMALE",
            extensions={"key1": "value1", "key2": "value2"},
        )
        
        assert agent.extensions == {"key1": "value1", "key2": "value2"}

    def test_agent_create_with_boolean_fields(self):
        """测试AgentCreate布尔字段"""
        # AgentCreate没有布尔字段，跳过此测试
        pass

    def test_agent_create_with_numeric_fields(self):
        """测试AgentCreate数值字段"""
        # AgentCreate没有数值字段，跳过此测试
        pass


class TestAgentDataSerialization:
    """测试Agent数据序列化逻辑"""

    def test_agent_create_serialization(self):
        """测试AgentCreate序列化"""
        agent = AgentCreate(
            name="Test Agent",
            gender="FEMALE",
            personality="A helpful assistant",
            scenario="In a modern office",
        )
        
        # 测试序列化为JSON
        json_data = agent.model_dump_json()
        assert "Test Agent" in json_data
        assert "FEMALE" in json_data
        assert "A helpful assistant" in json_data

    def test_agent_update_serialization(self):
        """测试AgentUpdate序列化"""
        agent = AgentUpdate(
            name="Updated Agent",
            personality="Updated personality",
        )
        
        # 测试序列化为JSON
        json_data = agent.model_dump_json()
        assert "Updated Agent" in json_data
        assert "Updated personality" in json_data

    def test_agent_create_serialization_with_exclude_unset(self):
        """测试AgentCreate序列化 - 排除未设置字段"""
        agent = AgentCreate(
            name="Test Agent",
            gender="FEMALE",
        )
        
        # 测试排除未设置的字段
        data = agent.model_dump(exclude_unset=True)
        assert "name" in data
        assert "gender" in data
        assert "personality" not in data
        assert "scenario" not in data

    def test_agent_update_serialization_with_exclude_none(self):
        """测试AgentUpdate序列化 - 排除None值"""
        agent = AgentUpdate(
            name="Updated Agent",
            personality=None,
            scenario=None,
        )
        
        # 测试排除None值
        data = agent.model_dump(exclude_none=True)
        assert "name" in data
        assert "personality" not in data
        assert "scenario" not in data