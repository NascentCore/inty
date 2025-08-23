#!/usr/bin/env python3
"""
Script to compress PNG avatar images to JPEG format and update database records.
"""

import argparse
import io
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Tuple

import psycopg2
import requests
from PIL import Image
from loguru import logger

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.core.config import global_config_loaded_from_config_yaml
from app.utils.gcs import upload_to_gcs


def get_database_connection(pg_url: str):
    """Create database connection from PostgreSQL URL"""
    conn = psycopg2.connect(pg_url)
    logger.info("Database connection established successfully")
    return conn


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


def compress_png_to_jpeg(image_data: bytes, quality: int = 80) -> bytes:
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
    output_buffer = io.BytesIO()
    image.save(output_buffer, format="JPEG", quality=quality, optimize=True)
    jpeg_data = output_buffer.getvalue()

    logger.info(f"Compressed PNG to JPEG: {len(image_data)} -> {len(jpeg_data)} bytes")
    return jpeg_data


def generate_jpeg_path(original_url: str) -> os.PathLike:
    """Generate new JPEG path and filename"""
    parsed = urlparse(original_url)
    path_parts = parsed.path.split("/")

    # Extract the directory path (everything except the filename)
    directory = "/".join(path_parts[2:-1])

    # Generate new filename with UUID
    new_filename = f"avatar-{uuid.uuid4().hex}.jpeg"

    # Construct new path
    new_path = f"{directory}/{new_filename}"

    return new_path


def upload_jpeg_to_gcs(jpeg_data: bytes, gcs_path: str) -> Optional[str]:
    """Upload JPEG image to Google Cloud Storage"""
    bucket_name = global_config_loaded_from_config_yaml.gcs.bucket
    logger.info(f"Uploading JPEG to GCS: {bucket_name}/{gcs_path}")

    # Upload to GCS
    public_url = upload_to_gcs(
        file_data=jpeg_data,
        content_type="image/jpeg",
        bucket_name=bucket_name,
        path=gcs_path,
    )

    logger.info(f"Successfully uploaded JPEG to: {public_url}")
    return public_url


def update_agent_avatar(conn, agent_id: str, new_avatar_url: str):
    """Update agent's avatar URL in the database"""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE agents SET avatar = %s, updated_at = NOW() WHERE id = %s",
        (new_avatar_url, agent_id),
    )
    conn.commit()
    logger.info(f"Updated agent {agent_id} avatar to: {new_avatar_url}")


def process_one_agent_avatar(conn, agent_id: str, avatar_url: str):
    """Process one agent avatar"""
    consent = input(
        f"Are you sure you want to proceed to update agent {agent_id} avatar? (y/n): "
    )
    if consent.lower() != "y":
        logger.info("User did not confirm, exiting...")
        return

    png_data = download_image(avatar_url)
    if not png_data:
        logger.error(f"Failed to download image from {avatar_url}, skipping...")
        return

    jpeg_data = compress_png_to_jpeg(png_data)
    if len(png_data) <= len(jpeg_data):
        logger.info(
            f"Skipping agent {agent_id} because the JPEG is larger than the PNG"
        )
        return

    gcs_path = generate_jpeg_path(avatar_url)
    logger.info(f"PNG url: {avatar_url}")
    logger.info(f"JPEG url: {gcs_path}")
    new_avatar_url = upload_jpeg_to_gcs(jpeg_data, gcs_path)
    update_agent_avatar(conn, agent_id, new_avatar_url)


def process_agent_avatars(conn):
    """Process all agent avatars that are PNG files"""
    cursor = conn.cursor()

    # Query agents with PNG avatars
    cursor.execute(
        """
        SELECT id, avatar 
        FROM agents 
        WHERE avatar IS NOT NULL 
        AND avatar != '' 
        AND avatar LIKE '%.png'
        AND deleted_at IS NULL
        """
    )

    agents = cursor.fetchall()
    logger.info(f"Found {len(agents)} agents with PNG avatars")

    if not agents:
        logger.info("No agents with PNG avatars found")
        return

    for agent_id, avatar_url in agents:
        process_one_agent_avatar(conn, agent_id, avatar_url)


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

    bucket_name = global_config_loaded_from_config_yaml.gcs.bucket
    credentials_path = global_config_loaded_from_config_yaml.gcs.credentials
    logger.info(f"GCS bucket: {bucket_name}")
    logger.info(f"GCS credentials: {credentials_path}")

    if not bucket_name or not credentials_path:
        logger.error("GCS configuration is incomplete")
        sys.exit(1)

    if not os.path.exists(credentials_path):
        logger.error(f"GCS credentials file not found: {credentials_path}")
        sys.exit(1)

    conn = get_database_connection(global_config_loaded_from_config_yaml.database.url)
    process_agent_avatars(conn)
    logger.info("Avatar compression process completed successfully")

    conn.close()
    logger.info("Database connection closed")


if __name__ == "__main__":
    main()
