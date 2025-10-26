from __future__ import annotations

import os
from pathlib import Path
import sys
import types

import pytest

from tests.fakes.gcs import FakeGCSClient


@pytest.fixture()
def tmp_fake_root(tmp_path: Path) -> Path:
    return tmp_path / "fake_gcs_root"


@pytest.fixture()
def fake_client(tmp_fake_root: Path) -> FakeGCSClient:
    return FakeGCSClient(base_dir=tmp_fake_root)


def test_upload_and_public_url_and_download(fake_client: FakeGCSClient):
    bucket = fake_client.bucket("inty-test")
    blob = bucket.blob("folder/a.txt")

    payload = b"hello world"
    blob.upload_from_string(payload, content_type="text/plain")

    assert blob.exists() is True
    assert blob.public_url == "https://storage.googleapis.com/inty-test/folder/a.txt"
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
    monkeypatch: pytest.MonkeyPatch, tmp_fake_root: Path
):
    # 将 fake client 注入到 app.external_services.gcs.gcs_client 中，验证最常用方法的兼容性
    import importlib

    # 在导入目标模块前，用最小 stub 替换 app.core.config，避免加载大量依赖
    cfg_mod = types.ModuleType("app.core.config")
    cfg_mod.global_config_loaded_from_config_yaml = types.SimpleNamespace(
        app=types.SimpleNamespace(debug=True, gcp_service_account_key="/non/existent.json")
    )
    sys.modules["app.core.config"] = cfg_mod

    fake = FakeGCSClient(base_dir=tmp_fake_root)

    # 懒加载目标模块，避免提前初始化
    gcs_module = importlib.import_module("app.external_services.gcs")

    # 注入
    monkeypatch.setattr(gcs_module, "gcs_client", fake, raising=True)

    # 使用模块函数进行一次完整的上传->存在性检查->下载->删除
    content = b"payload"
    bucket = "inty-test"
    path = "unit/test/file.dat"

    url = gcs_module.upload_to_gcs(content, "application/octet-stream", bucket, path)
    assert url == f"https://storage.googleapis.com/{bucket}/{path}"

    assert gcs_module.check_gcs_file_exists(bucket, path) is True

    downloaded = gcs_module.download_from_gcs(url)
    assert downloaded == content

    # 复制
    copied_url = gcs_module.copy_gcs_file(url, "unit/test/file-copy.dat", bucket)
    assert copied_url == f"https://storage.googleapis.com/{bucket}/unit/test/file-copy.dat"

    # 删除
    assert gcs_module.delete_from_gcs(bucket, path) is True
    assert gcs_module.check_gcs_file_exists(bucket, path) is False
