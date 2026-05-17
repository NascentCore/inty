"""
Cloudflare CDN代理服务
负责将GCS图片URL转换为Cloudflare CDN代理URL以提供加速访问
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml


class ImageTransformService:
    """Cloudflare CDN代理服务"""

    def __init__(self):
        self.config = global_config_loaded_from_config_yaml.cloudflare
        self.gcs_pattern = re.compile(
            r"https?://storage\.googleapis\.com/([^/]+/.+)"
        )
        self.gcs_uri_pattern = re.compile(r"gs://([^/]+/.+)")  # 支持 gs:// 格式
        # CDN URL pattern: https://domain.com/bucket/path (简单代理模式)
        self.cdn_pattern = None
        if self.config.domain:
            self.cdn_pattern = re.compile(
                rf"https://{re.escape(self.config.domain)}/(.+)"
            )

    def is_gcs_url(self, url: str) -> bool:
        """检查是否为GCS URL（支持 https:// 和 gs:// 格式）"""
        if not url:
            return False
        return bool(
            self.gcs_pattern.match(url) or self.gcs_uri_pattern.match(url)
        )

    def extract_gcs_path(self, gcs_url: str) -> Optional[str]:
        """从GCS URL中提取bucket和路径部分（支持 https:// 和 gs:// 格式）"""
        # 尝试匹配 https://storage.googleapis.com/bucket/path 格式
        match = self.gcs_pattern.match(gcs_url)
        if match:
            return match.group(1)  # 返回bucket/path部分

        # 尝试匹配 gs://bucket/path 格式
        match = self.gcs_uri_pattern.match(gcs_url)
        if match:
            return match.group(1)  # 返回bucket/path部分

        return None

    def is_cloudflare_url(self, url: str) -> bool:
        """检查是否为Cloudflare CDN URL"""
        if not url or not self.cdn_pattern:
            return False
        return bool(self.cdn_pattern.match(url))

    def cloudflare_to_gcs(self, cdn_url: str) -> Optional[str]:
        """
        将Cloudflare CDN URL转换回GCS URL

        Args:
            cdn_url: Cloudflare CDN URL，格式如：https://domain.com/cdn-cgi/image/options/bucket/path

        Returns:
            对应的GCS URL，格式如：https://storage.googleapis.com/bucket/path
        """
        if not self.is_cloudflare_url(cdn_url):
            return None

        try:
            match = self.cdn_pattern.match(cdn_url)
            if match:
                gcs_path = match.group(1)  # 提取bucket/path部分
                gcs_url = f"https://storage.googleapis.com/{gcs_path}"
                logger.debug(
                    f"Converted CDN URL to GCS: {cdn_url} -> {gcs_url}"
                )
                return gcs_url
        except Exception as e:
            logger.error(
                f"Failed to convert CDN URL to GCS: {cdn_url}, error: {str(e)}"
            )

        return None

    def transform_url(self, original_url: str) -> str:
        """
        转换GCS URL到Cloudflare CDN代理URL

        Args:
            original_url: 原始GCS URL

        Returns:
            CDN代理URL，如果转换失败或未启用则返回原URL
        """
        # 检查是否启用Cloudflare转换
        if not self.config.enabled:
            return original_url

        # 检查是否为有效的GCS URL
        if not self.is_gcs_url(original_url):
            return original_url

        # 检查domain配置
        if not self.config.domain:
            logger.warning(
                "Cloudflare domain not configured, returning original URL"
            )
            return original_url

        try:
            # 从GCS URL提取路径部分
            gcs_path = self.extract_gcs_path(original_url)
            if not gcs_path:
                logger.warning(
                    f"Failed to extract path from GCS URL: {original_url}"
                )
                return original_url

            # 构建Cloudflare CDN代理URL，简单的代理模式
            # 格式: https://domain.com/bucket/path (直接代理，无图片处理)
            cloudflare_url = f"https://{self.config.domain}/{gcs_path}"
            return cloudflare_url

        except Exception as e:
            logger.error(f"Failed to transform URL {original_url}: {str(e)}")
            if self.config.fallback_to_original:
                return original_url
            raise

    def transform_mobile(self, original_url: str) -> str:
        """转换为CDN代理URL"""
        return self.transform_url(original_url)

    def transform_desktop(self, original_url: str) -> str:
        """转换为CDN代理URL"""
        return self.transform_url(original_url)

    def transform_thumbnail(self, original_url: str) -> str:
        """转换为CDN代理URL"""
        return self.transform_url(original_url)

    def transform_agent_images(
        self, agent_data: dict, client_type: str = "mobile"
    ) -> dict:
        """
        批量转换Agent中的所有图片URL为CDN代理URL

        Args:
            agent_data: Agent数据字典
            client_type: 客户端类型 (已忽略，仅保持兼容性)

        Returns:
            转换后的Agent数据
        """
        # client_type参数保留用于兼容性，但不再使用
        if not self.config.enabled:
            return agent_data

        # 图片字段列表
        image_fields = ["avatar", "background"]
        list_image_fields = ["background_images", "photos"]

        # 转换单个图片字段
        for field in image_fields:
            if field in agent_data and agent_data[field]:
                agent_data[field] = self.transform_url(agent_data[field])

        # 转换图片列表字段
        for field in list_image_fields:
            if field in agent_data and isinstance(agent_data[field], list):
                agent_data[field] = [
                    self.transform_url(url) for url in agent_data[field] if url
                ]

        return agent_data

    def transform_url_list(
        self, urls: List[str], client_type: str = "mobile"
    ) -> List[str]:
        """批量转换URL列表为CDN代理URL"""
        # client_type参数保留用于兼容性，但不再使用
        if not self.config.enabled:
            return urls

        return [self.transform_url(url) for url in urls if url]

    def normalize_image_url_for_storage(self, url: str) -> str:
        """统一处理输入URL：CDN URL转换为GCS URL用于存储"""
        if not url:
            return url

        if self.is_cloudflare_url(url):
            gcs_url = self.cloudflare_to_gcs(url)
            if gcs_url:
                logger.debug(
                    f"已将CDN URL转换为GCS URL用于存储: {url} -> {gcs_url}"
                )
                return gcs_url
            else:
                logger.warning(f"CDN URL转换失败，使用原URL: {url}")
                return url
        return url  # 已经是GCS URL，直接返回

    def batch_normalize_urls_for_storage(self, urls_dict: dict) -> dict:
        """批量处理多个URL字段，将CDN URL转换为GCS URL用于存储"""
        if not self.config.enabled:
            return urls_dict

        url_fields = ["avatar", "background"]
        list_url_fields = ["background_images", "photos"]

        result = urls_dict.copy()

        # 处理单个URL字段
        for field in url_fields:
            if field in result and result[field]:
                result[field] = self.normalize_image_url_for_storage(
                    result[field]
                )

        # 处理URL列表字段
        for field in list_url_fields:
            if field in result and isinstance(result[field], list):
                result[field] = [
                    self.normalize_image_url_for_storage(url)
                    for url in result[field]
                    if url
                ]

        return result

    @dataclass
    class CroppedArea:
        """
        来自于 agent info extension 字段的 avatar_crop 字段
        {"avatar_crop": {"x": 197, "y": 97, "width": 444, "height": 445, "imageWidth": 832, "imageHeight": 1216}}
        """

        x: int
        y: int
        width: int
        height: int
        image_width: int  # 原图宽度
        image_height: int  # 原图高度

    def transform_cropped_avatar_url(
        self, background_url: str, avatar_crop: CroppedArea
    ) -> str:
        """
        转换裁剪后的头像URL为带有 trim 参数的 Cloudflare CDN URL

        Args:
            background_url: 背景图片的GCS URL
            avatar_crop: 裁切区域信息，包含 x, y, width, height

        Returns:
            带有裁切参数的CDN URL，如果转换失败则返回原始背景URL
        """
        # 检查是否启用Cloudflare转换
        if not self.config.enabled:
            return background_url

        # 检查是否为有效的GCS URL
        if not self.is_gcs_url(background_url):
            return background_url

        # 检查domain配置
        if not self.config.domain:
            logger.warning(
                "Cloudflare domain not configured, returning original URL"
            )
            return background_url

        try:
            # 从GCS URL提取路径部分
            gcs_path = self.extract_gcs_path(background_url)
            if not gcs_path:
                logger.warning(
                    f"Failed to extract path from GCS URL: {background_url}"
                )
                return background_url

            # 构建带有裁切参数的Cloudflare CDN URL
            # 坐标转换：extension格式(保留区域) -> Cloudflare trim格式
            # Extension格式：{x, y, width, height, imageWidth, imageHeight} 描述要保留的区域
            #
            # 经过分析用户提供的工作示例，发现Cloudflare trim可能使用以下格式之一：
            # 1. top;right;bottom;left (CSS margin顺序)
            # 2. x;y;width;height (绝对坐标)
            #
            # 基于用户工作URL trim=103;34;65;134 的分析，尝试不同的转换方式

            # 方案1：假设trim参数就是 x;y;width;height 格式（直接使用extension数据）
            # 但这与文档不符，且数值与extension数据不匹配

            # 方案2：假设是 top;right;bottom;left 边距格式
            trim_top = avatar_crop.y
            trim_right = avatar_crop.image_width - (
                avatar_crop.x + avatar_crop.width
            )
            trim_bottom = avatar_crop.image_height - (
                avatar_crop.y + avatar_crop.height
            )
            trim_left = avatar_crop.x

            # 构建Cloudflare CDN URL (format: top;right;bottom;left)
            trim_params = f"{trim_top};{trim_right};{trim_bottom};{trim_left}"
            cropped_url = f"https://{self.config.domain}/cdn-cgi/image/trim={trim_params}/{gcs_path}"

            logger.debug(
                f"Transformed cropped avatar URL: {background_url} -> {cropped_url} (keep area: x={avatar_crop.x},y={avatar_crop.y},w={avatar_crop.width},h={avatar_crop.height} -> trim margins top;right;bottom;left: {trim_top};{trim_right};{trim_bottom};{trim_left})"
            )
            return cropped_url

        except Exception as e:
            logger.error(
                f"Failed to transform cropped avatar URL {background_url}: {str(e)}"
            )
            if self.config.fallback_to_original:
                return background_url
            raise


# 创建全局实例
image_transform_service = ImageTransformService()
