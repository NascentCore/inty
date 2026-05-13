from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.models.base import Base


class VerificationCode(Base):
    """验证码模型"""

    __tablename__ = "verification_codes"

    id = Column(String, primary_key=True, index=True)
    phone = Column(String, index=True)
    code = Column(String)
    type = Column(String)  # REGISTER/LOGIN/RESET_PASSWORD
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    attempts = Column(Integer, default=0)
