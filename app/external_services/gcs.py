"""Google Cloud Storage helpers used by services and tests.

This module centralizes GCS client creation, URL parsing, and common object
operations so callers can work with both real GCS and the fake test client.
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import loguru
from google.cloud import storage

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.fakes.gcs import FakeGCSClient

logger = loguru.logger


GCS_PUBLIC_HTTPS_PREFIX = "https://storage.googleapis.com/"
GCS_PRIVATE_HTTPS_PREFIX = "https://storage.cloud.google.com/"
GCS_GS_PREFIX = "gs://"


gcs_client = None


def path_from_file_uri(uri: str) -> Path:
    """Resolve a ``file://`` URI to a local :class:`pathlib.Path` (POSIX and Windows)."""
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError(f"Expected file URI, got {uri!r}")
    path = unquote(parsed.path or "")
    if (
        sys.platform == "win32"
        and path.startswith("/")
        and len(path) >= 3
        and path[2] == ":"
    ):
        path = path.lstrip("/")
    return Path(path)


def _bucket_and_path_from_fake_local_file_uri(url: str) -> tuple[str, str]:
    cfg = global_config_loaded_from_config_yaml.gcs
    if not cfg.use_fake_gcs:
        raise ValueError(
            f"file URI not supported when use_fake_gcs is false: {url}"
        )
    base = Path(cfg.fake_gcs_base_dir).resolve()
    full = path_from_file_uri(url).resolve()
    try:
        rel = full.relative_to(base)
    except ValueError as e:
        raise ValueError(
            f"file URL is not under fake_gcs_base_dir ({base}): {url}"
        ) from e
    parts = rel.parts
    if len(parts) < 2:
        raise ValueError(
            f"Invalid fake storage path (need bucket/object): {url}"
        )
    return parts[0], "/".join(parts[1:])


def get_gcs_client():
    """获取GCS客户端，根据配置选择真实或假客户端"""
    global gcs_client
    if gcs_client is None:
        if global_config_loaded_from_config_yaml.gcs.use_fake_gcs:
            fake_gcs_base_dir = (
                global_config_loaded_from_config_yaml.gcs.fake_gcs_base_dir
            )
            logger.info(
                f"使用 GCS Fake 客户端，存储目录为: {fake_gcs_base_dir}"
            )
            gcs_client = FakeGCSClient(fake_gcs_base_dir)
        else:
            gcs_client = storage.Client.from_service_account_json(
                global_config_loaded_from_config_yaml.app.gcp_service_account_key
            )
    return gcs_client


def upload_to_gcs(file_data, content_type, bucket_name, path):
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    blob.upload_from_string(file_data, content_type=content_type)
    public_url = blob.public_url
    # blob.generate_signed_url(expiration=datetime.timedelta(seconds=3600))
    # TODO：是否可以用来提升安全性？
    return public_url


async def upload_to_gcs_async(file_data, content_type, bucket_name, path):
    """Async version of upload_to_gcs; runs the blocking upload in a thread."""
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    await asyncio.to_thread(
        blob.upload_from_string, file_data, content_type=content_type
    )
    return blob.public_url


# 新增删除方法
def delete_from_gcs(bucket_name, path):
    """删除GCS文件，如果文件不存在则忽略"""
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(path)

        # 检查文件是否存在
        if blob.exists():
            blob.delete()
            return True
        else:
            # 文件不存在，忽略删除操作
            return False
    except Exception as e:
        # 如果是404错误或其他删除相关错误，记录但不抛出异常
        from google.api_core import exceptions

        if isinstance(e, exceptions.NotFound):
            return False  # 文件不存在，正常情况
        else:
            # 其他错误重新抛出
            raise e


def copy_gcs_file(
    source_url: str, destination_path: str, bucket_name: str
) -> str:
    """
    复制GCS文件到新位置

    Args:
        source_url: 源文件的完整URL
        destination_path: 目标路径（不包含bucket名）
        bucket_name: 目标bucket名

    Returns:
        新文件的公共URL
    """
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)

    _, source_path = get_bucket_and_path_from_gcs_url(source_url)
    if not source_path:
        raise ValueError(f"Invalid GCS URL: {source_url}")

    # 获取源bucket和blob
    source_bucket = client.bucket(bucket_name)
    source_blob = source_bucket.blob(source_path)

    # 检查源文件是否存在
    if not source_blob.exists():
        raise FileNotFoundError(f"Source file not found: {source_url}")

    # 获取目标bucket和blob
    destination_bucket = client.bucket(bucket_name)
    destination_blob = destination_bucket.blob(destination_path)

    # 复制文件
    destination_blob.rewrite(source_blob)

    return destination_blob.public_url


