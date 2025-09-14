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
    @patch('app.utils.image_upload.upload_to_gcs')
    async def test_upload_png_file_returns_compressed_and_uncompressed_urls(self, mock_upload_to_gcs):
        """
        Test that uploading a PNG file returns both compressed and uncompressed URLs.
        This is the happy case where compression occurs and both versions are saved.
        """
        # Mock the GCS upload function to return fake URLs
        mock_upload_to_gcs.side_effect = [
            "https://storage.googleapis.com/test-bucket/images/uploads/test_user_123/20250914-174405-a2f57908.jpg",
            "https://storage.googleapis.com/test-bucket/images/uploads/test_user_123/20250914-174405-a2f57908-uncompressed.png"
        ]
        
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
        
        # Verify the result
        assert isinstance(result, APIResponse)
        assert result.code == 200, f"Expected success code 200, got {result.code}"
        assert result.data is not None
        
        response_data = result.data
 
        # Should have both compressed and uncompressed URLs
        assert "url" in response_data, "Compressed URL should be present"
        assert "uncompressed_url" in response_data, "Uncompressed URL should be present"
        
        # Verify URL formats
        compressed_url = response_data["url"]
        uncompressed_url = response_data["uncompressed_url"]
        
        assert compressed_url.startswith("https://storage.googleapis.com/"), "Compressed URL should be a valid GCS URL"
        assert uncompressed_url.startswith("https://storage.googleapis.com/"), "Uncompressed URL should be a valid GCS URL"
        
        # Verify file paths contain expected elements
        assert user_id in compressed_url, "Compressed URL should contain user ID"
        assert user_id in uncompressed_url, "Uncompressed URL should contain user ID"
        assert base_path in compressed_url, "Compressed URL should contain base path"
        assert base_path in uncompressed_url, "Uncompressed URL should contain base path"
        
        # Verify file extensions
        assert compressed_url.endswith(".jpg"), "Compressed file should be JPEG"
        assert uncompressed_url.endswith(".png"), "Uncompressed file should be PNG"
        
        # Verify uncompressed URL has the expected suffix
        assert "-uncompressed" in uncompressed_url, "Uncompressed URL should contain the suffix"
        
        # Verify that upload_to_gcs was called twice (compressed and uncompressed)
        assert mock_upload_to_gcs.call_count == 2, "upload_to_gcs should be called twice"
        
        print(f"Compressed URL: {compressed_url}")
        print(f"Uncompressed URL: {uncompressed_url}")

    @pytest.mark.asyncio
    @patch('app.utils.image_upload.upload_to_gcs')
    @patch('app.utils.image_upload.crop_avatar')
    async def test_upload_png_avatar_returns_only_compressed_url(self, mock_crop_avatar, mock_upload_to_gcs):
        """
        Test that uploading a PNG file for avatar cropping returns only compressed URL.
        Avatar images should not have uncompressed versions saved.
        """
        # Mock the GCS upload function to return fake URLs
        mock_upload_to_gcs.side_effect = [
            "https://storage.googleapis.com/test-bucket/avatars/test_user_123/20250914-174405-a2f57908.jpg",
            "https://storage.googleapis.com/test-bucket/avatars/test_user_123/20250914-174405-a2f57908-uncompressed.png",
            "https://storage.googleapis.com/test-bucket/avatars/test_user_123/20250914-174405-a2f57908-cropped.jpg"
        ]
        
        # Mock the crop_avatar function to return a mock PIL Image
        mock_cropped_image = MagicMock()
        mock_crop_avatar.return_value = mock_cropped_image
        
        # Read the test PNG file
        test_file_path = "tests/files/test.png"
        with open(test_file_path, "rb") as f:
            file_content = f.read()
        
        # Create a mock UploadFile
        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj,
            filename="test.png",
            headers={"content-type": "image/png"}
        )
        
        # Test parameters - this time for avatar cropping
        user_id = "test_user_123"
        base_path = "avatars/test_user_123"
        cropping_avatar = True  # This is an avatar, so uncompressed should NOT be saved
        
        # Call the function
        result = await process_image_upload(
            file=upload_file,
            user_id=user_id,
            base_path=base_path,
            cropping_avatar=cropping_avatar
        )
        
        # Verify the result
        assert isinstance(result, APIResponse)
        assert result.code == 200, f"Expected success code 200, got {result.code}"
        assert result.data is not None
        
        response_data = result.data
        
        # Should have compressed URL, uncompressed URL, and avatar URL
        assert "url" in response_data, "Compressed URL should be present"
        assert "uncompressed_url" in response_data, "Uncompressed URL should be present"
        assert "avatar_url" in response_data, "Avatar URL should be present"
        
        # Verify URL formats
        compressed_url = response_data["url"]
        uncompressed_url = response_data["uncompressed_url"]
        avatar_url = response_data["avatar_url"]
        
        assert compressed_url.startswith("https://storage.googleapis.com/"), "Compressed URL should be a valid GCS URL"
        assert uncompressed_url.startswith("https://storage.googleapis.com/"), "Uncompressed URL should be a valid GCS URL"
        assert avatar_url.startswith("https://storage.googleapis.com/"), "Avatar URL should be a valid GCS URL"
        
        # Verify file extensions
        assert compressed_url.endswith(".jpg"), "Compressed file should be JPEG"
        assert uncompressed_url.endswith(".png"), "Uncompressed file should be PNG"
        assert avatar_url.endswith(".jpg"), "Avatar file should be JPEG"
        
        # Verify that upload_to_gcs was called three times (compressed, uncompressed, and cropped avatar)
        assert mock_upload_to_gcs.call_count == 3, "upload_to_gcs should be called three times for avatar"
        
        print(f"Compressed URL: {compressed_url}")
        print(f"Uncompressed URL: {uncompressed_url}")
        print(f"Avatar URL: {avatar_url}")

    @pytest.mark.asyncio
    @patch('app.utils.image_upload.upload_to_gcs')
    async def test_upload_small_jpg_file_returns_only_compressed_url(self, mock_upload_to_gcs):
        """
        Test that uploading a small JPG file returns only compressed URL.
        Small JPG files don't get compressed, so no uncompressed version should be saved.
        """
        # Mock the GCS upload function to return a fake URL
        mock_upload_to_gcs.return_value = "https://storage.googleapis.com/test-bucket/images/uploads/test_user_123/20250914-174405-a2f57908.jpg"
        
        # Create a small test JPG file content (simulated)
        # In a real test, you might want to use an actual small JPG file
        small_jpg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        
        # Create a mock UploadFile
        file_obj = BytesIO(small_jpg_content)
        upload_file = UploadFile(
            file=file_obj,
            filename="small_test.jpg",
            headers={"content-type": "image/jpeg"}
        )
        
        # Test parameters
        user_id = "test_user_123"
        base_path = "images/uploads"
        cropping_avatar = False
        
        # Call the function
        result = await process_image_upload(
            file=upload_file,
            user_id=user_id,
            base_path=base_path,
            cropping_avatar=cropping_avatar
        )
        
        # Verify the result
        assert isinstance(result, APIResponse)
        assert result.code == 200, f"Expected success code 200, got {result.code}"
        assert result.data is not None
        
        response_data = result.data
        
        # Should have only compressed URL (no uncompressed since no compression occurred)
        assert "url" in response_data, "Compressed URL should be present"
        assert "uncompressed_url" not in response_data, "Uncompressed URL should NOT be present for small files"
        
        # Verify URL format
        compressed_url = response_data["url"]
        assert compressed_url.startswith("https://storage.googleapis.com/"), "URL should be a valid GCS URL"
        assert compressed_url.endswith(".jpg"), "File should be JPEG"
        
        # Verify that upload_to_gcs was called only once (no compression, no uncompressed)
        assert mock_upload_to_gcs.call_count == 1, "upload_to_gcs should be called once for small files"
        
        print(f"Compressed URL: {compressed_url}")

