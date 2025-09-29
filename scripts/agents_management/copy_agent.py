#!/usr/bin/env python3
"""
Copy an agent from one PostgreSQL database to another.

Usage:
    python copy_agent.py --name "Amber" --source-pg "postgresql://user:pass@host:port/db" --dest-pg "postgresql://user:pass@host:port/db"
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


def parse_pg_url(pg_url: str) -> str:
    """Convert PostgreSQL URL to async URL if needed."""
    if pg_url.startswith("postgresql://"):
        return pg_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return pg_url


async def get_agent_by_name(session: AsyncSession, name: str) -> Optional[dict]:
    """Get agent data by name from the database."""
    result = await session.execute(
        text("SELECT * FROM agents WHERE name = :name"),
        {"name": name}
    )
    row = result.fetchone()
    if not row:
        return None
    
    # Convert row to dict
    return dict(row._mapping)


async def agent_exists_in_dest(session: AsyncSession, name: str) -> bool:
    """Check if agent with given name already exists in destination database."""
    result = await session.execute(
        text("SELECT COUNT(*) FROM agents WHERE name = :name"),
        {"name": name}
    )
    count = result.scalar()
    return count > 0


async def copy_agent(source_session: AsyncSession, dest_session: AsyncSession, agent_data: dict) -> bool:
    """Copy agent data from source to destination database."""
    try:
        # Build dynamic INSERT statement
        columns = list(agent_data.keys())
        placeholders = [f":{col}" for col in columns]
        
        insert_sql = f"""
            INSERT INTO agents ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """
        
        await dest_session.execute(text(insert_sql), agent_data)
        await dest_session.commit()
        
        logger.info(f"Successfully copied agent '{agent_data['name']}' (ID: {agent_data['id']})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to copy agent: {e}")
        await dest_session.rollback()
        return False


async def main():
    parser = argparse.ArgumentParser(description="Copy an agent from one database to another")
    parser.add_argument("--name", required=True, help="Name of the agent to copy")
    parser.add_argument("--source-pg", required=True, help="Source PostgreSQL URL")
    parser.add_argument("--dest-pg", required=True, help="Destination PostgreSQL URL")
    parser.add_argument("--force", action="store_true", help="Overwrite if agent already exists in destination")
    
    args = parser.parse_args()
    
    # Parse database URLs
    try:
        source_url = parse_pg_url(args.source_pg)
        dest_url = parse_pg_url(args.dest_pg)
    except Exception as e:
        logger.error(f"Invalid database URL: {e}")
        sys.exit(1)
    
    # Create async engines
    try:
        source_engine = create_async_engine(source_url)
        dest_engine = create_async_engine(dest_url)
        
        # Create session makers
        SourceSession = sessionmaker(bind=source_engine, class_=AsyncSession, expire_on_commit=False)
        DestSession = sessionmaker(bind=dest_engine, class_=AsyncSession, expire_on_commit=False)
        
        logger.info(f"Connected to databases")
    except Exception as e:
        logger.error(f"Failed to create database engines: {e}")
        sys.exit(1)
    
    try:
        async with SourceSession() as source_session, DestSession() as dest_session:
            # Get agent from source
            agent_data = await get_agent_by_name(source_session, args.name)
            if not agent_data:
                logger.error(f"Agent '{args.name}' not found in source database")
                sys.exit(1)
            
            logger.info(f"Found agent '{args.name}' in source database (ID: {agent_data['id']})")
            
            # Check if agent already exists in destination
            if await agent_exists_in_dest(dest_session, args.name):
                if not args.force:
                    logger.error(f"Agent '{args.name}' already exists in destination database. Use --force to overwrite.")
                    sys.exit(1)
                else:
                    logger.warning(f"Agent '{args.name}' already exists in destination. Will overwrite due to --force flag.")
            
            # Copy the agent
            if await copy_agent(source_session, dest_session, agent_data):
                logger.info("Agent copy completed successfully!")
            else:
                logger.error("Agent copy failed!")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        sys.exit(1)
    finally:
        await source_engine.dispose()
        await dest_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