def get_bucket_and_path_from_gcs_url(url: str) -> tuple[str, str]:
    """Parse bucket name and object path from ``gs://``, ``https://storage...``, ``https://storage.cloud...``, or fake ``file://`` URLs."""
    if url.startswith("file:"):
        return _bucket_and_path_from_fake_local_file_uri(url)

    if not (
        url.startswith(GCS_PUBLIC_HTTPS_PREFIX)
        or url.startswith(GCS_GS_PREFIX)
        or url.startswith(GCS_PRIVATE_HTTPS_PREFIX)
    ):
        raise ValueError(f"Invalid GCS URL: {url}")

    if url.startswith(GCS_GS_PREFIX):
        url = url.removeprefix(GCS_GS_PREFIX)

    if url.startswith(GCS_PUBLIC_HTTPS_PREFIX):
        url = url.removeprefix(GCS_PUBLIC_HTTPS_PREFIX)

    if url.startswith(GCS_PRIVATE_HTTPS_PREFIX):
        url = url.removeprefix(GCS_PRIVATE_HTTPS_PREFIX)

    bucket_name, separator, gcs_path = url.partition("/")
    if not bucket_name or not separator or not gcs_path:
        raise ValueError(f"Invalid GCS URL: {url}")
    return bucket_name, gcs_path


def gs_uri_from_storage_reference_url(url: str) -> str | None:
    """Map ``gs://``, ``https://storage...``, or fake-mode ``file://`` to ``gs://bucket/path``."""
    u = (url or "").strip()
    if not u:
        return None
    try:
        bucket_name, gcs_path = get_bucket_and_path_from_gcs_url(u)
        return f"gs://{bucket_name}/{gcs_path}"
    except ValueError:
        return None


def is_valid_gcs_url(url: str) -> bool:
    """验证是否为有效的GCS URL"""
    if not url:
        return False

    if (
        global_config_loaded_from_config_yaml.gcs.use_fake_gcs
        and url.startswith("file:")
    ):
        try:
            base = Path(
                global_config_loaded_from_config_yaml.gcs.fake_gcs_base_dir
            ).resolve()
            path_from_file_uri(url).resolve().relative_to(base)
            return True
        except ValueError:
            return False

    # 检查是否为GCS URL格式
    gcs_patterns = [
        r"^https://storage\.googleapis\.com/[^/]+/.+",
        r"^https://storage\.cloud\.google\.com/[^/]+/.+",
        r"^gs://[^/]+/.+",
    ]

    for pattern in gcs_patterns:
        if re.match(pattern, url):
            return True

    return False


def is_temp_gcs_path(url: str, user_id: str) -> bool:
    """检查是否为用户的临时GCS路径

    注意：背景图片现在使用统一目录 backgrounds/{user_id}/，不再是临时路径
    只有 avatars/tmp/{user_id}/ 和 tmp/{user_id}/ 被认为是临时路径
    """
    if not url:
        return False

    _, path = get_bucket_and_path_from_gcs_url(url)
    if not path:
        return False

    # 检查是否为临时路径格式：avatars/tmp/{user_id}/... 或 tmp/{user_id}/...
    # 注意：backgrounds/{user_id}/ 现在是统一目录，不是临时路径
    temp_patterns = [
        f"backgrounds/tmp/{user_id}/",  # 保留以防有遗留的临时路径
        f"avatars/tmp/{user_id}/",
        f"tmp/{user_id}/",
    ]

    for pattern in temp_patterns:
        if path.startswith(pattern):
            return True

    return False


def check_gcs_file_exists(bucket_name: str, path: str) -> bool:
    """检查GCS文件是否存在"""
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(path)
        return blob.exists()
    except Exception:
        return False


def download_from_gcs(url: str) -> bytes:
    """从GCS下载文件"""
    if url.startswith("file:"):
        p = path_from_file_uri(url).resolve()
        logger.debug(f"read local file (fake GCS): {p}")
        return p.read_bytes()

    bucket_name, gcs_path = get_bucket_and_path_from_gcs_url(url)

    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)
    logger.debug(f"下载GCS文件: {bucket_name}/{gcs_path}")
    return blob.download_as_bytes()


def append_filename_suffix(gcs_path: str, suffix: str) -> str:
    """在GCS路径的文件名后添加后缀，阅读测试了解期行为，a/b.c -> a/b<suffix>.c"""
    DOT = "."
    if DOT not in gcs_path:
        return f"{gcs_path}{suffix}"
    parts = gcs_path.split(".", 1)
    return f"{parts[0]}{suffix}.{parts[1]}"
