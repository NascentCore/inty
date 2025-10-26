import os

import pytest
from loguru import logger
# 可选依赖项：如果Python SDK不可用，则跳过测试
inty_module = pytest.importorskip("inty")
Inty = getattr(inty_module, "Inty")

from app.external_services.gcs import download_from_gcs


@pytest.mark.noci
def test_upload_image():
# 最初使用虚拟api创建来宾用户。
    client = Inty(base_url="http://localhost:8000", api_key="dummy-api-key")
# 创建注册用户
    guest_response = client.api.v1.auth.create_guest(
        device_id="test-device-123",
        system_language="en",
        age_group="adult",
    )

    logger.debug(f"Guest registration response: {guest_response}")
# 提取令牌并更新客户端
    token = guest_response.data.token
    client = Inty(base_url="http://localhost:8000", api_key=token)

    test_image_path = "tests/files/test.jpg"
    logger.debug(f"Test image path: {test_image_path}")
    logger.debug(f"Pwd: {os.getcwd()}")
    logger.debug(f"files (readable) under pwd: {os.listdir(os.getcwd())}")
# 使用_​​​​_​​_KEEP__8__ 上传图片
    with open(test_image_path, "rb") as f:
        upload_response = client.api.v1.upload_image(file=f, cropping_avatar=True)

    assert upload_response.data is not None, "Upload failed: no URL returned"
    assert upload_response.data["url"].endswith(
        ".jpg"
    ), "Upload failed: URL does not end with .jpg"
    assert upload_response.data["avatar_url"].endswith(
        ".jpg"
    ), "Upload failed: avatar URL does not end with .jpg"

    image_bytes = download_from_gcs(upload_response.data["url"])
    with open(test_image_path, "rb") as f:
        file_bytes = f.read()
# 由于cropping_avatar=True，下载的图像将与原始图像不同
#总结验证其具有合理尺寸的有效（由于图像适当，应该更小）
    assert len(image_bytes) > 0
    assert len(file_bytes) > 0
    assert len(image_bytes) == len(
        file_bytes
    ), "Downloaded image should be the same size as original"
