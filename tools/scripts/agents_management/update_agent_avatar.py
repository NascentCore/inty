#!/usr/bin/env python3
"""
Script to compress PNG avatar images to JPEG format and update database records.
TODO: 添加补充开场白语音的功能
TODO：这个文件就是给 AI 角色补充元数据的工具
"""

import argparse
import io
import sys
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from loguru import logger
from PIL import Image
from sqlalchemy import and_, create_engine, select
from sqlalchemy.orm import Session

from app.utils.crop_avatar import crop_avatar
from app.utils.image import ImageFormat

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.gcs import upload_to_gcs
from app.models.agent import Agent


def download_image(url: str) -> Optional[bytes]:
    """Download image from URL"""
    logger.info(f"Downloading image from: {url}")
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        logger.error(f"Failed to download image from {url}: {response.status_code}")
        return None

    image_data = response.content
    logger.info(f"Downloaded image: {len(image_data)} bytes")
    return image_data


def _get_jpeg_bytes_from_pil_image(pil_image: Image.Image, quality: int) -> bytes:
    """Get image bytes from PIL image"""
    output_buffer = io.BytesIO()
    pil_image.save(
        output_buffer, format=ImageFormat.JPEG, quality=quality, optimize=True
    )
    return output_buffer.getvalue()


def compress_to_jpeg(image_data: bytes, quality: int = 80) -> bytes:
    """Compress PNG image to JPEG format"""
    # Open image with PIL
    image = Image.open(io.BytesIO(image_data))

    # Convert RGBA to RGB if necessary (JPEG doesn't support alpha channel)
    if image.mode in ("RGBA", "LA", "P"):
        # Create white background
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "P":
            image = image.convert("RGBA")
        background.paste(
            image, mask=image.split()[-1] if image.mode == "RGBA" else None
        )
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")

    # Save as JPEG to bytes
    jpeg_data = _get_jpeg_bytes_from_pil_image(image, quality)

    logger.debug(f"Compressed PNG to JPEG: {len(image_data)} -> {len(jpeg_data)} bytes")
    return jpeg_data


def _get_gcs_base_path(gcs_http_url: str) -> str:
    """Get GCS base path from GCS HTTP URL"""
    parsed = urlparse(gcs_http_url)
    path_parts = parsed.path.split("/")
    return "/".join(path_parts[2:-1])


def upload_jpeg_to_gcs(jpeg_data: bytes, gcs_path: str) -> Optional[str]:
    """Upload JPEG image to Google Cloud Storage"""
    bucket_name = global_config_loaded_from_config_yaml.gcs.bucket
    logger.debug(f"Uploading JPEG to GCS: {bucket_name}/{gcs_path}")

    # Upload to GCS
    public_url = upload_to_gcs(
        file_data=jpeg_data,
        content_type="image/jpeg",
        bucket_name=bucket_name,
        path=gcs_path,
    )

    logger.debug(f"Successfully uploaded JPEG to: {public_url}")
    return public_url


def update_agent_avatar(conn, agent_id: str, new_avatar_url: str):
    """Update agent's avatar URL in the database"""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE agents SET avatar = %s, updated_at = NOW() WHERE id = %s",
        (new_avatar_url, agent_id),
    )
    conn.commit()
    logger.debug(f"Updated agent {agent_id} avatar to: {new_avatar_url}")


def query_character(db: Session, agent_id: str) -> Agent:
    """Query agent table to get Agent object, aka character"""
    result = db.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


