from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.verification_code import (VerificationCodeCreate,
                                           VerificationCodeVerify)
from app.services import verification_code as verification_code_service

router = APIRouter()


@router.post("/send", response_model=dict)
def send_verification_code(
    *,
    db: Session = Depends(deps.get_db),
    verification_code_in: VerificationCodeCreate
) -> dict:
    """
    Send verification code
    """
    # Create verification code
    verification_code = verification_code_service.create_verification_code(
        db=db,
        phone=verification_code_in.phone
    )
    
    # TODO: Call SMS service to send verification code
    # Here we temporarily return the verification code, in production it should be sent via SMS
    return {
        "message": "Verification code sent",
        "code": verification_code.code  # For testing only, should be removed in production
    }


@router.post("/verify", response_model=dict)
def verify_code(
    *,
    db: Session = Depends(deps.get_db),
    verification_code_in: VerificationCodeVerify
) -> dict:
    """
    Verify verification code
    """
    # Get valid verification code
    verification_code = verification_code_service.get_valid_verification_code(
        db=db,
        phone=verification_code_in.phone,
        code=verification_code_in.code
    )
    
    if not verification_code:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification code"
        )
    
    # Mark verification code as used
    verification_code_service.mark_code_as_used(db=db, verification_code=verification_code)
    
    return {
        "message": "Verification successful"
    } 