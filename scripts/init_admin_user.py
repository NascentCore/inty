#!/usr/bin/env python3
"""
Script to initialize an admin user in the database.
This script creates a superuser with admin privileges.
"""
import sys
import os
from pathlib import Path

# Add the parent directory to Python path so we can import app modules
script_dir = Path(__file__).parent
parent_dir = script_dir.parent
sys.path.insert(0, str(parent_dir))

from loguru import logger
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.models.user import AuthType, Gender, User


def create_admin_user():
    """Create an admin user in the database."""
    logger.info("Starting admin user creation...")
    
    # Create database session
    db: Session = SessionLocal()
    # Check if admin user already exists
    existing_user = db.query(User).filter(
        User.id == "user-01JWZ34Y4D1C92GD86A5R6EWYJ"
    ).first()
    
    if existing_user:
        logger.warning("Admin user already exists with ID: user-01JWZ34Y4D1C92GD86A5R6EWYJ")
        return
    
    # Create new admin user
    admin_user = User(
        id="user-01JWZ34Y4D1C92GD86A5R6EWYJ",
        nickname="admin",
        email="admin@sxwl.ai",
        gender=Gender.MALE,
        age_group="18-24",
        description="An admin user",
        is_active=True,
        is_superuser=True,
        auth_type=AuthType.GOOGLE,
        readable_id="11111111"
    )
    
    # Add to database
    db.add(admin_user)
    db.commit()
    
    logger.info("Admin user created successfully!")
    logger.info(f"User ID: {admin_user.id}")
    logger.info(f"Email: {admin_user.email}")
    logger.info(f"Readable ID: {admin_user.readable_id}")

if __name__ == "__main__":
    create_admin_user()
