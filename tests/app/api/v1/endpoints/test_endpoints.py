import os
from pathlib import Path

import pytest
from loguru import logger

from app.external_services.gcs import download_from_gcs
from tests.app.api.test_client import TestClient


@pytest.mark.noci
def test_upload_image(integration_client: TestClient):
    test_image_path = Path("tests/files/test.jpg")
    logger.debug(f"Test image path: {test_image_path}")
    logger.debug(f"Pwd: {os.getcwd()}")
    logger.debug(f"files (readable) under pwd: {os.listdir(os.getcwd())}")

    data = {"cropping_avatar": "true"}

    with test_image_path.open("rb") as file_obj:
        files = {
            "file": (
                test_image_path.name,
                file_obj,
                "image/jpeg",
            )
        }
        response = integration_client.client.post(
            f"{integration_client.base_url}/api/v1/images",
            files=files,
            data=data,
        )

    assert response.status_code == 200, response.text
    upload_response = response.json()

    assert upload_response.get("data") is not None, "Upload failed: no URL returned"
    assert upload_response["data"]["url"].endswith(
        ".jpg"
    ), "Upload failed: URL does not end with .jpg"
    assert upload_response["data"]["avatar_url"].endswith(
        ".jpg"
    ), "Upload failed: avatar URL does not end with .jpg"

    image_bytes = download_from_gcs(upload_response["data"]["url"])
    with test_image_path.open("rb") as f:
        file_bytes = f.read()

    # Since cropping_avatar=True, the downloaded image will be different from original
    # Just verify it's a valid image with reasonable size (should be smaller due to cropping)
    assert len(image_bytes) > 0
    assert len(file_bytes) > 0
    assert len(image_bytes) == len(
        file_bytes
    ), "Downloaded image should be the same size as original"
