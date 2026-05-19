"""
视频生成服务：使用 Google Veo3 API 生成视频
"""

import uuid
from datetime import datetime
from typing import Optional

from google.genai import types
from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.gcs import upload_to_gcs
from app.utils.gemini import get_genai_client


class VideoGenerationService:
    """视频生成服务 - 使用 Google Veo3 API"""

    def __init__(self):
        # 安全访问配置，处理测试环境中配置可能未初始化的情况
        config = getattr(global_config_loaded_from_config_yaml, "agent", None)
        if config is None:
            # 如果配置不存在，使用默认值
            self.veo3_model = "veo-3.0-fast-generate-preview"
        else:
            self.config = config
            self.veo3_model = getattr(
                self.config, "veo3_model", "veo-3.0-fast-generate-preview"
            )

    async def generate_video_with_veo3(
        self,
        prompt: str,
        duration: int = 4,
        output_gcs_uri_base: Optional[str] = None,
        image_uri: Optional[str] = None,
    ) -> str:
        """
        使用 Google Veo3 API 生成视频

        Args:
            prompt: 视频生成提示词
            duration: 视频时长（秒），默认4秒
            output_gcs_uri_base: GCS URI 基础路径（可选）
            image_uri: 输入图片的 URI（可选），可以是 GCS URI 或 HTTPS URL
                将作为 source 中的 image 参数使用

        Returns:
            生成的视频 GCS URL
        """
        try:
            logger.debug(
                f"开始生成视频，提示词: {prompt}, 时长: {duration}秒, 模型: {self.veo3_model}, "
                f"输入图片: {image_uri if image_uri else '无'}"
            )

            client = get_genai_client()

            # 如果没有提供 GCS URI 基础路径，生成一个
            if not output_gcs_uri_base:
                # 安全访问 GCS 配置
                gcs_config = getattr(
                    global_config_loaded_from_config_yaml, "gcs", None
                )
                bucket = (
                    getattr(gcs_config, "bucket", "inty-storage")
                    if gcs_config
                    else "inty-storage"
                )
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = uuid.uuid4().hex[:8]
                output_gcs_uri_base = (
                    f"gs://{bucket}/videos/{timestamp}_{unique_id}"
                )

            # 准备 source 参数（包含 prompt 和 image）
            source_image = None
            if image_uri:
                # 确保使用 GCS URI 格式（gs://）
                gcs_uri = image_uri
                if not gcs_uri.startswith("gs://"):
                    # 如果是 HTTPS URL，尝试转换为 GCS URI
                    if "storage.googleapis.com" in gcs_uri:
                        # 从 https://storage.googleapis.com/bucket/path 提取路径
                        path = gcs_uri.replace(
                            "https://storage.googleapis.com/", ""
                        )
                        gcs_uri = f"gs://{path}"
                    else:
                        logger.warning(
                            f"无法将 URL 转换为 GCS URI: {image_uri}，将尝试直接使用"
                        )
                        gcs_uri = image_uri

                # 从文件扩展名推断 MIME 类型
                mime_type = "image/jpeg"  # 默认值
                if "." in gcs_uri:
                    ext = gcs_uri.split(".")[-1].lower()
                    mime_type_map = {
                        "jpg": "image/jpeg",
                        "jpeg": "image/jpeg",
                        "png": "image/png",
                        "gif": "image/gif",
                        "webp": "image/webp",
                        "avif": "image/avif",
                    }
                    mime_type = mime_type_map.get(ext, "image/jpeg")

                # 创建 Image 对象用于 source，必须提供 mime_type
                source_image = types.Image(gcs_uri=gcs_uri, mime_type=mime_type)
                logger.debug(f"已准备源图片: {gcs_uri}, MIME 类型: {mime_type}")

            # 创建 GenerateVideosSource
            # 注意：prompt 和 image 参数已废弃，应使用 source 参数
            source = types.GenerateVideosSource(
                prompt=prompt,
                image=source_image,
            )

            # 配置视频生成参数
            config_kwargs = {
                "duration_seconds": duration,
                "output_gcs_uri": output_gcs_uri_base,
            }

            generate_config = types.GenerateVideosConfig(**config_kwargs)

            # 调用 generate_videos，使用 source 参数而不是废弃的 prompt 和 image
            call_kwargs = {
                "model": self.veo3_model,
                "source": source,
                "config": generate_config,
            }

            # generate_videos 返回一个异步操作，需要轮询状态
            operation = client.models.generate_videos(**call_kwargs)

            logger.debug(f"Veo3 操作已创建: {operation}")

            # 轮询操作状态直到完成
            import asyncio
            import time

            max_wait_time = 300  # 最大等待时间 5 分钟
            poll_interval = 10  # 每 10 秒轮询一次
            start_time = time.time()

            while not operation.done:
                elapsed_time = time.time() - start_time
                if elapsed_time > max_wait_time:
                    raise TimeoutError(
                        f"Video generation timed out (exceeded {max_wait_time} seconds)"
                    )

                logger.debug(
                    f"等待视频生成完成... (已等待 {elapsed_time:.0f} 秒)"
                )
                await asyncio.sleep(poll_interval)

                # 获取最新操作状态
                operation = client.operations.get(operation)

            # 检查操作是否成功
            if not operation.done:
                raise RuntimeError(
                    "Video generation operation did not complete"
                )

            # 提取生成的视频 URL
            if hasattr(operation, "response") and operation.response:
                if (
                    hasattr(operation.response, "generated_videos")
                    and operation.response.generated_videos
                ):
                    generated_video = operation.response.generated_videos[0]
                    if (
                        hasattr(generated_video, "video")
                        and generated_video.video
                    ):
                        video_uri = (
                            generated_video.video.uri
                            if hasattr(generated_video.video, "uri")
                            else None
                        )
                        if video_uri:
                            logger.info(f"视频生成成功，GCS URI: {video_uri}")
                            return video_uri

            logger.error(f"无法从操作响应中提取视频 URL: {operation}")
            raise ValueError("Unable to extract video URL from API response")

        except Exception as e:
            logger.error(f"视频生成失败: {str(e)}")
            raise


# 延迟初始化全局实例，避免在导入时访问可能未初始化的配置
_video_generation_service_instance = None


def _get_video_generation_service() -> VideoGenerationService:
    """获取视频生成服务实例（懒加载）"""
    global _video_generation_service_instance
    if _video_generation_service_instance is None:
        _video_generation_service_instance = VideoGenerationService()
    return _video_generation_service_instance


# 使用类来模拟模块级变量，实现懒加载
class _VideoGenerationServiceProxy:
    """代理类，实现懒加载的 video_generation_service"""

    def __getattr__(self, name: str):
        return getattr(_get_video_generation_service(), name)


# 创建代理实例，在首次访问时才初始化真正的服务
video_generation_service = _VideoGenerationServiceProxy()
