#!/usr/bin/env python3
"""
Script to initialize an admin user in the database.
This script creates a superuser with admin privileges.

Local Ops bearer (``--token-file``): JWT lifetime is at least 2 hours; an existing
token in the file is reused when it still has ≥2 hours until ``exp`` (avoids
invalidating REPL/regression clients on every ``backend/ops/start.sh --local`` restart).
"""

import random
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import app modules
script_dir = Path(__file__).parent
parent_dir = script_dir.parent
sys.path.insert(0, str(parent_dir))

import cyclopts
from loguru import logger
from sqlalchemy.orm import Session

from app.core.security import (
    LOCAL_OPS_BEARER_MIN_LIFETIME,
    create_access_token,
    existing_bearer_token_usable,
    local_ops_bearer_expires_delta,
)
from app.db.base import SessionLocal
from app.models.agent import Agent
from app.models.registry import load_model_modules
from app.models.user import AuthType, Gender, User

load_model_modules()

DEFAULT_ADMIN_USER_ID = "user-01JWZ34Y4D1C92GD86A5R6EWYJ"


def generate_readable_id() -> str:
    """Generate a random 8-digit readable_id (0-9)."""
    return "".join(str(random.randint(0, 9)) for _ in range(8))


def _write_agent_id_file(db: Session, created_user: User, agent_id_file: Path) -> None:
    agent_id = (
        db.query(Agent.id)
        .filter(Agent.creator_id == created_user.id)
        .filter(Agent.deleted_at.is_(None))
        .order_by(Agent.created_at.desc(), Agent.id.desc())
        .limit(1)
        .scalar()
    )
    if agent_id is None:
        if agent_id_file.exists():
            agent_id_file.unlink()
        logger.warning(f"No active agent found for user {created_user.id}")
        return
    agent_id_file.write_text(agent_id + "\n")
    logger.info(f"Agent ID written to {agent_id_file}")


def create_user(
    user_id: str = DEFAULT_ADMIN_USER_ID,
    is_superuser: bool = True,
    token_file: Path | None = None,
    agent_id_file: Path | None = None,
):
    """Create an admin user in the database.

    Optionally write local reference files for the bearer token and user's agent.
    """
    logger.info("Starting admin user creation...")

    # Create database session
    db: Session = SessionLocal()
    try:
        # Check if admin user already exists
        existing_user = db.query(User).filter(User.id == user_id).first()

        if existing_user:
            logger.warning(f"Admin user already exists with ID: {user_id}")
            if existing_user.is_superuser != is_superuser:
                existing_user.is_superuser = is_superuser
                db.commit()
                db.refresh(existing_user)
            created_user = existing_user
        else:
            # Create new admin user
            created_user = User(
                id=user_id,
                nickname="admin",
                email="admin@sxwl.ai",
                gender=Gender.MALE,
                age_group="18-24",
                description="An admin user",
                is_superuser=is_superuser,
                auth_type=AuthType.GOOGLE,
                readable_id=generate_readable_id(),
            )

            # Add to database
            db.add(created_user)
            db.commit()

        if token_file is not None and token_file.is_file():
            existing_token = token_file.read_text(encoding="utf-8").strip()
            if existing_token != "" and existing_bearer_token_usable(
                existing_token, created_user.id
            ):
                logger.info(
                    f"Reusing bearer token in {token_file} "
                    f"(≥{LOCAL_OPS_BEARER_MIN_LIFETIME} remaining)"
                )
                print(f"🔑 Bearer Token: {existing_token} (reused)")
                if agent_id_file is not None:
                    _write_agent_id_file(db, created_user, agent_id_file)
                return

        access_token = create_access_token(
            created_user.id, expires_delta=local_ops_bearer_expires_delta()
        )

        logger.info("Admin user created successfully!")
        logger.info(f"User ID: {created_user.id}")
        logger.info(f"Email: {created_user.email}")
        logger.info(f"Readable ID: {created_user.readable_id}")
        logger.info(f"🔑 Bearer Token: {access_token}")
        print(f"🔑 Bearer Token: {access_token}")

        if token_file is not None:
            token_file.write_text(access_token + "\n")
            logger.info(f"Token written to {token_file}")

        if agent_id_file is not None:
            _write_agent_id_file(db, created_user, agent_id_file)
    finally:
        db.close()


if __name__ == "__main__":
    cyclopts.run(create_user)
