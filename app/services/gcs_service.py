"""
GCS文件上传服务
专门用于处理语音文件和其他媒体文件的上传
"""

from datetime import datetime
from typing import Optional

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.gcs import (
    check_gcs_file_exists,
    delete_from_gcs,
    get_bucket_and_path_from_gcs_url,
    get_gcs_client,
    upload_to_gcs,
)


class GCSService:
    """GCS文件上传服务"""

    def __init__(self):
        self.bucket_name = global_config_loaded_from_config_yaml.gcs.bucket

    def _blob_public_url(self, object_path: str) -> str:
        client = get_gcs_client()
        return client.bucket(self.bucket_name).blob(object_path).public_url

    async def upload_voice_file(
        self, file_name: str, file_data: bytes, content_type: str = "audio/mpeg"
    ) -> Optional[str]:
        """
        上传语音文件到GCS

        Args:
            file_name: 文件名
            file_data: 文件数据
            content_type: 文件类型

        Returns:
            文件的公共URL
        """
        try:
            # 构建语音文件路径：voice/{年月}/{文件名}
            date_path = datetime.now().strftime("%Y%m")
            file_path = f"voice/{date_path}/{file_name}"

            logger.debug(
                f"GCS上传路径: {file_path}, 文件大小: {len(file_data)} bytes"
            )

            # 检查文件是否已存在（缓存机制）
            logger.debug(f"检查GCS文件是否存在: {file_path}")
            if check_gcs_file_exists(self.bucket_name, file_path):
                logger.debug(f"语音文件已存在，直接返回缓存: {file_path}")
                return self._blob_public_url(file_path)

            logger.debug("文件不存在，开始上传到GCS")
            # 上传到GCS
            public_url = upload_to_gcs(
                file_data=file_data,
                content_type=content_type,
                bucket_name=self.bucket_name,
                path=file_path,
            )

            if public_url:
                logger.info(f"语音文件上传成功: {file_path} -> {public_url}")
                return public_url
            else:
                logger.error(f"语音文件上传失败，返回空URL: {file_path}")
                return None

        except Exception as e:
            logger.error(f"语音文件上传失败: {str(e)}")
            logger.exception("GCS上传异常详细信息:")
            return None

    async def upload_live_chat_audio(
        self,
        user_id: str,
        agent_id: str,
        session_id: str,
        voice_session_id: str,
        wav_bytes: bytes,
    ) -> Optional[str]:
        """
        上传 live chat 单路 WAV 到 GCS，路径为 live_chat/{user_id}/{agent_id}/{session_id}_{voice_session_id}.wav。
        上传失败时捕获异常并返回 None，避免影响调用方流程。
        voice_session_id 应由调用方保证非空（通常为单次通话的 UUID），以保证多次通话不覆盖。
        Returns:
            成功时返回公开 URL，失败时返回 None。
        """
        try:
            path = f"live_chat/{user_id}/{agent_id}/{session_id}_{voice_session_id}.wav"
            logger.debug(
                f"GCS 上传 live chat 音频: {path}, 大小: {len(wav_bytes)} bytes"
            )
            public_url = upload_to_gcs(
                file_data=wav_bytes,
                content_type="audio/wav",
                bucket_name=self.bucket_name,
                path=path,
            )
            if public_url:
                logger.info(f"Live chat 音频上传成功: {path}")
                return public_url
            return None
        except Exception as e:  # 有意捕获所有上传异常，统一返回 None 并打日志
            logger.error(f"Live chat 音频上传失败: {str(e)}")
            return None

    async def delete_voice_file(self, file_path: str) -> bool:
        """
        删除语音文件

        Args:
            file_path: 文件路径

        Returns:
            是否删除成功
        """
        try:
            if file_path.startswith("https://") or file_path.startswith("file:"):
                _, file_path = get_bucket_and_path_from_gcs_url(file_path)

            delete_from_gcs(self.bucket_name, file_path)
            logger.info(f"语音文件删除成功: {file_path}")
            return True

        except Exception as e:
            logger.error(f"语音文件删除失败: {str(e)}")
            return False

    def check_voice_file_exists(self, file_path: str) -> bool:
        """
        检查语音文件是否存在

        Args:
            file_path: 文件路径

        Returns:
            文件是否存在
        """
        try:
            if file_path.startswith("https://") or file_path.startswith("file:"):
                _, file_path = get_bucket_and_path_from_gcs_url(file_path)

            return check_gcs_file_exists(self.bucket_name, file_path)

        except Exception as e:
            logger.error(f"检查语音文件失败: {str(e)}")
            return False

    def get_voice_file_url(self, file_path: str) -> str:
        """
        获取语音文件的公共URL

        Args:
            file_path: 文件路径

        Returns:
            公共URL
        """
        if file_path.startswith("https://") or file_path.startswith("file:"):
            return file_path

        return self._blob_public_url(file_path)
