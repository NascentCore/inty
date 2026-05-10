"""In-memory filesystem-backed fake for google.cloud.storage used in tests and local dev.

Writes blobs under a configurable base directory and exposes ``Blob.public_url`` as a
local ``file://`` URI so callers match production layout without implying a real GCS HTTP endpoint.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional, Union


class FakeGCSClient:
    """一个用于测试的本地 GCS 客户端实现。

    行为：
    - 将上传的文件保存到本地临时/指定目录。
    - 暴露与 google.cloud.storage.Client 兼容的最小接口：bucket().blob().
    - Blob 支持：upload_from_string、download_as_bytes、exists、delete、rewrite、public_url。

    注意如果测试 base dir 不改变，则容易导致文件被反复使用，可能导致测试失败或者遗漏。
    """

    def __init__(self, base_dir: str = "/tmp/inty_fake_gcs") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def bucket(self, name: str) -> "FakeBucket":
        return FakeBucket(self, name)

    def cleanup(self) -> None:
        """清理所有存储的文件和目录"""
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)


class FakeBucket:
    def __init__(self, client: FakeGCSClient, name: str) -> None:
        self._client = client
        self.name = name

    def blob(self, path: str) -> "FakeBlob":
        return FakeBlob(self._client, self.name, path)


class FakeBlob:
    def __init__(self, client: FakeGCSClient, bucket_name: str, path: str) -> None:
        self._client = client
        self._bucket_name = bucket_name
        # 统一去掉前导斜杠，避免生成路径时出现双斜杠
        self._path = path.lstrip("/")

    # 与 google.cloud.storage.Blob 接口保持一致（属性）
    @property
    def public_url(self) -> str:
        return self._fs_path().resolve().as_uri()

    # 与 google.cloud.storage.Blob 接口保持一致（方法）
    def upload_from_string(
        self, data: Union[str, bytes], content_type: Optional[str] = None
    ) -> None:
        file_path = self._fs_path()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = data
        file_path.write_bytes(data_bytes)
        # content_type 在当前测试场景不使用，仅保持签名兼容

    def download_as_bytes(self) -> bytes:
        file_path = self._fs_path()
        return file_path.read_bytes()

    def exists(self) -> bool:
        return self._fs_path().is_file()

    def delete(self) -> None:
        file_path = self._fs_path()
        if file_path.exists():
            file_path.unlink()
        else:
            # 模拟真实 SDK 的行为：不存在时抛出错误
            raise FileNotFoundError(str(file_path))

    # google-cloud-storage 的重写复制接口（简化版）
    def rewrite(self, source_blob: "FakeBlob"):
        src_path = source_blob._fs_path()
        dst_path = self._fs_path()
        if not src_path.exists():
            raise FileNotFoundError(str(src_path))
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        dst_path.write_bytes(src_path.read_bytes())
        return None

    # 内部工具
    def _fs_path(self) -> Path:
        return self._client.base_dir / self._bucket_name / self._path
