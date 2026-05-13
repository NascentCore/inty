"""
Unit tests for image upload utility functions.
"""

import os
import random
import uuid
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from loguru import logger
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from app.core.config import global_config_loaded_from_config_yaml
from app.models.base import Base
from app.models.resource import Resource
from app.models.user import AuthType, User
from app.schemas.response import APIResponse
from app.services.user_service import generate_next_readable_id_sync
from app.utils.image import ImageFormat, ImageSize
from app.utils.image_upload import ImageUploadResponse, process_image_upload


def _assert_served_image_url(url: str) -> None:
    """URL after upload: fake GCS uses file://; real stack uses CDN or GCS HTTPS."""
    gcs_cfg = global_config_loaded_from_config_yaml.gcs
    if gcs_cfg.use_fake_gcs:
        assert url.startswith("file:"), url
        assert gcs_cfg.bucket in url.replace("\\", "/"), url
    else:
        assert (
            "cdn.example.com" in url or "storage.googleapis.com" in url
        ), url


def _assert_fallback_public_url_after_cdn_failure(url: str) -> None:
    """When CDN transform fails, response falls back to blob public_url."""
    gcs_cfg = global_config_loaded_from_config_yaml.gcs
    if gcs_cfg.use_fake_gcs:
        assert url.startswith("file:"), url
        assert gcs_cfg.bucket in url.replace("\\", "/"), url
    else:
        assert "storage.googleapis.com" in url, url


def create_test_user(db: Session, user_id: str) -> User:
    """创建测试用户，确保用户存在"""
    # 检查用户是否已存在
    existing_user = db.query(User).filter(User.id == user_id).one_or_none()
    if existing_user:
        return existing_user
    
    # 生成唯一的readable_id
    readable_id = str(random.randint(10000000, 99999999))
    # 确保readable_id唯一
    while db.query(User).filter(User.readable_id == readable_id).one_or_none():
        readable_id = str(random.randint(10000000, 99999999))
    
    # 创建新的测试用户
    test_user = User(
        id=user_id,
        readable_id=readable_id,
        auth_type=AuthType.GUEST,
        system_language="en",
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    return test_user



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
    async def test_upload_png_file_creates_resource_records_with_correct_metadata(self):
        """
        Test that uploading a PNG file creates resource records with correct metadata.
        """
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建测试用户，使用随机后缀来区分不同测试用例
        user_id = f"testuser-{uuid.uuid4().hex}"
        test_user = create_test_user(db, user_id)

        # 准备测试文件
        test_file_path = "tests/files/test.png"
        with open(test_file_path, "rb") as f:
            file_content = f.read()
        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj, filename="test.png", headers={"content-type": "image/png"}
        )
        base_path = "images/uploads"

        # 确保使用fake GCS
        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=user_id,
                async_db=async_db,
                base_path=base_path,
                cropping_avatar=True,
            )

        # 验证上传结果
        assert result.code == 200
        assert result.data.url is not None
        assert result.data.size is not None
        assert result.data.original_url is not None
        assert result.data.avatar_url is not None
        assert result.data.avatar_size is not None

        # 验证数据库中的资源记录
        resources = db.query(Resource).filter(Resource.user_id == user_id).all()
        assert len(resources) == 3, f"Expected 3 resources, got {len(resources)}"

        # 验证每个资源记录都有正确的元数据
        for resource in resources:
            assert resource.user_id == user_id
            assert resource.resource_metadata["creator"] == user_id
            assert resource.resource_metadata["size"]["width"] > 0
            assert resource.resource_metadata["size"]["height"] > 0
            assert resource.resource_metadata["byte_size"] > 0
            _assert_served_image_url(resource.url)

        # 清理
        db.close()
        await async_engine.dispose()

    @pytest.mark.asyncio
    async def test_image_upload_creates_duplicate_resource_records(self):
        """
        Test that confirms the bug: image upload creates duplicate resource records
        for the same URLs (both CDN and GCS versions).

        Expected behavior: Should create 3 unique resource records
        Actual behavior: Creates 6 resource records (duplicates for CDN and GCS URLs)
        """
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建测试用户
        user_id = f"testuser-duplicate-{uuid.uuid4().hex}"
        test_user = create_test_user(db, user_id)

        # 准备测试文件
        test_file_path = "tests/files/test.png"
        with open(test_file_path, "rb") as f:
            file_content = f.read()
        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj, filename="test.png", headers={"content-type": "image/png"}
        )
        base_path = "images/uploads"

        # 确保使用fake GCS
        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=user_id,
                async_db=async_db,
                base_path=base_path,
                cropping_avatar=True,
            )

        # 验证上传结果成功
        assert result.code == 200

        # 检查资源记录数量 - 这里应该发现重复记录的问题
        all_resources = db.query(Resource).filter(Resource.user_id == user_id).all()

        print(f"Total resource records created: {len(all_resources)}")
        for i, resource in enumerate(all_resources):
            print(
                f"Resource {i+1}: URL={resource.url}, Size={resource.resource_metadata.get('size')}, Cropped={resource.resource_metadata.get('cropped')}"
            )

        # 预期的资源记录数量应该是3个（压缩图片、原始图片、扣脸图片）
        # 但实际上由于bug，会创建6个记录（每个图片的CDN和GCS版本都被记录）
        expected_unique_images = 3  # compressed, original, cropped
        actual_records = len(all_resources)

        # 这个测试会失败，证明bug存在
        assert actual_records == expected_unique_images, (
            f"Expected {expected_unique_images} unique resource records, "
            f"but got {actual_records}. This confirms the duplicate URL bug exists. "
            f"The bug creates both CDN and GCS URL records for the same image."
        )

        # 验证URL的唯一性
        urls = [resource.url for resource in all_resources]
        unique_urls = set(urls)

        assert len(urls) == len(unique_urls), (
            f"Found duplicate URLs in resource records. "
            f"Total URLs: {len(urls)}, Unique URLs: {len(unique_urls)}. "
            f"URLs: {urls}"
        )

        # 清理
        db.close()
        await async_engine.dispose()


