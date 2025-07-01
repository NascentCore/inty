from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime
from app.api import deps
from app.models.report import ReportStatus
from app.schemas.report import ReportReason, ReportCreate, ReportQuery, ReportOut, TargetType
from app.services import report_service
from app.db.session import get_async_db
from app.models.user import User
from app.schemas.response import APIResponse, PaginationData
from app.utils.gcs import upload_to_gcs
from app.core.config import settings
from loguru import logger

router = APIRouter()

@router.get("/reasons", response_model=APIResponse[List[ReportReason]])
async def get_report_reasons(
    db: AsyncSession = Depends(get_async_db)
):
    """Get report reasons list"""
    try:
        reasons = await report_service.list_report_reasons(db)
        return APIResponse.success(data=reasons)
    except Exception as e:
        logger.error(f"Failed to get report reasons: {str(e)}")
        return APIResponse.error(message=str(e))

@router.post("/upload-image", response_model=APIResponse[dict])
async def upload_report_image(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Upload image for report"""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            return APIResponse.error(message="Only image files are allowed")
        
        # Validate file size (e.g., max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        file_data = await file.read()
        if len(file_data) > max_size:
            return APIResponse.error(message="File size exceeds 10MB limit")
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        file_extension = file.filename.split('.')[-1].lower() if file.filename and '.' in file.filename else 'jpg'
        
        # Generate storage path
        report_image_path = f"reports/images/{current_user.id}/{timestamp}-{unique_id}.{file_extension}"
        
        # Upload to GCS
        url = upload_to_gcs(file_data, file.content_type, settings.gcs.bucket, report_image_path)
        
        logger.info(f"Report image uploaded successfully: {url}")
        return APIResponse.success(data={"url": url})
        
    except Exception as e:
        logger.error(f"Failed to upload report image: {str(e)}")
        return APIResponse.error(message="Image upload failed")

@router.post("/", response_model=APIResponse)
async def create_report(
    report_in: ReportCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Submit report"""
    try:
        report = await report_service.create_report(db, report_in, current_user.id)
        return APIResponse.success()
    except Exception as e:
        logger.error(f"Failed to create report: {str(e)}")
        return APIResponse.error(message=str(e))

@router.get("/", response_model=APIResponse[PaginationData[ReportOut]])
async def list_reports(
    reason_ids: Optional[List[int]] = Query(None),
    target_id: Optional[str] = None,
    target_type: Optional[TargetType] = None,
    status: Optional[ReportStatus] = None,
    reporter_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """Query report records (requires admin permission)"""
    if not current_user.is_superuser:
        return APIResponse.error(message="Unauthorized access")
    try:
        skip = (page - 1) * page_size
        query = ReportQuery(
            reason_ids=reason_ids,
            target_id=target_id,
            target_type=target_type,
            status=status,
            reporter_id=reporter_id,
            skip=skip,
            limit=page_size
        )
        items, total = await report_service.query_reports(db, query)
        items = [ReportOut.model_validate(obj, from_attributes=True) for obj in items]
        total_pages = (total + page_size - 1) // page_size if page_size else 1
        pagination = PaginationData[ReportOut](
            list=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        return APIResponse.success(data=pagination)
    except Exception as e:
        logger.error(f"Failed to query reports: {str(e)}")
        return APIResponse.error(message=str(e)) 