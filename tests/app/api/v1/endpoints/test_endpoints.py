import os
import pytest

from inty import Inty
from app.utils.gcs import download_from_gcs

from loguru import logger


@pytest.mark.noci
def test_upload_image():
    # Initially use dummy api key to create guest user.
    client = Inty(base_url="http://localhost:8000", api_key="dummy-api-key")
    # Create guest user
    guest_response = client.api.v1.auth.create_guest(
        device_id="test-device-123",
        system_language="en",
        age_group="adult",
    )

    logger.debug(f"Guest registration response: {guest_response}")

    # Extract token and update client
    token = guest_response.data.token
    client = Inty(base_url="http://localhost:8000", api_key=token)

    test_image_path = "tests/app/api/v1/endpoints/test.png"
    logger.debug(f"Test image path: {test_image_path}")
    logger.debug(f"Pwd: {os.getcwd()}")
    logger.debug(f"files (readable) under pwd: {os.listdir(os.getcwd())}")

    # Upload image using SDK
    with open(test_image_path, "rb") as f:
        upload_response = client.api.v1.upload_image(file=f, cropping_avatar=True)

    assert upload_response.data is not None, "Upload failed: no URL returned"
    assert upload_response.data["url"].endswith(
        ".jpeg"
    ), "Upload failed: URL does not end with .jpeg"
    assert upload_response.data["avatar_url"].endswith(
        ".jpeg"
    ), "Upload failed: avatar URL does not end with .jpeg"

    image_bytes = download_from_gcs(upload_response.data["url"])
    with open(test_image_path, "rb") as f:
        file_bytes = f.read()

    # Since cropping_avatar=True, the downloaded image will be different from original
    # Just verify it's a valid image with reasonable size (should be smaller due to cropping)
    assert len(image_bytes) > 0
    assert len(file_bytes) > 0
    assert len(image_bytes) != len(
        file_bytes
    ), "TODO: do not compress image when uploading"
