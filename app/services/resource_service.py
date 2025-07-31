from typing import List, Optional

from sqlalchemy.orm import Session

from app import models, schemas


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
