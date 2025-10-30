"""
集成测试：验证 text-to-image API 生成图片时正确保存 prompts 到 resources 表
"""
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.core.config import global_config_loaded_from_config_yaml
from app.models import Base
from app.models.resource import ImageResourceMetadata, Resource, ResourceType
from app.services.resource_service import async_create_image_resource
from app.utils.image import ImageFormat, ImageSize


def create_test_user(db, user_id: str) -> models.User:
    """创建测试用户"""
    existing_user = db.query(models.User).filter(models.User.id == user_id).one_or_none()
    if existing_user:
        return existing_user
    
    readable_id = str(uuid.uuid4().int)[:8]
    test_user = models.User(
        id=user_id,
        readable_id=readable_id,
        auth_type=models.AuthType.GUEST,
        system_language="zh",
        is_active=True,
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    return test_user


@pytest.mark.asyncio
async def test_text_to_image_saves_prompts_to_resources():
    """
    测试 async_create_image_resource 函数是否正确保存 prompts 到 resources 表
    
    验证点：
    1. 调用 async_create_image_resource 时传入 prompts 参数
    2. 检查 resources 表中是否创建了对应记录
    3. 验证 resource_metadata 中的 prompts 字段包含正确的 prompt 和 negative_prompt
    """
    # 使用本地数据库
    DATABASE_URL = global_config_loaded_from_config_yaml.database.url
    
    # 创建测试数据库引擎和会话
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # 创建 async session
    async_engine = create_async_engine(
        global_config_loaded_from_config_yaml.database.async_url
    )
    async_session = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # 创建测试用户
    user_id = f"testuser-prompts-{uuid.uuid4().hex}"
    test_user = create_test_user(db, user_id)
    
    # 准备测试数据
    test_url = f"https://cdn.test.com/test-image-{uuid.uuid4().hex}.jpg"
    test_prompt = "A beautiful sunset over mountains"
    test_negative_prompt = "blurry, low quality"
    test_size = ImageSize(width=1024, height=1024)
    
    # 调用 async_create_image_resource 并传入 prompts
    async with async_session() as async_db:
        await async_create_image_resource(
            async_db=async_db,
            user_id=user_id,
            url=test_url,
            size=test_size,
            format=ImageFormat.JPEG,
            byte_size=102400,
            compressed=False,
            cropped=False,
            gcs_url=f"gs://test-bucket/test-image-{uuid.uuid4().hex}.jpg",
            prompts={
                "prompt": test_prompt,
                "negative_prompt": test_negative_prompt,
            },
        )
        await async_db.commit()
    
    # 从数据库查询生成的资源记录
    resource = db.query(Resource).filter(Resource.url == test_url).one_or_none()
    
    # 验证资源记录存在
    assert resource is not None, f"未找到 URL 为 {test_url} 的资源记录"
    
    # 验证资源类型
    assert resource.type == ResourceType.IMAGE
    
    # 验证 resource_metadata 存在
    assert resource.resource_metadata is not None
    
    # 解析 resource_metadata
    metadata = ImageResourceMetadata(**resource.resource_metadata)
    
    # 验证 prompts 字段存在且包含正确的值
    assert metadata.prompts is not None, "resource_metadata 中缺少 prompts 字段"
    assert "prompt" in metadata.prompts, "prompts 中缺少 prompt 字段"
    assert "negative_prompt" in metadata.prompts, "prompts 中缺少 negative_prompt 字段"
    
    # 验证 prompts 内容正确
    assert metadata.prompts["prompt"] == test_prompt
    assert metadata.prompts["negative_prompt"] == test_negative_prompt
    
    # 清理测试数据
    db.close()
    await async_engine.dispose()


@pytest.mark.asyncio
async def test_text_to_image_saves_prompts_without_negative_prompt():
    """
    测试在没有 negative_prompt 时也能正确保存 prompts
    
    验证点：
    1. 调用 async_create_image_resource 时不提供 negative_prompt
    2. 检查 resources 表中 prompts 字段的 negative_prompt 为 None
    """
    DATABASE_URL = global_config_loaded_from_config_yaml.database.url
    
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    async_engine = create_async_engine(
        global_config_loaded_from_config_yaml.database.async_url
    )
    async_session = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    user_id = f"testuser-prompts-no-neg-{uuid.uuid4().hex}"
    test_user = create_test_user(db, user_id)
    
    test_url = f"https://cdn.test.com/test-image-{uuid.uuid4().hex}.jpg"
    test_prompt = "A serene lake at dawn"
    test_size = ImageSize(width=1024, height=1024)
    
    # 调用 async_create_image_resource，negative_prompt 为 None
    async with async_session() as async_db:
        await async_create_image_resource(
            async_db=async_db,
            user_id=user_id,
            url=test_url,
            size=test_size,
            format=ImageFormat.JPEG,
            byte_size=102400,
            compressed=False,
            cropped=False,
            gcs_url=f"gs://test-bucket/test-image-{uuid.uuid4().hex}.jpg",
            prompts={
                "prompt": test_prompt,
                "negative_prompt": None,
            },
        )
        await async_db.commit()
    
    # 查询资源记录
    resource = db.query(Resource).filter(Resource.url == test_url).one_or_none()
    
    assert resource is not None
    metadata = ImageResourceMetadata(**resource.resource_metadata)
    
    # 验证 prompts 字段存在
    assert metadata.prompts is not None
    assert metadata.prompts["prompt"] == test_prompt
    assert metadata.prompts["negative_prompt"] is None
    
    # 清理
    db.close()
    await async_engine.dispose()