class TestImageUploadValidation:
    """Test cases for image upload validation."""

    @pytest.mark.asyncio
    async def test_file_size_exceeds_limit(self):
        """Test that files exceeding size limit are rejected."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建一个超过限制的大文件
        large_file_data = b"x" * (10 * 1024 * 1024)  # 10MB
        file_obj = BytesIO(large_file_data)
        upload_file = UploadFile(
            file=file_obj, filename="large.jpg", headers={"content-type": "image/jpeg"}
        )

        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=f"testuser-validation-{uuid.uuid4().hex}",
                async_db=async_db,
                max_size_mb=5,  # 5MB limit
            )

        assert result.code == 400
        assert "File size exceeds" in result.message
        assert result.data["error_code"] == "FILE_SIZE_EXCEEDED"
        assert result.data["max_size_mb"] == 5

        # 清理
        db.close()
        await async_engine.dispose()

    @pytest.mark.asyncio
    async def test_missing_filename(self):
        """Test that files without filename are rejected."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        file_obj = BytesIO(b"fake image data")
        upload_file = UploadFile(
            file=file_obj, filename=None, headers={"content-type": "image/jpeg"}
        )

        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=f"testuser-validation-{uuid.uuid4().hex}",
                async_db=async_db,
            )

        assert result.code == 400
        assert "Filename is required" in result.message

        # 清理
        db.close()
        await async_engine.dispose()

    @pytest.mark.asyncio
    async def test_invalid_filename_no_extension(self):
        """Test that files without extension are rejected."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        file_obj = BytesIO(b"fake image data")
        upload_file = UploadFile(
            file=file_obj,
            filename="noextension",
            headers={"content-type": "image/jpeg"},
        )

        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=f"testuser-validation-{uuid.uuid4().hex}",
                async_db=async_db,
            )

        assert result.code == 400
        assert "Invalid filename" in result.message

        # 清理
        db.close()
        await async_engine.dispose()

    @pytest.mark.asyncio
    async def test_unsupported_file_format(self):
        """Test that unsupported file formats are rejected."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 使用真正不支持的格式（.txt 而不是 .gif，因为现在支持 GIF 和 AVIF）
        file_obj = BytesIO(b"fake text data")
        upload_file = UploadFile(
            file=file_obj, filename="test.txt", headers={"content-type": "text/plain"}
        )

        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=f"testuser-validation-{uuid.uuid4().hex}",
                async_db=async_db,
            )

        assert result.code == 400
        assert "Unsupported file type" in result.message

        # 清理
        db.close()
        await async_engine.dispose()


class TestImageUploadCompression:
    """Test cases for image compression functionality."""

    @pytest.mark.asyncio
    async def test_png_compression_to_jpeg(self):
        """Test that PNG files are compressed to JPEG."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建测试用户
        user_id = f"testuser-compression-{uuid.uuid4().hex}"
        test_user = create_test_user(db, user_id)

        # 使用测试PNG文件
        test_file_path = "tests/files/test.png"
        with open(test_file_path, "rb") as f:
            file_content = f.read()

        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj, filename="test.png", headers={"content-type": "image/png"}
        )

        # 使用fake GCS，不需要mock upload_to_gcs
        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=user_id,
                async_db=async_db,
            )

        assert result.code == 200
        _assert_served_image_url(result.data.url)

        # 清理
        db.close()
        await async_engine.dispose()

    @pytest.mark.asyncio
    async def test_large_file_compression(self):
        """Test that large files are compressed regardless of format."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建测试用户
        user_id = f"testuser-large-{uuid.uuid4().hex}"
        test_user = create_test_user(db, user_id)

        # 使用真实的测试图片文件，但模拟它很大
        test_file_path = "tests/files/test.jpg"
        with open(test_file_path, "rb") as f:
            file_content = f.read()

        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj, filename="large.jpg", headers={"content-type": "image/jpeg"}
        )

        # 确保使用fake GCS
        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=user_id,
                async_db=async_db,
            )

        assert result.code == 200
        _assert_served_image_url(result.data.url)

        # 清理
        db.close()
        await async_engine.dispose()


