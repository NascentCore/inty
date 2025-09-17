import io
from unittest.mock import patch

import pytest
from google.cloud import storage
from loguru import logger
from PIL import Image

from app import models
from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.agent import AgentUpdate, ModelConfig
from app.services.agent_service import _crop_avatar_from_background, _update_agent_in_db
from app.utils.gcs import download_from_gcs, get_bucket_and_path_from_gcs_url


@pytest.mark.asyncio
@pytest.mark.skip(reason="Do not have access to gcs")
async def test_crop_avatar_from_background():
    bucket_name, path = get_bucket_and_path_from_gcs_url(
        "https://storage.googleapis.com/yx-test/Screenshot_20250815_213911-cropped-avatar.png")
    bucket = storage.Client.from_service_account_json(
        global_config_loaded_from_config_yaml.gcs.credentials
    ).bucket(bucket_name)
    try:
        bucket.blob(path).delete()
    except Exception:
        pass

    assert not bucket.blob(path).exists()

    cropped_avatar_url = await _crop_avatar_from_background(
        "https://storage.cloud.google.com/yx-test/Screenshot_20250815_213911.png",
    )
    assert cropped_avatar_url == "https://storage.googleapis.com/yx-test/Screenshot_20250815_213911-cropped-avatar.png"
    logger.info(f"Cropped avatar URL: {cropped_avatar_url}")
    jpe_data = download_from_gcs(cropped_avatar_url)
    image = Image.open(io.BytesIO(jpe_data))
    image.show()


def test_update_agent_in_db():
    """Test _update_agent_in_db function with llm_config update"""

    agent_in_db = models.Agent(
        name="Original Agent",
        personality="Original personality",
        settings={"existing_setting": "value"},
    )

    agent_update = AgentUpdate(
        name="Updated Agent",
        personality="New personality",
        llm_config=ModelConfig(
            model="anthropic/claude-3.5-sonnet",
            temperature=0.7,
            max_tokens=2048,
        ),
    )

    # Convert AgentUpdate to dict for the updated function signature
    update_data = agent_update.model_dump(exclude_unset=True)
    _update_agent_in_db(update_data, agent_in_db)

    # Verify agent attributes were updated
    agent_in_db_dict = {
        k: v for k, v in agent_in_db.__dict__.items() if not k.startswith("_")
    }
    assert agent_in_db_dict == {
        "name": "Updated Agent",
        "personality": "New personality",
        "settings": {
            "existing_setting": "value",
            "llm_config": {
                "max_tokens": 2048,
                "model": "anthropic/claude-3.5-sonnet",
                "temperature": 0.7,
            },
        },
    }

    agent_update = AgentUpdate(llm_config=None)

    # Convert AgentUpdate to dict for the updated function signature
    update_data = agent_update.model_dump(exclude_unset=True)
    _update_agent_in_db(update_data, agent_in_db)

    # Verify agent attributes were updated
    agent_in_db_dict = {
        k: v for k, v in agent_in_db.__dict__.items() if not k.startswith("_")
    }
    assert agent_in_db_dict == {
        "name": "Updated Agent",
        "personality": "New personality",
        "settings": {
            "existing_setting": "value",
        },
    }, "llm_config should be removed"


def test_process_agent_image_urls():
    """Test process_agent_image_urls function with valid URLs"""
    from app.services.agent_service import process_agent_image_urls

    # Test with valid URLs
    agent_data = {
        "name": "Test Agent",
        "avatar": "https://storage.googleapis.com/test-bucket/avatar.jpg",
        "background": "https://storage.googleapis.com/test-bucket/background.jpg",
        "background_images": [
            "https://storage.googleapis.com/test-bucket/photo1.jpg",
            "https://storage.googleapis.com/test-bucket/photo2.jpg",
        ],
    }

    # Mock the is_valid_gcs_url function to return True for all URLs
    with patch("app.utils.gcs.is_valid_gcs_url", return_value=True):
        result = process_agent_image_urls(agent_data)

        # Verify that all image URLs are collected in background_images
        assert result["background_images"] == [
            "https://storage.googleapis.com/test-bucket/avatar.jpg",
            "https://storage.googleapis.com/test-bucket/background.jpg",
            "https://storage.googleapis.com/test-bucket/photo1.jpg",
            "https://storage.googleapis.com/test-bucket/photo2.jpg",
        ]
        assert (
            result["avatar"] == "https://storage.googleapis.com/test-bucket/avatar.jpg"
        )
        assert (
            result["background"]
            == "https://storage.googleapis.com/test-bucket/background.jpg"
        )
