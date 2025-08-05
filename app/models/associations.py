import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models import Base

# 用户关注AI角色的关联表
# TODO: 这个需要修改，跟其他表格定义要一致
agent_followers = Table(
    "agent_followers",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id"), primary_key=True),
    Column("agent_id", String, ForeignKey("agents.id"), primary_key=True),
)
