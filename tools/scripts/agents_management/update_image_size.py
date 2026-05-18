#!/usr/bin/env python3
"""
Script to check agents' avatar and background URLs against resources table
and create/update resource records with proper image metadata.
"""

import asyncio
import io

from loguru import logger
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.db.session import AsyncSessionLocal
from app.external_services.gcs import download_from_gcs, is_valid_gcs_url
from app.models.agent import Agent
from app.models.resource import Resource
from app.services.resource_service import async_create_image_resource
from app.utils.image import ImageFormat, ImageSize


def get_image_metadata(image_bytes: bytes) -> tuple[ImageSize, int]:
    pil_image = Image.open(io.BytesIO(image_bytes))
    size = ImageSize(width=pil_image.width, height=pil_image.height)
    byte_size = len(image_bytes)
    return size, byte_size


_process_single_url = set()


async def process_agent_urls(db: AsyncSession, agent: Agent) -> None:
    """
    Process avatar and background URLs for a single agent
    """
    logger.info(f"Processing agent {agent.id} ({agent.name})")

    # Process avatar URL
    if (
        agent.avatar
        and is_valid_gcs_url(agent.avatar)
        and agent.avatar not in _process_single_url
    ):
        await process_single_url(
            db, agent.avatar, agent.creator_id, agent.id, "avatar"
        )
        _process_single_url.add(agent.avatar)

    # Process background URL
    if (
        agent.background
        and is_valid_gcs_url(agent.background)
        and agent.background not in _process_single_url
    ):
        await process_single_url(
            db, agent.background, agent.creator_id, agent.id, "background"
        )
        _process_single_url.add(agent.background)
    # Process background_images (JSON array)
    if agent.background_images:
        for bg_url in agent.background_images:
            if (
                bg_url
                and is_valid_gcs_url(bg_url)
                and bg_url not in _process_single_url
            ):
                await process_single_url(
                    db, bg_url, agent.creator_id, agent.id, "background_image"
                )
                _process_single_url.add(bg_url)


def _check_metadata(metadata: dict, size: ImageSize, byte_size: int) -> bool:
    """
    Check if metadata matches the given size and byte size
    """
    if not metadata:
        return False

    stored_size = metadata.get("size", {})
    stored_byte_size = metadata.get("byte_size", 0)

    return (
        stored_size.get("width") == size.width
        and stored_size.get("height") == size.height
        and stored_byte_size == byte_size
    )


async def process_single_url(
    db: AsyncSession, url: str, user_id: str, agent_id: str, url_type: str
) -> None:
    """
    Process a single URL - check if it exists in resources table and create/update if needed
    """
    logger.info(f"Processing {url_type} URL: {url}")

    try:
        image_bytes = download_from_gcs(url)
        size, byte_size = get_image_metadata(image_bytes)
        logger.info(f"Image metadata: {size}, {byte_size}")
    except Exception as e:
        logger.error(f"Error downloading or processing image {url}: {e}")
        return

    # Check if resource already exists
    result = await db.execute(select(Resource).filter(Resource.url == url))
    existing_resource = result.scalar_one_or_none()

    if existing_resource:
        # Resource exists, check if metadata needs updating
        metadata = existing_resource.resource_metadata or {}
        if not _check_metadata(metadata, size, byte_size):
            logger.info(f"Updating metadata for {url}")
            metadata.update(
                {
                    "size": size.model_dump(),
                    "byte_size": byte_size,
                }
            )
            existing_resource.resource_metadata = metadata
            await db.commit()
            logger.info(f"Updated metadata for {url}")
        else:
            logger.info(f"Metadata is correct for {url}")
    else:
        # Resource doesn't exist, create new one
        logger.info(f"Creating new resource record for {url}")
        try:
            # Determine format from URL extension
            format = ImageFormat.JPEG  # default
            if url.lower().endswith(".png"):
                format = ImageFormat.PNG
            elif url.lower().endswith(".webp"):
                format = ImageFormat.WEBP
            elif url.lower().endswith(".jpg") or url.lower().endswith(".jpeg"):
                format = ImageFormat.JPEG

            await async_create_image_resource(
                async_db=db,
                user_id=user_id,
                url=url,
                size=size,
                format=format,
                byte_size=byte_size,
                compressed=False,  # We don't know if it was compressed
                cropped=False,  # We don't know if it was cropped
            )

            # Update agent_id for the resource
            result = await db.execute(
                select(Resource).filter(Resource.url == url)
            )
            resource = result.scalar_one_or_none()
            if resource:
                resource.agent_id = agent_id
                await db.commit()

            logger.info(f"Created resource record for {url}")
        except Exception as e:
            logger.error(f"Error creating resource for {url}: {e}")


async def main():
    """
    Main function to process all agents
    """
    logger.info("Starting image size update script")

    async with AsyncSessionLocal() as db:
        # Get all agents with avatar or background URLs
        result = await db.execute(
            select(Agent).filter(
                (Agent.avatar.isnot(None))
                | (Agent.background.isnot(None))
                | (Agent.background_images.isnot(None))
            )
        )
        agents = result.scalars().all()

        logger.info(f"Found {len(agents)} agents with image URLs")
        for agent in agents:
            try:
                logger.info(f"Processing agent {agent.id} ({agent.name})")
                await process_agent_urls(db, agent)
                logger.info(f"Processed agent {agent.id} ({agent.name})")
            except Exception as e:
                logger.error(
                    f"Skipping, error when processing agent {agent.id} ({agent.name}): {e}"
                )
    logger.info("Image size update script completed")


if __name__ == "__main__":
    asyncio.run(main())
