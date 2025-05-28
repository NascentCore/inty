from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.verification_code import VerificationCodeCreate, VerificationCodeVerify
from app.services import verification_code as verification_code_service

router = APIRouter()


@router.post("/send", response_model=dict)
def send_verification_code(
    *,
    db: Session = Depends(deps.get_db),
    verification_code_in: VerificationCodeCreate
) -> dict:
    """
    发送验证码
    """
    # 创建验证码
    verification_code = verification_code_service.create_verification_code(
        db=db,
        phone=verification_code_in.phone
    )
    
    # TODO: 调用短信服务发送验证码
    # 这里暂时返回验证码，实际生产环境应该通过短信发送
    return {
        "message": "验证码已发送",
        "code": verification_code.code  # 仅用于测试，生产环境应删除
    }


@router.post("/verify", response_model=dict)
def verify_code(
    *,
    db: Session = Depends(deps.get_db),
    verification_code_in: VerificationCodeVerify
) -> dict:
    """
    验证验证码
    """
    # 获取有效的验证码
    verification_code = verification_code_service.get_valid_verification_code(
        db=db,
        phone=verification_code_in.phone,
        code=verification_code_in.code
    )
    
    if not verification_code:
        raise HTTPException(
            status_code=400,
            detail="验证码无效或已过期"
        )
    
    # 标记验证码为已使用
    verification_code_service.mark_code_as_used(db=db, verification_code=verification_code)
    
    return {
        "message": "验证成功"
    } 