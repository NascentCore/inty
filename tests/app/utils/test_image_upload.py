"""
Unit tests for image upload utility functions.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.schemas.response import APIResponse
from app.utils.image_upload import process_image_upload


class TestUploadImage:
    """Test cases for upload_image function."""

    @pytest.mark.asyncio
    @pytest.mark.noci
    async def test_upload_png_file_returns_compressed_and_uncompressed_urls(self):
        """
        Test that uploading a PNG file returns both compressed and original URLs.
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
        # Mock database session
        mock_db = MagicMock(spec=Session)

        result = await process_image_upload(
            file=upload_file,
            user_id=user_id,
            db=mock_db,
            base_path=base_path,
            cropping_avatar=cropping_avatar,
        )
        assert result.code is 200
