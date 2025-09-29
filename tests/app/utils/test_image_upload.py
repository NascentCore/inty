"""
Unit tests for image upload utility functions.
"""

import os
import random
import uuid
from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi import UploadFile
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from app.models import Base
from app.models.resource import Resource
from app.models.user import AuthType, User
from app.schemas.response import APIResponse
from app.services.user_service import generate_next_readable_id_sync
from app.utils.image_upload import ImageUploadResponse, process_image_upload


def register_user(db: Session, user_in) -> User:
    """Register user (phone number etc.)"""
    user_id = str(uuid.uuid4())
    readable_id = generate_next_readable_id_sync(db)

    user = User(
        id=user_id,
        readable_id=readable_id,
        auth_type=user_in.auth_type,
        system_language=(
            user_in.user_info.system_language if user_in.user_info else "en"
        ),
        is_active=True,
    )
    if user_in.user_info:
        user.gender = user_in.user_info.gender
        user.age_group = user_in.user_info.age_group
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestUploadImage:
    """Test cases for upload_image function."""

    @pytest.mark.asyncio
    @pytest.mark.noci
    async def test_upload_png_file_creates_resource_records_with_correct_metadata(self):
        """
        Test that uploading a PNG file creates resource records with correct metadata.
        """
        # 使用本地数据库
        DATABASE_URL = "postgresql://postgres:sxwl666!@localhost/inty"

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建测试用户，使用随机后缀来区分不同测试用例
        user_id = f"testuser-{uuid.uuid4().hex}"
        # 8 位数字 ID
        readable_id = str(random.randint(10000000, 99999999))

        # 检查用户是否已存在，如果存在则删除
        existing_user = db.query(User).filter(User.id == user_id).one_or_none()
        if not existing_user:
            # 创建新的测试用户
            test_user = User(
                id=user_id,
                readable_id=readable_id,
                auth_type=AuthType.GUEST,
                system_language="en",
                is_active=True,
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)

        # 准备测试文件
        test_file_path = "tests/files/test.png"
        with open(test_file_path, "rb") as f:
            file_content = f.read()
        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj, filename="test.png", headers={"content-type": "image/png"}
        )
        base_path = "images/uploads"

        # Mock GCS 上传函数，返回对应 user_id 的 URL，这样保证多次运行测试相互无干扰。
        mock_gcs_url = f"https://storage.googleapis.com/test-bucket/{user_id}/image.jpg"
        mock_gcs_avatar_url = (
            f"https://storage.googleapis.com/test-bucket/{user_id}/avatar.jpg"
        )
        mock_gcs_original_url = (
            f"https://storage.googleapis.com/test-bucket/{user_id}/original.png"
        )

        with patch("app.utils.image_upload.upload_to_gcs") as mock_upload:
            # 根据不同的调用返回不同的URL
            def mock_upload_side_effect(file_data, content_type, bucket_name, path):
                if "original" in path:
                    return mock_gcs_original_url
                elif "avatar" in path or "cropped" in path:
                    return mock_gcs_avatar_url
                else:
                    return mock_gcs_url

            mock_upload.side_effect = mock_upload_side_effect

            # Mock CDN 转换服务
            with patch(
                "app.services.image_transform_service.image_transform_service"
            ) as mock_transform:

                def mock_transform_side_effect(url):
                    return url  # 直接返回原URL

                mock_transform.transform_mobile.side_effect = mock_transform_side_effect

                result = await process_image_upload(
                    file=upload_file,
                    user_id=user_id,
                    db=db,
                    base_path=base_path,
                    cropping_avatar=True,
                )

        # 验证上传结果
        assert result.code == 200
        assert result.data == ImageUploadResponse(
            url=f"https://storage.googleapis.com/test-bucket/{user_id}/image.jpg",
            size={
                "width": 320,
                "height": 214,
            },
            original_url=f"https://storage.googleapis.com/test-bucket/{user_id}/original.png",
            avatar_url=f"https://storage.googleapis.com/test-bucket/{user_id}/avatar.jpg",
            avatar_size={
                "width": 214,
                "height": 214,
            },
        ), f"上传结果不正确，实际结果：{result.data.model_dump()}"

        image_resource = (
            db.query(Resource)
            .filter(
                Resource.url
                == f"https://storage.googleapis.com/test-bucket/{user_id}/image.jpg"
            )
            .one()
        )
        assert image_resource.resource_metadata == {
            "creator": user_id,
            "size": {"width": 320, "height": 214},
            "content_type": "image/jpeg",
            "byte_size": 15456,
            "compressed": True,
            "uncompressed_image_url": f"https://storage.googleapis.com/test-bucket/{user_id}/original.png",
            "cropped": False,
            "uncropped_image_url": None,
        }, f"图片资源记录不正确，实际结果：{image_resource.resource_metadata}"

        original_resource = (
            db.query(Resource)
            .filter(
                Resource.url
                == f"https://storage.googleapis.com/test-bucket/{user_id}/original.png"
            )
            .one()
        )
        assert original_resource.resource_metadata == {
            "creator": user_id,
            "size": {"width": 320, "height": 214},
            "content_type": "image/png",
            "byte_size": 119645,
            "compressed": False,
            "uncompressed_image_url": None,
            "cropped": False,
            "uncropped_image_url": None,
        }, f"原始图片资源记录不正确，实际结果：{original_resource.resource_metadata}"

        avatar_resource = (
            db.query(Resource)
            .filter(
                Resource.url
                == f"https://storage.googleapis.com/test-bucket/{user_id}/avatar.jpg"
            )
            .one()
        )
        assert avatar_resource.resource_metadata == {
            "creator": user_id,
            # 扣脸图片大小为 214x214；这个符合上面返回的信息
            "size": {"width": 214, "height": 214},
            "content_type": "image/jpeg",
            "byte_size": 11178,
            "compressed": True,
            "uncompressed_image_url": None,
            "cropped": True,
            "uncropped_image_url": f"https://storage.googleapis.com/test-bucket/{user_id}/image.jpg",
        }, f"扣脸图片资源记录不正确，实际结果：{avatar_resource.resource_metadata}"
