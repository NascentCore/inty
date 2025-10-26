"""
Simplified unit tests for data validation and serialization
测试数据验证和序列化的核心逻辑 - 简化版本
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.schemas.agent import (
    Agent,
    AgentBase,
    AgentCreate,
    AgentInDB,
    AgentList,
    AgentMetaData,
    AgentSortConfig,
    AgentSortOption,
    AgentUpdate,
    CreatorAgentStats,
    ModelConfig,
    TextToImageRequest,
)
from app.schemas.user import User, UserBase, UserCreate, UserInDBBase, UserUpdate
from app.schemas.chat import Chat, ChatBase, ChatCreate, ChatInDB, ChatUpdate


class TestAgentValidation:
    """测试Agent数据验证逻辑"""

    def test_agent_base_validation_success(self):
        """测试AgentBase验证成功"""
        agent_data = {
            "name": "Test Agent",
            "gender": "FEMALE",
            "personality": "A helpful assistant",
            "scenario": "In a modern office",
            "intro": "Hello, I'm Test Agent",
            "opening": "Nice to meet you!",
        }
        
        agent = AgentBase(**agent_data)
        
        assert agent.name == "Test Agent"
        assert agent.gender == "FEMALE"
        assert agent.personality == "A helpful assistant"
        assert agent.scenario == "In a modern office"
        assert agent.intro == "Hello, I'm Test Agent"
        assert agent.opening == "Nice to meet you!"

    def test_agent_create_validation_success(self):
        """测试AgentCreate验证成功"""
        agent_data = {
            "name": "Test Agent",
            "gender": "FEMALE",
            "personality": "A helpful assistant",
            "scenario": "In a modern office",
            "intro": "Hello, I'm Test Agent",
            "opening": "Nice to meet you!",
            "category": "Assistant",
            "tags": ["helpful", "friendly"],
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

    def test_model_config_validation_success(self):
        """测试ModelConfig验证成功"""
        config_data = {
            "model": "anthropic/claude-3.5-sonnet",
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 0.9,
        }
        
        config = ModelConfig(**config_data)
        
        assert config.model == "anthropic/claude-3.5-sonnet"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
        assert config.top_p == 0.9

    def test_model_config_validation_invalid_temperature(self):
        """测试ModelConfig验证 - 无效温度"""
        config_data = {
            "model": "anthropic/claude-3.5-sonnet",
            "temperature": 3.0,  # 超出范围
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(**config_data)
        
        assert "temperature" in str(exc_info.value)

    def test_agent_meta_data_validation_success(self):
        """测试AgentMetaData验证成功"""
        meta_data = {
            "score": 4,  # 使用整数
            "comment": "Great agent!",
        }
        
        meta = AgentMetaData(**meta_data)
        
        assert meta.score == 4
        assert meta.comment == "Great agent!"

    def test_agent_sort_option_validation(self):
        """测试AgentSortOption验证"""
        # 测试有效的排序选项
        valid_options = ["created_asc", "created_desc", "random", "score_based_random"]
        for option in valid_options:
            sort_option = AgentSortOption(option)
            assert sort_option == option

        # 测试无效的排序选项
        with pytest.raises(ValueError):
            AgentSortOption("invalid_option")

    def test_agent_sort_config_validation_success(self):
        """测试AgentSortConfig验证成功"""
        config_data = {
            "sort": "created_desc",
            "sort_seed": "test-seed",
        }
        
        config = AgentSortConfig(**config_data)
        
        assert config.sort == AgentSortOption.CREATED_DESC
        assert config.sort_seed == "test-seed"

    def test_text_to_image_request_validation_success(self):
        """测试TextToImageRequest验证成功"""
        request_data = {
            "prompt": "A beautiful sunset over mountains",
            "negative_prompt": "blurry, low quality",
            "enhance_prompt": True,
            "count": 2,
        }
        
        request = TextToImageRequest(**request_data)
        
        assert request.prompt == "A beautiful sunset over mountains"
        assert request.negative_prompt == "blurry, low quality"
        assert request.enhance_prompt is True
        assert request.count == 2


class TestAgentSerialization:
    """测试Agent数据序列化逻辑"""

    def test_agent_in_db_serialization(self):
        """测试AgentInDB序列化"""
        agent_data = {
            "id": str(uuid.uuid4()),
            "readable_id": "12345678",
            "name": "Test Agent",
            "gender": "FEMALE",
            "creator_id": str(uuid.uuid4()),
            "visibility": "PUBLIC",
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        agent = AgentInDB(**agent_data)
        
        assert agent.id == agent_data["id"]
        assert agent.readable_id == agent_data["readable_id"]
        assert agent.name == agent_data["name"]
        assert agent.gender == agent_data["gender"]
        assert agent.creator_id == agent_data["creator_id"]
        assert agent.visibility == agent_data["visibility"]
        assert agent.status == agent_data["status"]

    def test_agent_serialization_with_llm_config(self):
        """测试Agent序列化 - 包含LLM配置"""
        agent_data = {
            "id": str(uuid.uuid4()),
            "readable_id": "12345678",
            "name": "Test Agent",
            "gender": "FEMALE",
            "creator_id": str(uuid.uuid4()),
            "visibility": "PUBLIC",
            "status": "PENDING",
            "settings": {
                "llm_config": {
                    "model": "anthropic/claude-3.5-sonnet",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                }
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        agent = Agent(**agent_data)
        
        # 验证LLM配置被正确提取（通过序列化方法）
        serialized_llm_config = agent.serialize_llm_config(agent.llm_config)
        assert serialized_llm_config is not None
        assert serialized_llm_config.model == "anthropic/claude-3.5-sonnet"
        assert serialized_llm_config.temperature == 0.7
        assert serialized_llm_config.max_tokens == 2048

    def test_agent_serialization_with_meta_data(self):
        """测试Agent序列化 - 包含元数据"""
        agent_data = {
            "id": str(uuid.uuid4()),
            "readable_id": "12345678",
            "name": "Test Agent",
            "gender": "FEMALE",
            "creator_id": str(uuid.uuid4()),
            "visibility": "PUBLIC",
            "status": "PENDING",
            "meta_data": {
                "score": 4,
                "comment": "Great agent!",
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        agent = Agent(**agent_data)
        
        # 验证元数据被正确转换
        assert agent.meta_data is not None
        assert agent.meta_data.score == 4
        assert agent.meta_data.comment == "Great agent!"

    def test_agent_list_serialization(self):
        """测试AgentList序列化"""
        agents_data = [
            {
                "id": str(uuid.uuid4()),
                "readable_id": "11111111",
                "name": "Agent 1",
                "gender": "FEMALE",
                "creator_id": str(uuid.uuid4()),
                "visibility": "PUBLIC",
                "status": "PENDING",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": str(uuid.uuid4()),
                "readable_id": "22222222",
                "name": "Agent 2",
                "gender": "MALE",
                "creator_id": str(uuid.uuid4()),
                "visibility": "PUBLIC",
                "status": "PENDING",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        ]
        
        agent_list = AgentList(
            items=[Agent(**agent_data) for agent_data in agents_data],
            total=2,
            page=1,
            page_size=10,
        )
        
        assert len(agent_list.items) == 2
        assert agent_list.total == 2
        assert agent_list.page == 1
        assert agent_list.page_size == 10

    def test_creator_agent_stats_serialization(self):
        """测试CreatorAgentStats序列化"""
        stats_data = {
            "creator_id": str(uuid.uuid4()),
            "public_agents_count": 5,
            "total_public_agents_follows": 100,
        }
        
        stats = CreatorAgentStats(**stats_data)
        
        assert stats.creator_id == stats_data["creator_id"]
        assert stats.public_agents_count == 5
        assert stats.total_public_agents_follows == 100


class TestUserValidation:
    """测试用户数据验证逻辑"""

    def test_user_base_validation_success(self):
        """测试UserBase验证成功"""
        user_data = {
            "nickname": "test_user",
            "system_language": "en",
            "gender": "FEMALE",
        }
        
        user = UserBase(**user_data)
        
        assert user.nickname == "test_user"
        assert user.system_language == "en"
        assert user.gender == "FEMALE"

    def test_user_create_validation_success(self):
        """测试UserCreate验证成功"""
        user_data = {
            "nickname": "test_user",
            "system_language": "en",
            "gender": "FEMALE",
            "auth_type": "PHONE",
            "phone": "+1234567890",
        }
        
        user = UserCreate(**user_data)
        
        assert user.nickname == "test_user"
        assert user.system_language == "en"
        assert user.gender == "FEMALE"
        assert user.auth_type == "PHONE"
        assert user.phone == "+1234567890"

    def test_user_update_validation_partial(self):
        """测试UserUpdate验证 - 部分更新"""
        user_data = {
            "nickname": "updated_user",
            "system_language": "zh",
        }
        
        user = UserUpdate(**user_data)
        
        assert user.nickname == "updated_user"
        assert user.system_language == "zh"
        assert user.gender is None  # 未提供的字段应该为None

    def test_user_in_db_serialization(self):
        """测试UserInDBBase序列化"""
        user_data = {
            "id": str(uuid.uuid4()),
            "readable_id": "12345678",
            "nickname": "test_user",
            "system_language": "en",
            "auth_type": "PHONE",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        user = UserInDBBase(**user_data)
        
        assert user.id == user_data["id"]
        assert user.readable_id == user_data["readable_id"]
        assert user.nickname == user_data["nickname"]
        assert user.system_language == user_data["system_language"]
        assert user.auth_type == user_data["auth_type"]
        assert user.is_active == user_data["is_active"]


class TestChatValidation:
    """测试聊天数据验证逻辑"""

    def test_chat_create_validation_success(self):
        """测试ChatCreate验证成功"""
        chat_data = {
            "agent_id": str(uuid.uuid4()),
        }
        
        chat = ChatCreate(**chat_data)
        
        assert chat.agent_id == chat_data["agent_id"]

    def test_chat_update_validation_partial(self):
        """测试ChatUpdate验证 - 部分更新"""
        chat_data = {
            "request_id": "test-request-id",
        }
        
        chat = ChatUpdate(**chat_data)
        
        assert chat.request_id == "test-request-id"

    def test_chat_in_db_serialization(self):
        """测试ChatInDB序列化"""
        chat_data = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "agent_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        chat = ChatInDB(**chat_data)
        
        assert chat.id == chat_data["id"]
        assert chat.user_id == chat_data["user_id"]
        assert chat.agent_id == chat_data["agent_id"]

    def test_chat_serialization_with_last_message(self):
        """测试Chat序列化 - 包含最后消息"""
        chat_data = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "agent_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        # 模拟最后消息
        last_message = "Hello! How can I help you?"
        
        chat = Chat(**chat_data)
        chat.last_message = last_message
        
        assert chat.last_message == "Hello! How can I help you?"