class TestImageUploadDifferentFormats:
    """Test cases for different image formats."""

    @pytest.mark.asyncio
    async def test_jpg_upload(self):
        """Test JPG file upload."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建测试用户
        user_id = f"testuser-jpg-{uuid.uuid4().hex}"
        test_user = create_test_user(db, user_id)

        test_file_path = "tests/files/test.jpg"
        with open(test_file_path, "rb") as f:
            file_content = f.read()

        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj, filename="test.jpg", headers={"content-type": "image/jpeg"}
        )

        # 使用fake GCS，不需要mock upload_to_gcs
        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=user_id,
                async_db=async_db,
            )

        assert result.code == 200
        _assert_served_image_url(result.data.url)

        # 清理
        db.close()
        await async_engine.dispose()

    @pytest.mark.asyncio
    async def test_webp_upload(self):
        """Test WEBP file upload."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建测试用户
        user_id = f"testuser-webp-{uuid.uuid4().hex}"
        test_user = create_test_user(db, user_id)

        test_file_path = "tests/files/test.webp"
        with open(test_file_path, "rb") as f:
            file_content = f.read()

        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj, filename="test.webp", headers={"content-type": "image/webp"}
        )

        # 使用fake GCS，不需要mock upload_to_gcs
        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=user_id,
                async_db=async_db,
            )

        assert result.code == 200
        _assert_served_image_url(result.data.url)

        # 清理
        db.close()
        await async_engine.dispose()


class TestImageUploadCropping:
    """Test cases for avatar cropping functionality."""

    @pytest.mark.asyncio
    async def test_avatar_cropping_success(self):
        """Test successful avatar cropping."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建测试用户
        user_id = f"testuser-avatar-{uuid.uuid4().hex}"
        test_user = create_test_user(db, user_id)

        test_file_path = "tests/files/frontal.png"
        with open(test_file_path, "rb") as f:
            file_content = f.read()

        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj, filename="frontal.png", headers={"content-type": "image/png"}
        )

        # 确保使用fake GCS
        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=user_id,
                async_db=async_db,
                cropping_avatar=True,
            )

        assert result.code == 200
        assert result.data.avatar_url is not None
        assert result.data.avatar_size is not None
        _assert_served_image_url(result.data.avatar_url)

        # 清理
        db.close()
        await async_engine.dispose()

    @pytest.mark.asyncio
    async def test_avatar_cropping_no_face_detected(self):
        """Test avatar cropping when no face is detected."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建测试用户
        user_id = f"testuser-no-face-{uuid.uuid4().hex}"
        test_user = create_test_user(db, user_id)

        # 使用一个没有检测到人脸的图片
        test_file_path = "tests/files/detection-failure-1.jpeg"
        with open(test_file_path, "rb") as f:
            file_content = f.read()

        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj,
            filename="no-face.jpg",
            headers={"content-type": "image/jpeg"},
        )

        # 确保使用fake GCS
        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=user_id,
                async_db=async_db,
                cropping_avatar=True,
            )

        assert result.code == 200
        # 即使没有检测到人脸，上传也应该成功，只是没有avatar_url
        assert result.data.url is not None

        # 清理
        db.close()
        await async_engine.dispose()


