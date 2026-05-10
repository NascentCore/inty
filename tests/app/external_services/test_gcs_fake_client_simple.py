"""测试假GCS客户端功能"""

from unittest.mock import MagicMock, patch

import pytest

from app.external_services.fakes.gcs import FakeGCSClient


class TestFakeGCSClientDirect:
    """直接测试假GCS客户端功能"""

    @pytest.fixture(autouse=True)
    def cleanup_fake_gcs_files(self):
        """自动清理假GCS测试文件"""
        fake_client = FakeGCSClient()
        yield
        fake_client.cleanup()

    def test_fake_gcs_client_upload(self):
        """测试假GCS客户端上传功能"""
        fake_client = FakeGCSClient()
        bucket = fake_client.bucket("test-bucket")
        blob = bucket.blob("test/file.txt")

        test_data = b"test file content"
        blob.upload_from_string(test_data, content_type="text/plain")

        # 验证文件存在
        assert blob.exists()

        # 验证下载内容
        downloaded_data = blob.download_as_bytes()
        assert downloaded_data == test_data

        # 验证公共URL（假客户端为本地 file URI）
        public_url = blob.public_url
        assert public_url.startswith("file:")
        assert "test-bucket" in public_url
        assert "test/file.txt" in public_url

    def test_fake_gcs_client_delete(self):
        """测试假GCS客户端删除功能"""
        fake_client = FakeGCSClient()
        bucket = fake_client.bucket("test-bucket")
        blob = bucket.blob("test/file.txt")

        test_data = b"test content"
        blob.upload_from_string(test_data)

        # 验证文件存在
        assert blob.exists()

        # 删除文件
        blob.delete()

        # 验证文件不存在
        assert not blob.exists()

    def test_fake_gcs_client_copy(self):
        """测试假GCS客户端复制功能"""
        fake_client = FakeGCSClient()
        bucket = fake_client.bucket("test-bucket")

        # 创建源文件
        source_blob = bucket.blob("test/source.txt")
        test_data = b"test copy content"
        source_blob.upload_from_string(test_data)

        # 创建目标blob
        dest_blob = bucket.blob("test/destination.txt")

        # 复制文件
        dest_blob.rewrite(source_blob)

        # 验证目标文件存在
        assert dest_blob.exists()

        # 验证目标文件内容
        downloaded_data = dest_blob.download_as_bytes()
        assert downloaded_data == test_data

    def test_fake_gcs_client_with_gcs_service(self):
        """测试假GCS客户端与GCS服务的集成"""
        # 由于配置文件已经启用了假GCS客户端，直接测试即可
        import app.external_services.gcs

        # 测试上传
        test_data = b"test integration content"
        result_url = app.external_services.gcs.upload_to_gcs(
            test_data, "text/plain", "test-bucket", "test/integration.txt"
        )
        
        # 验证返回的URL格式（假 GCS 为 file://）
        assert result_url.startswith("file:")
        assert "test-bucket" in result_url
        assert "test/integration.txt" in result_url
        
        # 验证文件存在
        assert app.external_services.gcs.check_gcs_file_exists("test-bucket", "test/integration.txt")
        
        # 验证下载
        downloaded_data = app.external_services.gcs.download_from_gcs(result_url)
        assert downloaded_data == test_data
