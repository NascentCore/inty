from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import deps
from app.services import resource_service

router = APIRouter()

@router.get("/", response_model=List[schemas.Resource])
def list_resources(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get resources list
    """
    resources = resource_service.get_resources(db, skip=skip, limit=limit)
    return resources

@router.post("/", response_model=schemas.Resource)
def create_resource(
    *,
    db: Session = Depends(deps.get_db),
    resource_in: schemas.ResourceCreate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new resource
    """
    resource = resource_service.create_resource(db, resource_in=resource_in, user_id=current_user.id)
    return resource

@router.get("/{resource_id}", response_model=schemas.Resource)
def get_resource(
    *,
    db: Session = Depends(deps.get_db),
    resource_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get resource by ID
    """
    resource = resource_service.get_resource(db, resource_id=resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource

@router.put("/{resource_id}", response_model=schemas.Resource)
def update_resource(
    *,
    db: Session = Depends(deps.get_db),
    resource_id: str,
    resource_in: schemas.ResourceUpdate,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update resource
    """
    resource = resource_service.get_resource(db, resource_id=resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    resource = resource_service.update_resource(db, db_resource=resource, resource_in=resource_in)
    return resource

@router.delete("/{resource_id}", response_model=schemas.Resource)
def delete_resource(
    *,
    db: Session = Depends(deps.get_db),
    resource_id: str,
    current_user: schemas.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete resource
    """
    resource = resource_service.get_resource(db, resource_id=resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    resource = resource_service.delete_resource(db, db_resource=resource)
    return resource 