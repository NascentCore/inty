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

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.operators import and_

# Add the app directory to the Python path so we can import models
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.models.agent import Agent


def parse_pg_url(pg_url: str) -> str:
    """Convert PostgreSQL URL to async URL if needed."""
    if pg_url.startswith("postgresql://"):
        return pg_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return pg_url


async def get_agents_by_name(session: AsyncSession, name: str) -> list[Agent]:
    """Get all agents with the given name from the database."""
    result = await session.execute(
        select(Agent).where(
            and_(Agent.name == name, Agent.deleted_at.is_(None))
        )
    )
    agents = result.scalars().all()

    if len(agents) == 0:
        raise Exception("No rows were found")

    return agents


async def copy_agent(
    source_session: AsyncSession,
    dest_session: AsyncSession,
    source_agent: Agent,
) -> bool:
    """Copy agent data from source to destination database."""
    try:
        # Detach the source agent from its session and add to destination session
        # This is much simpler than manually copying all fields
        source_session.expunge(source_agent)
        dest_session.add(source_agent)
        await dest_session.commit()

        logger.info(
            f"Successfully copied agent '{source_agent.name}' (ID: {source_agent.id})"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to copy agent: {e}")
        await dest_session.rollback()
        return False


def parse_args():
    parser = argparse.ArgumentParser(
        description="Copy an agent from one database to another"
    )
    parser.add_argument(
        "--name", required=True, help="Name of the agent to copy"
    )
    parser.add_argument(
        "--source-pg",
        required=False,
        default="postgresql://postgres:postgres@localhost:15432/devdb",
        help="Source PostgreSQL URL",
    )
    parser.add_argument(
        "--dest-pg",
        required=False,
        default="postgresql://postgres:sxwl666!@localhost:15432/inty",
        help="Destination PostgreSQL URL",
    )
    return parser.parse_args()


async def main():
    args = parse_args()

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
        SourceSession = sessionmaker(
            bind=source_engine, class_=AsyncSession, expire_on_commit=False
        )
        DestSession = sessionmaker(
            bind=dest_engine, class_=AsyncSession, expire_on_commit=False
        )

        logger.info(f"Connected to databases")
    except Exception as e:
        logger.error(f"Failed to create database engines: {e}")
        sys.exit(1)

    try:
        async with (
            SourceSession() as source_session,
            DestSession() as dest_session,
        ):
            # Get all agents from source by name
            source_agents = await get_agents_by_name(source_session, args.name)
            logger.info(
                f"Found {len(source_agents)} agent(s) with name '{args.name}' in source database"
            )

            # Copy all agents
            success_count = 0
            for i, source_agent in enumerate(source_agents, 1):
                logger.info(
                    f"Copying agent {i}/{len(source_agents)} (ID: {source_agent.id})"
                )
                if await copy_agent(source_session, dest_session, source_agent):
                    success_count += 1
                    logger.info(
                        f"Successfully copied agent {i}/{len(source_agents)}"
                    )
                else:
                    logger.error(
                        f"Failed to copy agent {i}/{len(source_agents)}"
                    )

            if success_count == len(source_agents):
                logger.info(
                    f"All {success_count} agent(s) copied successfully!"
                )
            else:
                logger.error(
                    f"Only {success_count}/{len(source_agents)} agent(s) copied successfully!"
                )
                sys.exit(1)
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        sys.exit(1)
    finally:
        await source_engine.dispose()
        await dest_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
