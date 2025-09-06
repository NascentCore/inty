from datetime import datetime
import io
import pytest

from PIL import Image

from google.cloud import storage

from app.core.config import global_config_loaded_from_config_yaml
from app.services.agent_service import (
    _crop_avatar_from_background,
    _process_agent_update_data,
)
from app.utils.gcs import download_from_gcs, get_bucket_and_path_from_gcs_url
from app.schemas.agent import ModelConfig, Agent, AgentUpdate

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


def test_process_agent_update_data():
    """测试 _process_agent_update_data 函数处理 llm_config 更新"""

    # 创建模拟的数据库对象，使用 Pydantic model
    db_agent = Agent(
        id="test-agent-id",
        readable_id="10000001",
        name="Test Agent",
        gender="FEMALE",
        settings={},
        intro="Original intro",
        created_at=datetime.now(),
    )

    # 创建更新请求
    update_request = AgentUpdate(
        name="Updated Agent",
        intro="Updated intro",
        llm_config=ModelConfig(model="gpt-4", temperature=0.7, max_tokens=2000),
    )

    # 调用函数
    _process_agent_update_data(update_request, db_agent)

    # 验证结果
    assert db_agent.name == "Updated Agent"
    assert db_agent.intro == "Updated intro"
    assert db_agent.settings["llm_config"]["model"] == "gpt-4"
    assert db_agent.settings["llm_config"]["temperature"] == 0.7
    assert db_agent.settings["llm_config"]["max_tokens"] == 2000


def test_process_agent_update_data_with_null_llm_config():
    """测试 _process_agent_update_data 函数处理 llm_config 为 null 的情况"""

    # 创建模拟的数据库对象，包含现有的 llm_config
    db_agent = Agent(
        id="test-agent-id",
        readable_id="10000001",
        name="Test Agent",
        gender="FEMALE",
        settings={
            "llm_config": {"model": "gpt-4", "temperature": 0.7, "max_tokens": 2000}
        },
        intro="Original intro",
        created_at=datetime.now(),
    )

    # 创建更新请求，llm_config 为 None
    update_request = AgentUpdate(
        name="Updated Agent",
        intro="Updated intro",
        llm_config=None,
    )

    # 调用函数
    _process_agent_update_data(update_request, db_agent)

    # 验证结果
    assert db_agent.name == "Updated Agent"
    assert db_agent.intro == "Updated intro"
    # 验证 llm_config 已被删除
    assert "llm_config" not in db_agent.settings
