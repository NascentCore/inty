import re
import time
import traceback

import loguru
from google.api_core import retry
from google.cloud import storage

from app.core.config import global_config_loaded_from_config_yaml

logger = loguru.logger


GCS_PUBLIC_HTTPS_PREFIX = "https://storage.googleapis.com/"
GCS_PRIVATE_HTTPS_PREFIX = "https://storage.cloud.google.com/"
GCS_GS_PREFIX = "gs://"


gcs_client = None

try:
    # 创建带有自定义传输配置的GCS客户端
    import requests
    from google.auth.transport.requests import Request

    # 创建自定义的requests会话，增加超时和重试
    session = requests.Session()
    session.timeout = 30  # 增加超时时间

    # 配置重试策略
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    gcs_client = storage.Client.from_service_account_json(
        global_config_loaded_from_config_yaml.app.gcp_service_account_key, _http=session
    )
    logger.debug("GCS客户端初始化成功")
except Exception as e:
    if global_config_loaded_from_config_yaml.app.debug:
        logger.error(f"GCS客户端初始化失败，debug 模式下忽略: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
    else:
        raise


def upload_to_gcs(file_data, content_type, bucket_name, path, max_retries=3):
    """
    上传文件到GCS，带重试机制

    Args:
        file_data: 文件数据
        content_type: 内容类型
        bucket_name: 存储桶名称
        path: 文件路径
        max_retries: 最大重试次数

    Returns:
        文件的公共URL
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            bucket = gcs_client.bucket(bucket_name)
            blob = bucket.blob(path)
            blob.upload_from_string(file_data, content_type=content_type)
            public_url = blob.public_url
            logger.debug(f"GCS上传成功 (尝试 {attempt + 1}/{max_retries + 1}): {path}")
            return public_url
        except Exception as e:
            last_exception = e
            logger.warning(
                f"GCS上传失败 (尝试 {attempt + 1}/{max_retries + 1}): {str(e)}"
            )
            logger.warning(f"错误类型: {type(e).__name__}")

            # 如果是最后一次尝试，记录详细错误信息
            if attempt == max_retries:
                logger.error(f"GCS上传最终失败，已重试 {max_retries} 次")
                logger.error(f"错误堆栈: {traceback.format_exc()}")
            else:
                # 等待一段时间后重试，使用指数退避
                wait_time = 2**attempt
                logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

    # 所有重试都失败了，抛出最后一个异常
    raise last_exception


# 新增删除方法
def delete_from_gcs(bucket_name, path):
    """删除GCS文件，如果文件不存在则忽略"""
    try:
        bucket = gcs_client.bucket(bucket_name)
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
    bucket = gcs_client.bucket(bucket_name)

    _, source_path = get_bucket_and_path_from_gcs_url(source_url)
    if not source_path:
        raise ValueError(f"Invalid GCS URL: {source_url}")

    # 获取源bucket和blob
    source_bucket = gcs_client.bucket(bucket_name)
    source_blob = source_bucket.blob(source_path)

    # 检查源文件是否存在
    if not source_blob.exists():
        raise FileNotFoundError(f"Source file not found: {source_url}")

    # 获取目标bucket和blob
    destination_bucket = gcs_client.bucket(bucket_name)
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
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(path)
        return blob.exists()
    except Exception:
        return False


def download_from_gcs(url: str) -> bytes:
    """从GCS下载文件"""
    bucket_name, gcs_path = get_bucket_and_path_from_gcs_url(url)
    assert gcs_path

    bucket = gcs_client.bucket(bucket_name)
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
