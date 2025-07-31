import re
from urllib.parse import urlparse

from google.cloud import storage

from app.core.config import settings  # 假设你的配置是settings对象


def upload_to_gcs(file_data, content_type, bucket_name, path):
    client = storage.Client.from_service_account_json(settings.gcs.credentials)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    blob.upload_from_string(file_data, content_type=content_type)
    return blob.public_url


# 新增删除方法
def delete_from_gcs(bucket_name, path):
    """删除GCS文件，如果文件不存在则忽略"""
    try:
        client = storage.Client.from_service_account_json(settings.gcs.credentials)
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


def copy_gcs_file(source_url: str, destination_path: str, bucket_name: str) -> str:
    """
    复制GCS文件到新位置

    Args:
        source_url: 源文件的完整URL
        destination_path: 目标路径（不包含bucket名）
        bucket_name: 目标bucket名

    Returns:
        新文件的公共URL
    """
    client = storage.Client.from_service_account_json(settings.gcs.credentials)

    # 解析源文件路径
    source_path = get_path_from_gcs_url(source_url)
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


def get_path_from_gcs_url(url: str) -> str:
    """从GCS URL中提取文件路径"""
    if not url:
        return ""

    # 处理两种URL格式：
    # 1. https://storage.googleapis.com/bucket/path
    # 2. gs://bucket/path
    if url.startswith("gs://"):
        # gs://bucket/path 格式
        path = url[5:]  # 去掉 "gs://"
        if "/" in path:
            bucket_and_path = path.split("/", 1)
            if len(bucket_and_path) == 2:
                return bucket_and_path[1]
    else:
        # https://storage.googleapis.com/bucket/path 格式
        parts = url.split(".com/")
        if len(parts) >= 2:
            path = parts[1]
            # 去掉bucket名前缀
            bucket = settings.gcs.bucket
            if path.startswith(bucket + "/"):
                path = path[len(bucket) + 1 :]
                return path

    return ""


def is_valid_gcs_url(url: str) -> bool:
    """验证是否为有效的GCS URL"""
    if not url:
        return False

    # 检查是否为GCS URL格式
    gcs_patterns = [
        r"^https://storage\.googleapis\.com/[^/]+/.+",
        r"^gs://[^/]+/.+",
    ]

    for pattern in gcs_patterns:
        if re.match(pattern, url):
            return True

    return False


def is_temp_gcs_path(url: str, user_id: str) -> bool:
    """检查是否为用户的临时GCS路径"""
    if not url:
        return False

    path = get_path_from_gcs_url(url)
    if not path:
        return False

    # 检查是否为临时路径格式：backgrounds/tmp/{user_id}/... 或 avatars/tmp/{user_id}/...
    temp_patterns = [
        f"backgrounds/tmp/{user_id}/",
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
        client = storage.Client.from_service_account_json(settings.gcs.credentials)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(path)
        return blob.exists()
    except Exception:
        return False


def is_user_gcs_file(url: str, bucket_name: str) -> bool:
    """检查URL是否是用户GCS bucket中的有效文件"""
    if not is_valid_gcs_url(url):
        return False

    path = get_path_from_gcs_url(url)
    if not path:
        return False

    return check_gcs_file_exists(bucket_name, path)
