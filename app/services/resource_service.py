from typing import List, Optional

from loguru import logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import Session

from app import models, schemas
from app.models.resource import ResourceType
from app.schemas.exclude_fields import EXCLUDE_FIELDS
from app.schemas.resource import ResourceCreate
from app.utils.image import ImageFormat, ImageSize


def get_resource(db: Session, resource_id: str) -> Optional[models.Resource]:
    """
    Get resource by ID
    """
    return db.query(models.Resource).filter(models.Resource.id == resource_id).first()


def get_resources(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Resource]:
    """
    Get resources list
    """
    return db.query(models.Resource).offset(skip).limit(limit).all()


def create_resource(
    db: Session,
    resource_in: schemas.ResourceCreate,
    user_id: str,
    on_conflict_do_nothing: bool = False,
) -> Optional[models.Resource]:
    """
    Create new resource
    """
    # 排除数据库模型中不存在的字段
    resource_data = resource_in.model_dump(exclude=EXCLUDE_FIELDS)

    if on_conflict_do_nothing:
        # 使用 PostgreSQL 的 INSERT ... ON CONFLICT DO NOTHING
        stmt = (
            insert(models.Resource)
            .values(**resource_data, user_id=user_id)
            .on_conflict_do_nothing(index_elements=["url"])
        )
        db.execute(stmt)
        db.commit()
        # 冲突时返回 None,不抛异常
        return None
    else:
        # 保持原有逻辑
        db_resource = models.Resource(**resource_data, user_id=user_id)
        db.add(db_resource)
        db.commit()
        db.refresh(db_resource)
        return db_resource


def update_resource(
    db: Session, *, db_resource: models.Resource, resource_in: schemas.ResourceUpdate
) -> models.Resource:
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


def delete_resource(db: Session, *, db_resource: models.Resource) -> models.Resource:
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
) -> None:
    """
    创建图片资源记录的辅助函数
    """
    resource_metadata = {
        "creator": user_id,
        "size": size.model_dump(),
        "content_type": f"image/{format.value}",
        "byte_size": byte_size,
        "compressed": compressed,
        "uncompressed_image_url": uncompressed_image_url,
        "cropped": cropped,
        "uncropped_image_url": uncropped_image_url,
    }

    # Add GCS URL to metadata if provided
    if gcs_url:
        resource_metadata["gcs_url"] = gcs_url
    resource = create_resource(
        db=db,
        resource_in=ResourceCreate(
            type=ResourceType.IMAGE,
            url=url,
            resource_metadata=resource_metadata,
        ),
        user_id=user_id,
        on_conflict_do_nothing=False,  # Disable conflict handling for now
    )
    if resource:
        logger.debug(
            f"创建图片资源记录成功，URL: {resource.url} 数据：{resource_metadata}"
        )
    else:
        logger.debug(f"图片资源记录已存在，跳过插入，URL: {url}")


async def async_create_resource(
    async_db: AsyncSession,
    resource_in: schemas.ResourceCreate,
    user_id: str,
    on_conflict_do_nothing: bool = False,
) -> Optional[models.Resource]:
    # 排除数据库模型中不存在的字段
    resource_data = resource_in.model_dump(exclude=EXCLUDE_FIELDS)

    if on_conflict_do_nothing:
        stmt = (
            insert(models.Resource)
            .values(**resource_data, user_id=user_id)
            .on_conflict_do_nothing(index_elements=["url"])
        )
        await async_db.execute(stmt)
        await async_db.commit()
        return None
    else:
        db_resource = models.Resource(**resource_data, user_id=user_id)
        async_db.add(db_resource)
        await async_db.commit()
        await async_db.refresh(db_resource)
        return db_resource


async def async_create_image_resource(
    async_db: AsyncSession,
    user_id: str,
    url: str,
    size: ImageSize,
) -> None:
    """
    创建图片资源记录的辅助函数
    """
    resource_metadata = {
        "size": size.model_dump(),
    }
    resource = await async_create_resource(
        async_db=async_db,
        resource_in=ResourceCreate(
            type=ResourceType.IMAGE,
            url=url,
            resource_metadata=resource_metadata,
        ),
        user_id=user_id,
        on_conflict_do_nothing=True,
    )
    if resource:
        logger.debug(
            f"创建图片资源记录成功，URL: {resource.url} 数据：{resource_metadata}"
        )
    else:
        logger.debug(f"图片资源记录已存在，跳过插入，URL: {url}")
