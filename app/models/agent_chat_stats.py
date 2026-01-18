"""
Agent chat statistics model.

CREATED_BY_AGENT
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models import Base


class AgentChatStats(Base):
    __tablename__ = "agent_chat_stats"

    id = Column(String, ForeignKey("agents.id"), primary_key=True)
    period = Column(String, primary_key=True)
    messages_count = Column(Integer, nullable=False)
    users_count = Column(Integer, nullable=False)

    agent = relationship("Agent")
