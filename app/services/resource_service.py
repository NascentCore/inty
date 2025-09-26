from typing import List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from app import models, schemas
from app.models.resource import ResourceType
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
    db: Session, resource_in: schemas.ResourceCreate, user_id: str
) -> models.Resource:
    """
    Create new resource
    """
    db_resource = models.Resource(**resource_in.dict(), user_id=user_id)
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
    update_data = resource_in.dict(exclude_unset=True)
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
    resource = create_resource(
        db=db,
        resource_in=ResourceCreate(
            type=ResourceType.IMAGE,
            url=url,
            resource_metadata=resource_metadata,
        ),
        user_id=user_id,
    )
    logger.debug(f"创建图片资源记录成功，URL: {resource.url}")
