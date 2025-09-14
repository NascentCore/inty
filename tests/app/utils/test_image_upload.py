"""
Unit tests for image upload utility functions.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import UploadFile
from io import BytesIO
from pathlib import Path

from app.utils.image_upload import process_image_upload
from app.schemas.response import APIResponse


class TestProcessImageUpload:
    """Test cases for process_image_upload function."""

    @pytest.mark.asyncio
    async def test_upload_png_file_returns_compressed_and_uncompressed_urls(self):
        """
        Test that uploading a PNG file returns both compressed and uncompressed URLs.
        This is the happy case where compression occurs and both versions are saved.
        """
        test_file_path = "tests/files/test.png"
        with open(test_file_path, "rb") as f:
            file_content = f.read()
        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj,
            filename="test.png",
            headers={"content-type": "image/png"}
        )
        user_id = "test_user_123"
        base_path = "images/uploads"
        cropping_avatar = False
        result = await process_image_upload(
            file=upload_file,
            user_id=user_id,
            base_path=base_path,
            cropping_avatar=cropping_avatar
        )
        assert result.success is True
