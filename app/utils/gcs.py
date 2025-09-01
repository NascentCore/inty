import loguru
import re

from google.cloud import storage

from app.core.config import global_config_loaded_from_config_yaml

logger = loguru.logger


GCS_PUBLIC_HTTPS_PREFIX = "https://storage.googleapis.com/"
GCS_PRIVATE_HTTPS_PREFIX = "https://storage.cloud.google.com/"
GCS_GS_PREFIX = "gs://"


GCS_HTTPS_PREFIX = "https://storage.googleapis.com/"
GCS_GS_PREFIX = "gs://"


def upload_to_gcs(file_data, content_type, bucket_name, path):
    logger.info(f"=== 开始GCS上传 ===")
    logger.debug(f"文件大小: {len(file_data)} bytes")
    logger.debug(f"Content-Type: {content_type}")
    logger.debug(f"Bucket: {bucket_name}")
    logger.debug(f"路径: {path}")

    try:
        logger.debug(
            f"使用凭证文件: {global_config_loaded_from_config_yaml.gcs.credentials}"
        )
        client = storage.Client.from_service_account_json(
            global_config_loaded_from_config_yaml.gcs.credentials
        )
        logger.debug("GCS客户端创建成功")

        bucket = client.bucket(bucket_name)
        logger.debug(f"获取bucket: {bucket_name}")

        blob = bucket.blob(path)
        logger.debug(f"创建blob对象: {path}")

        logger.debug("开始上传文件内容")
        blob.upload_from_string(file_data, content_type=content_type)
        logger.debug("文件上传完成")

        public_url = blob.public_url
        logger.debug(f"获取公共URL: {public_url}")

        logger.info("=== GCS上传成功 ===")
        return public_url

    except Exception as e:
        logger.error(f"GCS上传失败: {str(e)}")
        logger.error(f"错误类型: {type(e).__name__}")
        import traceback

        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise


# 新增删除方法
def delete_from_gcs(bucket_name, path):
    """删除GCS文件，如果文件不存在则忽略"""
    try:
        client = storage.Client.from_service_account_json(
            global_config_loaded_from_config_yaml.gcs.credentials
        )
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
    client = storage.Client.from_service_account_json(
        global_config_loaded_from_config_yaml.gcs.credentials
    )

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


def get_bucket_and_path_from_gcs_url(url: str) -> str:
    """从GCS URL中提取文件路径"""
    assert (
        url.startswith(GCS_PUBLIC_HTTPS_PREFIX)
        or url.startswith(GCS_GS_PREFIX)
        or url.startswith(GCS_PRIVATE_HTTPS_PREFIX)
    )

    # 处理两种URL格式：
    # 1. https://storage.googleapis.com/bucket/path
    # 2. gs://bucket/path
    if url.startswith(GCS_GS_PREFIX):
        url = url.removeprefix(GCS_GS_PREFIX)

    if url.startswith(GCS_PUBLIC_HTTPS_PREFIX):
        url = url.removeprefix(GCS_PUBLIC_HTTPS_PREFIX)

    if url.startswith(GCS_PRIVATE_HTTPS_PREFIX):
        url = url.removeprefix(GCS_PRIVATE_HTTPS_PREFIX)

    return url.split("/", 1)


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

    _, path = get_bucket_and_path_from_gcs_url(url)
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
        client = storage.Client.from_service_account_json(
            global_config_loaded_from_config_yaml.gcs.credentials
        )
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(path)
        return blob.exists()
    except Exception:
        return False


def download_from_gcs(url: str) -> bytes:
    """从GCS下载文件"""
    bucket_name, gcs_path = get_bucket_and_path_from_gcs_url(url)
    assert gcs_path

    client = storage.Client.from_service_account_json(
        global_config_loaded_from_config_yaml.gcs.credentials
    )
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
    assert len(parts) == 2
    return f"{parts[0]}{suffix}.{parts[1]}"
