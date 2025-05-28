import random
import string
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.verification_code import VerificationCode
from app.schemas.verification_code import VerificationCodeCreate


def generate_verification_code(length: int = 6) -> str:
    """生成验证码"""
    return ''.join(random.choices(string.digits, k=length))


def create_verification_code(
    db: Session,
    phone: str,
    code: str,
    expires_in: int = 300  # 5分钟有效期
) -> VerificationCode:
    """创建验证码记录"""
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    db_code = VerificationCode(
        phone=phone,
        code=code,
        expires_at=expires_at
    )
    db.add(db_code)
    db.commit()
    db.refresh(db_code)
    return db_code


def verify_code(
    db: Session,
    phone: str,
    code: str
) -> bool:
    """验证验证码"""
    db_code = db.query(VerificationCode).filter(
        VerificationCode.phone == phone,
        VerificationCode.code == code,
        VerificationCode.expires_at > datetime.utcnow(),
        VerificationCode.is_used == False
    ).first()
    
    if not db_code:
        return False
    
    # 标记验证码已使用
    db_code.is_used = True
    db.add(db_code)
    db.commit()
    
    return True


def send_verification_code(phone: str, code: str) -> bool:
    """
    发送验证码
    TODO: 实现实际的短信发送逻辑
    """
    # 这里应该调用实际的短信服务
    # 为了开发方便，暂时直接返回成功
    print(f"Sending verification code {code} to {phone}")
    return True 