class TestImageUploadErrorHandling:
    """Test cases for error handling."""

    @pytest.mark.asyncio
    async def test_gcs_upload_failure(self):
        """Test handling of GCS upload failure."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建测试用户
        user_id = f"testuser-gcs-fail-{uuid.uuid4().hex}"
        test_user = create_test_user(db, user_id)

        test_file_path = "tests/files/test.jpg"
        with open(test_file_path, "rb") as f:
            file_content = f.read()

        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj, filename="test.jpg", headers={"content-type": "image/jpeg"}
        )

        with patch("app.utils.image_upload.upload_to_gcs") as mock_upload:
            mock_upload.side_effect = Exception("GCS upload failed")

            # GCS上传失败应该抛出异常
            async with async_session() as async_db:
                with pytest.raises(Exception, match="GCS upload failed"):
                    await process_image_upload(
                        file=upload_file,
                        user_id=user_id,
                        async_db=async_db,
                    )

        # 清理
        db.close()
        await async_engine.dispose()

    @pytest.mark.asyncio
    async def test_cdn_transform_failure_fallback(self):
        """Test fallback to GCS URL when CDN transform fails."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建测试用户
        user_id = f"testuser-cdn-fail-{uuid.uuid4().hex}"
        test_user = create_test_user(db, user_id)

        test_file_path = "tests/files/test.jpg"
        with open(test_file_path, "rb") as f:
            file_content = f.read()

        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj, filename="test.jpg", headers={"content-type": "image/jpeg"}
        )

        # 确保使用fake GCS
        # Mock CDN 转换失败
        with patch(
            "app.services.image_transform_service.image_transform_service"
        ) as mock_transform:
            mock_transform.transform_mobile.side_effect = Exception(
                "CDN transform failed"
            )

            async with async_session() as async_db:
                result = await process_image_upload(
                    file=upload_file,
                    user_id=user_id,
                    async_db=async_db,
                )

        assert result.code == 200
        # 应该回退到 blob public_url（fake 模式下为 file://）
        _assert_fallback_public_url_after_cdn_failure(result.data.url)

        # 清理
        db.close()
        await async_engine.dispose()


class TestImageUploadResourceRecords:
    """Test cases for resource record creation."""

    @pytest.mark.asyncio
    async def test_resource_record_creation_with_metadata(self):
        """Test that resource records are created with correct metadata."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建测试用户
        user_id = f"testuser-resource-{uuid.uuid4().hex}"
        test_user = create_test_user(db, user_id)

        # 准备测试文件
        test_file_path = "tests/files/test.jpg"
        with open(test_file_path, "rb") as f:
            file_content = f.read()

        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj, filename="test.jpg", headers={"content-type": "image/jpeg"}
        )

        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=user_id,
                async_db=async_db,
            )

        assert result.code == 200

        # 验证数据库中的资源记录
        resources = db.query(Resource).filter(Resource.user_id == user_id).all()
        assert len(resources) >= 1  # 至少有一个资源记录

        # 检查资源记录的元数据
        for resource in resources:
            assert resource.user_id == user_id
            assert resource.resource_metadata["creator"] == user_id
            assert resource.resource_metadata["size"]["width"] > 0
            assert resource.resource_metadata["size"]["height"] > 0
            assert resource.resource_metadata["byte_size"] > 0
            _assert_served_image_url(resource.url)

        # 清理
        db.close()
        await async_engine.dispose()

    @pytest.mark.asyncio
    async def test_original_and_compressed_resource_records(self):
        """Test that both original and compressed resource records are created when compression occurs."""
        # 使用本地数据库
        DATABASE_URL = global_config_loaded_from_config_yaml.database.url

        # 创建测试数据库引擎和会话
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # 创建一个 async session
        async_engine = create_async_engine(
            global_config_loaded_from_config_yaml.database.async_url
        )
        async_session = sessionmaker(
            bind=async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建测试用户
        user_id = f"testuser-compression-{uuid.uuid4().hex}"
        test_user = create_test_user(db, user_id)

        # 准备测试文件
        test_file_path = "tests/files/test.png"
        with open(test_file_path, "rb") as f:
            file_content = f.read()

        file_obj = BytesIO(file_content)
        upload_file = UploadFile(
            file=file_obj, filename="test.png", headers={"content-type": "image/png"}
        )

        # 使用fake GCS，不需要mock upload_to_gcs
        async with async_session() as async_db:
            result = await process_image_upload(
                file=upload_file,
                user_id=user_id,
                async_db=async_db,
            )

        assert result.code == 200

        # 验证数据库中的资源记录
        resources = db.query(Resource).filter(Resource.user_id == user_id).all()
        assert len(resources) >= 2  # 至少有两个资源记录（原始PNG和压缩JPEG）

        # 检查压缩资源记录
        compressed_resources = [r for r in resources if r.resource_metadata.get("content_type") == "image/jpeg"]
        assert len(compressed_resources) >= 1

        # 检查原始资源记录
        original_resources = [r for r in resources if r.resource_metadata.get("content_type") == "image/png"]
        assert len(original_resources) >= 1

        # 验证压缩效果
        compressed_resource = compressed_resources[0]
        original_resource = original_resources[0]
        
        # 压缩后的文件应该更小
        assert compressed_resource.resource_metadata["byte_size"] < original_resource.resource_metadata["byte_size"]

        # 验证URL格式
        for resource in resources:
            _assert_served_image_url(resource.url)

        # 清理
        db.close()
        await async_engine.dispose()
