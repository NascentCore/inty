import random
import string
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.verification_code import VerificationCode


def generate_code(length: int = 6) -> str:
    """生成指定长度的数字验证码"""
    return "".join(random.choices(string.digits, k=length))


def create_verification_code(db: Session, phone: str) -> VerificationCode:
    """创建验证码"""
    # 生成验证码
    code = generate_code()

    # 计算过期时间
    expires_at = datetime.utcnow() + timedelta(
        minutes=settings.verification.code_expire_minutes
    )

    # 创建验证码记录
    verification_code = VerificationCode(phone=phone, code=code, expires_at=expires_at)

    db.add(verification_code)
    db.commit()
    db.refresh(verification_code)

    return verification_code


def get_valid_verification_code(
    db: Session, phone: str, code: str
) -> Optional[VerificationCode]:
    """获取有效的验证码"""
    return (
        db.query(VerificationCode)
        .filter(
            VerificationCode.phone == phone,
            VerificationCode.code == code,
            VerificationCode.is_used == False,
            VerificationCode.expires_at > datetime.utcnow(),
        )
        .first()
    )


def mark_code_as_used(db: Session, verification_code: VerificationCode) -> None:
    """将验证码标记为已使用"""
    verification_code.is_used = True
    db.commit()
