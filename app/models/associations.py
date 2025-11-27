from sqlalchemy import Column, ForeignKey, String, Table

from app.models import Base

# 用户关注AI角色的关联表
# DEPRECATED：已废弃，没有在使用
agent_followers = Table(
    "agent_followers",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id"), primary_key=True),
    Column("agent_id", String, ForeignKey("agents.id"), primary_key=True),
)
