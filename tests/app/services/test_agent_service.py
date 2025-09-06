import io
import pytest

from PIL import Image

from google.cloud import storage

from app import models
from app.core.config import global_config_loaded_from_config_yaml
from app.services.agent_service import _crop_avatar_from_background
from app.utils.gcs import download_from_gcs, get_bucket_and_path_from_gcs_url
from app.schemas.agent import AgentUpdate, ModelConfig
from app.services.agent_service import _update_agent_in_db

from loguru import logger


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

    _update_agent_in_db(agent_update, agent_in_db)

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

    _update_agent_in_db(agent_update, agent_in_db)

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
