from typing import Any, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import Session

from app.models.resource import Resource
from app.models.resource import ImageResourceMetadata, ResourceType
from app.schemas.exclude_fields import EXCLUDE_FIELDS
from app.schemas.resource import ResourceCreate
from app.utils.image import ImageFormat, ImageSize
from app.schemas.resource import ResourceUpdate


def get_resource(db: Session, resource_id: str) -> Optional[Resource]:
    """
    Get resource by ID
    """
    return db.query(Resource).filter(Resource.id == resource_id).first()


def get_resources(
    db: Session, skip: int = 0, limit: int = 100
) -> List[Resource]:
    """
    Get resources list
    """
    return db.query(Resource).offset(skip).limit(limit).all()


def create_resource(
    db: Session,
    resource_in: ResourceCreate,
    user_id: str,
) -> Resource:
    """
    Create new resource
    """
    # 排除数据库模型中不存在的字段
    resource_data = resource_in.model_dump(exclude=EXCLUDE_FIELDS)

    # 创建资源记录，如果发生冲突则抛出异常
    db_resource = Resource(**resource_data, user_id=user_id)
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    return db_resource


def update_resource(
    db: Session, *, db_resource: Resource, resource_in: ResourceUpdate
) -> Resource:
    """
    Update resource
    """
    update_data = resource_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_resource, field, value)
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    return db_resource


def delete_resource(db: Session, *, db_resource: Resource) -> Resource:
    """
    Delete resource
    """
    db.delete(db_resource)
    db.commit()
    return db_resource


def create_image_resource(
    # TODO: 使用 AsyncSession 替换 Session
    db: Session,
    user_id: str,
    url: str,
    size: ImageSize,
    format: ImageFormat,
    byte_size: int,
    compressed: bool = False,
    uncompressed_image_url: Optional[str] = None,
    cropped: bool = False,
    uncropped_image_url: Optional[str] = None,
    gcs_url: Optional[str] = None,
    generation_prompt: Optional[str] = None,
    generation_model: Optional[str] = None,
    text_to_image_request: Optional[dict[str, Any]] = None,
    langsmith_trace_id: Optional[str] = None,
    langsmith_trace_url: Optional[str] = None,
) -> None:
    """
    创建图片资源记录的辅助函数
    一个记录存储 CDN URL（如 https://cdn.example.com/image.jpg）
    另一个记录存储 GCS URL（如 https://storage.googleapis.com/bucket/image.jpg）
    GCS URL 用于内部存储，CDN URL 用于外部 app 访问，其会做压缩裁切等功能。
    """
    # Create image resource metadata using the new Pydantic model
    image_metadata = ImageResourceMetadata(
        creator=user_id,
        size=size,
        content_type=f"image/{format.value}",
        byte_size=byte_size,
        compressed=compressed,
        uncompressed_image_url=uncompressed_image_url,
        cropped=cropped,
        uncropped_image_url=uncropped_image_url,
        gcs_url=gcs_url,
        generation_prompt=generation_prompt,
        generation_model=generation_model,
        text_to_image_request=text_to_image_request,
        langsmith_trace_id=langsmith_trace_id,
        langsmith_trace_url=langsmith_trace_url,
    )

    # Convert to dict for database storage
    resource_metadata = image_metadata.model_dump()
    resource = create_resource(
        db=db,
        resource_in=ResourceCreate(
            type=ResourceType.IMAGE,
            url=url,
            resource_metadata=resource_metadata,
        ),
        user_id=user_id,
    )
    logger.debug(f"创建图片资源记录成功，URL: {resource.url} 数据：{resource_metadata}")


async def async_create_resource(
    async_db: AsyncSession,
    resource_in: ResourceCreate,
    user_id: str,
) -> Resource:
    # 排除数据库模型中不存在的字段
    resource_data = resource_in.model_dump(exclude=EXCLUDE_FIELDS)

    # 创建资源记录，如果发生冲突则抛出异常
    db_resource = Resource(**resource_data, user_id=user_id)
    async_db.add(db_resource)
    await async_db.commit()
    await async_db.refresh(db_resource)
    return db_resource


async def async_create_image_resource(
    async_db: AsyncSession,
    user_id: str,
    url: str,
    size: ImageSize,
    format: ImageFormat,
    byte_size: int,
    compressed: bool = False,
    uncompressed_image_url: Optional[str] = None,
    cropped: bool = False,
    uncropped_image_url: Optional[str] = None,
    gcs_url: Optional[str] = None,
    generation_prompt: Optional[str] = None,
    reference_image_url: Optional[str] = None,
    user_reference_image_url: Optional[str] = None,
    agent_id: Optional[str] = None,
    only_include_ai_character: bool = False,
    generation_model: Optional[str] = None,
    text_to_image_request: Optional[dict[str, Any]] = None,
    langsmith_trace_id: Optional[str] = None,
    langsmith_trace_url: Optional[str] = None,
) -> None:
    """
    创建图片资源记录的辅助函数 (异步版本)
    一个记录存储 CDN URL（如 https://cdn.example.com/image.jpg）
    另一个记录存储 GCS URL（如 https://storage.googleapis.com/bucket/image.jpg）
    GCS URL 用于内部存储，CDN URL 用于外部 app 访问，其会做压缩裁切等功能。
    """
    # Create image resource metadata using the new Pydantic model
    image_metadata = ImageResourceMetadata(
        creator=user_id,
        size=size,
        content_type=f"image/{format.value}",
        byte_size=byte_size,
        compressed=compressed,
        uncompressed_image_url=uncompressed_image_url,
        cropped=cropped,
        uncropped_image_url=uncropped_image_url,
        gcs_url=gcs_url,
        generation_prompt=generation_prompt,
        generation_model=generation_model,
        text_to_image_request=text_to_image_request,
        reference_image_url=reference_image_url,
        user_reference_image_url=user_reference_image_url,
        reference_image_urls=[
            url
            for url in [reference_image_url, user_reference_image_url]
            if url is not None
        ],
        only_include_ai_character=only_include_ai_character,
        langsmith_trace_id=langsmith_trace_id,
        langsmith_trace_url=langsmith_trace_url,
    )

    # Convert to dict for database storage
    resource_metadata = image_metadata.model_dump()
    resource = await async_create_resource(
        async_db=async_db,
        resource_in=ResourceCreate(
            type=ResourceType.IMAGE,
            url=url,
            resource_metadata=resource_metadata,
            agent_id=agent_id,
        ),
        user_id=user_id,
    )
    logger.debug(f"创建图片资源记录成功，URL: {resource.url} 数据：{resource_metadata}")