def process_one_agent_avatar_with_database(db: Session, agent_id: str):
    """Process one agent avatar with database"""
    agent = query_character(db, agent_id)
    if not agent:
        logger.error(f"Agent {agent_id} not found, skipping...")
        return
    logger.info(f"Processing character {agent.name} ({agent_id})...")
    for key, value in agent.__dict__.items():
        print(f"{key}: {value}")

    png_data = download_image(agent.avatar)
    if not png_data:
        logger.error(f"Failed to download image from {agent.avatar}, skipping...")
        return
    compressed_avatar_url = agent.avatar
    if len(png_data) >= 500 * 1024:
        jpeg_path = _get_gcs_base_path(agent.avatar) + f"/{str(uuid.uuid4())}.jpeg"
        consent = input(
            f"Compress agent {agent_id} avatar and upload to {jpeg_path}? (y/n): "
        )
        if consent.lower() == "y":
            jpeg_data = compress_to_jpeg(png_data)
            logger.info(
                f"Compressed PNG to JPEG: {len(png_data)} -> {len(jpeg_data)} bytes"
            )
            compressed_avatar_url = upload_jpeg_to_gcs(jpeg_data, jpeg_path)
    else:
        logger.info(
            f"Agent {agent_id} avatar is smaller than 500KB, skipping compression..."
        )

    avatar_pil_image = Image.open(io.BytesIO(png_data))
    avatar_pil_image.show()
    if not agent.background:
        consent = input(
            f"Agent {agent_id} has no background, update background to avatar? (y/n): "
        )
        if consent.lower() == "y":
            agent.background = compressed_avatar_url or agent.avatar
            logger.info(
                f"Agent {agent_id} background is updated to: {agent.background}"
            )

    consent = input(f"Crop agent {agent_id} avatar? (y/n): ")
    if consent.lower() == "y":
        crop_avatar_result = crop_avatar(png_data)
        pil_avatr = crop_avatar_result.image
        pil_avatr.show()
        print(crop_avatar_result.size)

        jpeg_data = _get_jpeg_bytes_from_pil_image(pil_avatr, 80)
        gcs_base_path = _get_gcs_base_path(agent.avatar)
        new_avatar_url = upload_jpeg_to_gcs(
            jpeg_data, f"{gcs_base_path}/{str(uuid.uuid4())}.jpeg"
        )

        consent = input(f"Update agent {agent_id} avatar? (y/n): ")
        if consent.lower() == "y":
            agent.avatar = new_avatar_url

    if agent.background_images is None:
        agent.background_images = [agent.background]
    elif agent.background not in agent.background_images:
        agent.background_images.append(agent.background)

    if not db.is_modified(agent):
        logger.info(f"Agent {agent_id} is not modified, skipping commit")
        return

    for key, value in agent.__dict__.items():
        print(f"{key}: {value}")

    consent = input(
        f"Are you sure you want to proceed to update agent {agent_id} avatar? (y/n): "
    )
    if consent.lower() != "y":
        logger.info("User did not confirm, exiting...")
        return
    logger.info(f"Committing agent {agent_id} to database")
    db.commit()


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Compress PNG avatar images to JPEG format and update database",
    )
    parser.add_argument(
        "--pg-url",
        default=global_config_loaded_from_config_yaml.database.url,
        type=str,
        help="PostgreSQL URL",
    )
    parser.add_argument(
        "--image-path",
        type=Path,
        help="Path to the image to crop",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=80,
        help="JPEG compression quality (1-100)",
    )

    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    logger.info("Starting avatar compression process")
    logger.info(f"Database URL: {args.pg_url}")
    logger.info(f"JPEG quality: {args.quality}")

    # Ask for user confirmation to proceed
    user_input = input(f"Are you sure you want to proceed with {args.pg_url}? (y/n): ")
    if user_input.lower() != "y":
        logger.info("User did not confirm, exiting...")
        sys.exit(0)

    if args.image_path:
        img_data = open(args.image_path, "rb").read()
        jpeg_data = compress_to_jpeg(img_data, args.quality)
        img = Image.open(io.BytesIO(jpeg_data))
        img.show()
        img.save(f"compressed-{args.image_path.name}")
        logger.info(
            f"Compressed image saved to: {f'compressed-{args.image_path.name}'}"
            f"Original image size: {args.image_path.stat().st_size} bytes"
            f"Compressed image size: {len(jpeg_data)} bytes"
        )
        return
    else:
        engine = create_engine(global_config_loaded_from_config_yaml.database.url)
        db = Session(engine)

        agent_ids = (
            db.execute(
                select(Agent.id).where(
                    and_(Agent.avatar.isnot(None), Agent.deleted_at.is_(None))
                )
            )
            .scalars()
            .all()
        )
        for agent_id in agent_ids:
            process_one_agent_avatar_with_database(db, agent_id)
        db.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    main()
