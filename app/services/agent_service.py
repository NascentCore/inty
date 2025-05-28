from typing import List, Optional
from sqlalchemy.orm import Session

from app import models, schemas

def get_agent(db: Session, agent_id: str) -> Optional[models.Agent]:
    """
    通过ID获取AI角色
    """
    return db.query(models.Agent).filter(models.Agent.id == agent_id).first()

def get_agents(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Agent]:
    """
    获取AI角色列表
    """
    return db.query(models.Agent).offset(skip).limit(limit).all()

def create_agent(
    db: Session, agent_in: schemas.AgentCreate, user_id: str
) -> models.Agent:
    """
    创建新的AI角色
    """
    db_agent = models.Agent(
        **agent_in.dict(),
        user_id=user_id
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

def update_agent(
    db: Session,
    *,
    db_agent: models.Agent,
    agent_in: schemas.AgentUpdate
) -> models.Agent:
    """
    更新AI角色
    """
    update_data = agent_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_agent, field, value)
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

def delete_agent(
    db: Session,
    *,
    db_agent: models.Agent
) -> models.Agent:
    """
    删除AI角色
    """
    db.delete(db_agent)
    db.commit()
    return db_agent 