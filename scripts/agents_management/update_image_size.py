#!/usr/bin/env python3
"""
Script to check agents' avatar and background URLs against resources table
and create/update resource records with proper image metadata.
"""

import io

from loguru import logger
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.external_services.gcs import download_from_gcs
from app.models import Agent, Resource
from app.services.resource_service import create_image_resource
from app.utils.image import ImageFormat, ImageSize


def get_image_metadata(image_bytes: bytes) -> tuple[ImageSize, ImageFormat, int]:
    """
    Get image metadata from bytes

    Returns:
        tuple: (ImageSize, ImageFormat, byte_size)
    """
    pil_image = Image.open(io.BytesIO(image_bytes))
    size = ImageSize(width=pil_image.width, height=pil_image.height)

    # Determine format from PIL image
    format_map = {
        "JPEG": ImageFormat.JPEG,
        "PNG": ImageFormat.PNG,
        "WEBP": ImageFormat.WEBP,
    }
    format = format_map.get(pil_image.format, ImageFormat.JPEG)

    byte_size = len(image_bytes)

    return size, format, byte_size


_process_single_url = set()


def process_agent_urls(db: Session, agent: Agent) -> None:
    """
    Process avatar and background URLs for a single agent
    """
    logger.info(f"Processing agent {agent.id} ({agent.name})")

    # Process avatar URL
    if agent.avatar and agent.avatar not in _process_single_url:
        process_single_url(db, agent.avatar, agent.creator_id, agent.id, "avatar")
        _process_single_url.add(agent.avatar)

    # Process background URL
    if agent.background and agent.background not in _process_single_url:
        process_single_url(
            db, agent.background, agent.creator_id, agent.id, "background"
        )
        _process_single_url.add(agent.background)
    # Process background_images (JSON array)
    if agent.background_images:
        for bg_url in agent.background_images:
            if bg_url not in _process_single_url:
                process_single_url(
                    db, bg_url, agent.creator_id, agent.id, "background_image"
                )
                _process_single_url.add(bg_url)


def process_single_url(
    db: Session, url: str, user_id: str, agent_id: str, url_type: str
) -> None:
    """
    Process a single URL - check if it exists in resources table and create/update if needed
    """
    logger.info(f"Processing {url_type} URL: {url}")
    image_bytes = download_from_gcs(url)
    size, format, byte_size = get_image_metadata(image_bytes)

    # Check if resource already exists
    existing_resource = db.query(Resource).filter(Resource.url == url).first()

    if existing_resource:
        logger.info(f"Resource exists, verifying metadata for {url}")
        # Download image to verify metadata
        try:
            # Check if metadata matches
            metadata = existing_resource.resource_metadata or {}
            stored_size = metadata.get("size", {})
            stored_byte_size = metadata.get("byte_size", 0)

            if (
                stored_size.get("width") != size.width
                or stored_size.get("height") != size.height
                or stored_byte_size != byte_size
            ):
                logger.info(f"Updating metadata for {url}")
                # Update metadata
                metadata.update(
                    {
                        "size": size.model_dump(),
                        "content_type": f"image/{format.value}",
                        "byte_size": byte_size,
                    }
                )
                existing_resource.resource_metadata = metadata
                db.commit()
                logger.info(f"Updated metadata for {url}")
            else:
                logger.info(f"Metadata is correct for {url}")

        except Exception as e:
            logger.error(f"Error verifying metadata for {url}: {e}")
    else:
        logger.info(f"Resource not found, creating new record for {url}")
        # Download image and create resource record
        try:
            # Create resource record
            create_image_resource(
                db=db,
                user_id=user_id,
                url=url,
                size=size,
                format=format,
                byte_size=byte_size,
                compressed=False,  # We don't know if it was compressed
                cropped=False,  # We don't know if it was cropped
            )

            # Update agent_id for the resource
            resource = db.query(Resource).filter(Resource.url == url).first()
            if resource:
                resource.agent_id = agent_id
                db.commit()

            logger.info(f"Created resource record for {url}")

        except Exception as e:
            logger.error(f"Error creating resource for {url}: {e}")


def main():
    """
    Main function to process all agents
    """
    logger.info("Starting image size update script")

    db = SessionLocal()
    # Get all agents with avatar or background URLs
    agents = (
        db.query(Agent)
        .filter(
            (Agent.avatar.isnot(None))
            | (Agent.background.isnot(None))
            | (Agent.background_images.isnot(None))
        )
        .all()
    )

    try:
        logger.info(f"Found {len(agents)} agents with image URLs")
        for agent in agents:
            logger.info(f"Processing agent {agent.id} ({agent.name})")
            process_agent_urls(db, agent)
            logger.info(f"Processed agent {agent.id} ({agent.name})")
        logger.info("Image size update script completed")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
