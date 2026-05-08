from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import pytest

from app.external_services.fakes.gcs import FakeGCSClient


@pytest.fixture()
def fake_client() -> FakeGCSClient:
    return FakeGCSClient()


def test_upload_and_public_url_and_download(fake_client: FakeGCSClient):
    bucket = fake_client.bucket("inty-test")
    blob = bucket.blob("folder/a.txt")

    payload = b"hello world"
    blob.upload_from_string(payload, content_type="text/plain")

    assert blob.exists() is True
    expected_uri = (fake_client.base_dir / "inty-test" / "folder" / "a.txt").resolve().as_uri()
    assert blob.public_url == expected_uri
    assert blob.download_as_bytes() == payload


def test_delete(fake_client: FakeGCSClient):
    bucket = fake_client.bucket("inty-test")
    blob = bucket.blob("to/delete.bin")
    blob.upload_from_string(b"123")
    assert blob.exists() is True

    blob.delete()
    assert blob.exists() is False

    with pytest.raises(FileNotFoundError):
        blob.delete()


def test_rewrite_copy(fake_client: FakeGCSClient):
    bucket = fake_client.bucket("inty-test")
    src = bucket.blob("src/file.bin")
    dst = bucket.blob("dst/file.bin")

    data = os.urandom(16)
    src.upload_from_string(data)

    # copy
    dst.rewrite(src)

    assert dst.exists() is True
    assert dst.download_as_bytes() == data


def test_integration_with_app_external_services_gcs_module(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    # 将 fake client 注入到 app.external_services.gcs.gcs_client 中，验证最常用方法的兼容性
    import importlib

    # 保存原始模块以便恢复
    original_config_mod = sys.modules.get("app.core.config")

    fake = FakeGCSClient(base_dir=str(tmp_path / "fake_root"))

    # 在导入目标模块前，用最小 stub 替换 app.core.config，避免加载大量依赖
    cfg_mod = types.ModuleType("app.core.config")
    cfg_mod.global_config_loaded_from_config_yaml = types.SimpleNamespace(
        app=types.SimpleNamespace(
            debug=True, gcp_service_account_key="/non/existent.json"
        ),
        gemini_live=types.SimpleNamespace(enabled=False),
        gcs=types.SimpleNamespace(
            use_fake_gcs=True,
            fake_gcs_base_dir=str(fake.base_dir.resolve()),
        ),
    )
    sys.modules["app.core.config"] = cfg_mod

    try:
        # 懒加载目标模块，避免提前初始化
        gcs_module = importlib.import_module("app.external_services.gcs")

        monkeypatch.setattr(
            gcs_module,
            "global_config_loaded_from_config_yaml",
            cfg_mod.global_config_loaded_from_config_yaml,
            raising=True,
        )
        # 注入
        monkeypatch.setattr(gcs_module, "gcs_client", fake, raising=True)

        # 使用模块函数进行一次完整的上传->存在性检查->下载->删除
        content = b"payload"
        bucket = "inty-test"
        path = "unit/test/file.dat"

        url = gcs_module.upload_to_gcs(
            content, "application/octet-stream", bucket, path
        )
        assert url == (fake.base_dir / bucket / path).resolve().as_uri()

        assert gcs_module.check_gcs_file_exists(bucket, path) is True

        downloaded = gcs_module.download_from_gcs(url)
        assert downloaded == content

        # 复制
        copied_url = gcs_module.copy_gcs_file(url, "unit/test/file-copy.dat", bucket)
        assert copied_url == (
            fake.base_dir / bucket / "unit/test/file-copy.dat"
        ).resolve().as_uri()

        # 删除
        assert gcs_module.delete_from_gcs(bucket, path) is True
        assert gcs_module.check_gcs_file_exists(bucket, path) is False
    finally:
        # 恢复原始 config 模块
        if original_config_mod is not None:
            sys.modules["app.core.config"] = original_config_mod


def test_fake_gcs_client_cleanup():
    """测试假GCS客户端清理功能"""
    fake = FakeGCSClient()
    bucket = "test-bucket"

    # 上传多个文件
    content = b"test content"
    paths = ["test1.txt", "dir/test2.txt", "dir/subdir/test3.txt"]

    for path in paths:
        blob = fake.bucket(bucket).blob(path)
        blob.upload_from_string(content)
        assert blob.exists()

    # 验证文件和目录存在
    assert fake.base_dir.exists()
    assert (fake.base_dir / bucket).exists()

    # 清理
    fake.cleanup()

    # 验证所有文件和目录被删除
    for path in paths:
        blob = fake.bucket(bucket).blob(path)
        assert not blob.exists()

    assert not (fake.base_dir / bucket).exists()
    assert not fake.base_dir.exists()
