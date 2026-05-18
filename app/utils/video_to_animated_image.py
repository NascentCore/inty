"""
视频转动图工具：将视频转换为 AVIF、GIF 或 WebP 格式的动图
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.gcs import download_from_gcs, upload_to_gcs


def convert_video_to_animated_image(
    video_url: str,
    output_format: str = "avif",
    duration: int = 4,
    fps: Optional[int] = None,
    max_width: Optional[int] = None,
) -> tuple[bytes, str]:
    """
    将视频转换为动图（AVIF、GIF 或 WebP）

    Args:
        video_url: 视频 URL（GCS URL 或 HTTP URL）
        output_format: 输出格式，avif、gif 或 webp
        duration: 视频时长（秒）
        fps: 帧率（可选，默认使用配置值，webp 格式固定为 12）
        max_width: 最大宽度（可选，默认使用配置值，webp 格式固定为 360）

    Returns:
        tuple: (动图文件的字节数据, 实际使用的格式)
        如果请求 AVIF 但 FFmpeg 不支持，会自动回退到 GIF
    """
    config = global_config_loaded_from_config_yaml.agent

    # WebP 格式使用固定参数
    if output_format == "webp":
        fps = 12
        max_width = 360
    else:
        if fps is None:
            fps = getattr(config, "animated_image_fps", 15)

        if max_width is None:
            max_width = getattr(config, "animated_image_max_width", 720)

    # 下载视频到临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
        video_path = temp_video.name

        try:
            # 下载视频
            if (
                video_url.startswith("gs://")
                or "storage.googleapis.com" in video_url
            ):
                video_data = download_from_gcs(video_url)
                temp_video.write(video_data)
            else:
                # 对于 HTTP URL，使用 requests 下载
                import requests

                response = requests.get(video_url, timeout=60)
                response.raise_for_status()
                temp_video.write(response.content)

            temp_video.flush()

            # 使用 ffmpeg 转换为动图
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{output_format}"
            ) as temp_output:
                output_path = temp_output.name

                try:
                    if output_format == "webp":
                        # 转换为 WebP 动图
                        # 使用 filter_complex 确保首尾帧一致，实现无缝循环
                        # 先处理视频，然后复制第一帧并转换为视频流，最后连接
                        filter_complex = (
                            f"[0:v]fps={fps},scale={max_width}:-1:flags=lanczos[main];"
                            f"[main]split[stream1][stream2];"
                            f"[stream2]select='eq(n,0)',loop=1:1:0[first];"
                            f"[stream1][first]concat=n=2:v=1:a=0[out]"
                        )
                        cmd = [
                            "ffmpeg",
                            "-i",
                            video_path,
                            "-filter_complex",
                            filter_complex,
                            "-map",
                            "[out]",
                            "-c:v",
                            "libwebp",
                            "-q:v",
                            "60",
                            "-compression_level",
                            "6",
                            "-lossless",
                            "0",
                            "-preset",
                            "default",
                            "-loop",
                            "0",
                            "-t",
                            str(duration),
                            output_path,
                            "-y",  # 覆盖输出文件
                        ]
                    elif output_format == "avif":
                        # 转换为 AVIF 动图
                        # 需要 ffmpeg 支持 libavif 编码器
                        # 先检查是否支持 libavif
                        check_cmd = ["ffmpeg", "-encoders"]
                        check_result = subprocess.run(
                            check_cmd,
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )
                        if "libavif" not in check_result.stdout:
                            logger.warning(
                                "FFmpeg 不支持 libavif 编码器，将回退到 GIF 格式"
                            )
                            output_format = "gif"
                            # 更新输出文件路径
                            output_path = output_path.replace(".avif", ".gif")

                        if output_format == "avif":
                            cmd = [
                                "ffmpeg",
                                "-i",
                                video_path,
                                "-vf",
                                f"fps={fps},scale={max_width}:-1:flags=lanczos",
                                "-t",
                                str(duration),
                                "-c:v",
                                "libavif",
                                "-pix_fmt",
                                "yuva420p",
                                "-loop",
                                "0",
                                output_path,
                                "-y",  # 覆盖输出文件
                            ]
                        else:
                            # 回退到 GIF
                            cmd = [
                                "ffmpeg",
                                "-i",
                                video_path,
                                "-vf",
                                f"fps={fps},scale={max_width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                                "-t",
                                str(duration),
                                "-loop",
                                "0",
                                output_path,
                                "-y",  # 覆盖输出文件
                            ]
                    else:  # gif
                        # 转换为 GIF
                        cmd = [
                            "ffmpeg",
                            "-i",
                            video_path,
                            "-vf",
                            f"fps={fps},scale={max_width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                            "-t",
                            str(duration),
                            "-loop",
                            "0",
                            output_path,
                            "-y",  # 覆盖输出文件
                        ]

                    logger.debug(f"执行 ffmpeg 命令: {' '.join(cmd)}")

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300,  # 5分钟超时
                    )

                    if result.returncode != 0:
                        logger.error(f"ffmpeg 转换失败: {result.stderr}")
                        raise RuntimeError(
                            f"Video conversion failed: {result.stderr}"
                        )

                    # 读取生成的动图文件
                    with open(output_path, "rb") as f:
                        animated_data = f.read()

                    logger.info(
                        f"视频转换成功: {len(animated_data)} bytes, 格式: {output_format}"
                    )

                    return animated_data, output_format

                except FileNotFoundError:
                    logger.error("ffmpeg 未找到，请确保已安装 ffmpeg")
                    raise RuntimeError(
                        "ffmpeg 未安装或不在 PATH 中。"
                        "请参考文档 backend/docs/FFMPEG_INSTALLATION.md 了解安装方法。"
                    )
                except subprocess.TimeoutExpired:
                    logger.error("视频转换超时")
                    raise RuntimeError("Video conversion timed out")
                finally:
                    # 清理临时输出文件
                    try:
                        Path(output_path).unlink()
                    except Exception as e:
                        logger.warning(f"清理临时文件失败: {e}")

        finally:
            # 清理临时视频文件
            try:
                Path(video_path).unlink()
            except Exception as e:
                logger.warning(f"清理临时视频文件失败: {e}")


async def convert_video_to_animated_image_and_upload(
    video_url: str,
    user_id: str,
    output_format: str = "avif",
    duration: int = 4,
    base_path: str = "uploads/animated_images",
) -> str:
    """
    将视频转换为动图并上传到 GCS

    Args:
        video_url: 视频 URL
        user_id: 用户 ID
        output_format: 输出格式，avif、gif 或 webp
        duration: 视频时长（秒）
        base_path: GCS 存储基础路径

    Returns:
        上传后的动图 CDN URL
    """
    import uuid
    from datetime import datetime

    # 转换视频为动图
    animated_data, actual_format = convert_video_to_animated_image(
        video_url=video_url,
        output_format=output_format,
        duration=duration,
    )

    # 生成唯一文件名（使用实际格式）
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    file_gcs_path = (
        f"{base_path}/{user_id}/{timestamp}-{unique_id}.{actual_format}"
    )

    # 上传到 GCS
    bucket = global_config_loaded_from_config_yaml.gcs.bucket
    content_type = f"image/{actual_format}"
    gcs_url = upload_to_gcs(
        animated_data,
        content_type,
        bucket,
        file_gcs_path,
    )

    # 转换为 CDN URL
    from app.services.image_transform_service import image_transform_service

    try:
        cdn_url = image_transform_service.transform_desktop(gcs_url)
        logger.debug(f"动图上传成功，CDN URL: {cdn_url}")
        return cdn_url
    except Exception as transform_error:
        logger.warning(
            f"Failed to transform URL to CDN: {gcs_url}, error: {str(transform_error)}"
        )
        return gcs_url  # Fallback to original GCS URL
