"""
图片生成服务：基于聊天上下文和角色背景图生成图片
使用 Gemini 2.5 Flash Image 模型实现角色外观一致性。

本模块使用 generate_content（非 Imagen generate_images）：图片以内联数据返回，
由本服务调用 upload_to_gcs 上传；Imagen 的 generate_images 则通过
output_gcs_uri 由 SDK 直接写 GCS。
"""

import base64
import io
import os
import re
import tempfile
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

import PIL.Image
from app.core.google_genai.wrapped_client import (
    GeminiImageExtractionError,
    WrappedClient,
)
from google.genai import types
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent import prompts as agent_prompts
from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.gcs import GCS_GS_PREFIX, GCS_PUBLIC_HTTPS_PREFIX, upload_to_gcs
from app.models.resource import ResourceType
from app.services import agent_service, chat_history_service
from app.services.image_transform_service import image_transform_service
from app.services.resource_service import async_create_image_resource
from app.services.user_service import build_user_info_prompt_block
from app.utils.gemini import get_genai_client
from app.utils.image import ImageFormat, ImageSize
from app.utils.models_catalog import NANO_BANANA

# 生图失败时日志中提示词最大长度，避免泄露过多用户内容并控制日志体积
_MAX_PROMPT_LOG_LEN = 800000


class GeneratedImageProcessResult(TypedDict):
    """Result of processing a Gemini image_part: metadata dict plus raw data and GCS URI."""

    size: ImageSize
    format: ImageFormat
    raw_data: bytes
    gcs_uri: str
    generated_at: datetime.time


def _process_image_part_to_generated_image(
    image_part: Any,
    gcs_uri_base: str,
) -> GeneratedImageProcessResult:
    """
    从 Gemini 返回的 image_part（inline_data）解析图片、上传 GCS，返回 generated_image 元数据及 image_data、gcs_uri。
    """
    logger.debug("inline_data 类型: {}", type(image_part.inline_data))
    logger.debug("inline_data.data 类型: {}", type(image_part.inline_data.data))
    if hasattr(image_part.inline_data, "mime_type"):
        logger.debug(
            "inline_data.mime_type: {}",
            image_part.inline_data.mime_type,
        )

    raw_data = image_part.inline_data.data
    if isinstance(raw_data, str):
        image_data = base64.b64decode(raw_data)
        logger.debug("数据是 base64 字符串，已解码")
    elif isinstance(raw_data, bytes):
        image_data = raw_data
        logger.debug("数据已经是 bytes，直接使用")
    else:
        logger.error("未知的数据类型: {}", type(raw_data))
        raise ValueError(
            "Unsupported image data type: {}".format(type(raw_data))
        )

    logger.info("成功提取图片数据，大小: {} bytes", len(image_data))
    if len(image_data) == 0:
        raise ValueError("Image data is empty")

    header = image_data[:20] if len(image_data) >= 20 else image_data
    logger.debug("图片数据头部（hex）: {}", header.hex())

    if image_data[:2] == b"\xff\xd8":
        logger.debug("检测到 JPEG 格式")
    elif image_data[:8] == b"\x89PNG\r\n\x1a\n":
        logger.debug("检测到 PNG 格式")
    elif image_data[:6] in (b"GIF87a", b"GIF89a"):
        logger.debug("检测到 GIF 格式")
    elif image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
        logger.debug("检测到 WEBP 格式")
    else:
        logger.warning("未知的图片格式，尝试作为原始数据处理")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            tmp.write(image_data)
            logger.debug("原始数据已写入: {}", tmp.name)

    try:
        pil_image = PIL.Image.open(io.BytesIO(image_data))
        width, height = pil_image.size
        image_format = pil_image.format or "JPEG"
        logger.info(
            "成功解析图片: {}x{}, 格式: {}", width, height, image_format
        )
    except Exception as e:
        logger.error("PIL 无法解析图片: {}", str(e))
        try:
            text_content = image_data.decode("utf-8")[:200]
            logger.error("数据可能是文本: {}", text_content)
        except (UnicodeDecodeError, ValueError, AttributeError):
            # 仅避免 decode 失败掩盖主异常，不改变主流程
            pass
        raise ValueError("Unable to parse image data: {}".format(str(e))) from e

    # 按实际格式设置 content_type 与扩展名，避免将 PNG 等误标为 JPEG
    _FORMAT_TO_MIME = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "GIF": "image/gif",
        "WEBP": "image/webp",
    }
    _FORMAT_TO_EXT = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "WEBP": "webp"}
    fmt_upper = (image_format or "JPEG").upper()
    content_type = _FORMAT_TO_MIME.get(fmt_upper, "image/jpeg")
    ext = _FORMAT_TO_EXT.get(fmt_upper, "jpg")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    gcs_path = "{}/{}_{}.{}".format(
        gcs_uri_base, timestamp, uuid.uuid4().hex[:8], ext
    )
    bucket_name = global_config_loaded_from_config_yaml.gcs.bucket
    upload_to_gcs(
        file_data=image_data,
        content_type=content_type,
        bucket_name=bucket_name,
        path=gcs_path,
    )
    gcs_uri = "gs://{}/{}".format(bucket_name, gcs_path)
    logger.info("图片已上传到 GCS: {}", gcs_uri)

    generated_image: Dict[str, Any] = {
        "image_url": gcs_uri,
        "width": width,
        "height": height,
        "format": image_format.lower(),
        "generated_at": datetime.utcnow().isoformat(),
    }
    return {
        "generated_image": generated_image,
        "size": ImageSize(width=width, height=height),
        "format": image_format.lower(),
        "raw_data": image_data,
        "gcs_uri": gcs_uri,
    }


def _serialize_gemini_response_for_log(response: Any) -> Dict[str, Any]:
    """将 Gemini generate_content 的返回序列化为可安全写入日志的字典（不含图片二进制）。"""
    out: Dict[str, Any] = {}
    if response is None:
        return out
    try:
        _fill_serialized_gemini_response(out, response)
    except Exception as e:
        logger.warning("生图失败日志序列化异常，使用简化信息: {}", e)
        return {"error": "serialization_failed", "message": str(e)}
    return out


def _fill_serialized_gemini_response(out: Dict[str, Any], response: Any) -> None:
    """填充 out，可能抛错；由 _serialize_gemini_response_for_log 捕获。"""
    if hasattr(response, "prompt_feedback") and response.prompt_feedback:
        pf = response.prompt_feedback
        out["prompt_feedback"] = {
            "block_reason": getattr(pf, "block_reason", None),
        }
    if hasattr(response, "candidates") and response.candidates:
        candidates = []
        for i, c in enumerate(response.candidates):
            entry: Dict[str, Any] = {
                "index": i,
                "finish_reason": getattr(c, "finish_reason", None),
            }
            safety_ratings = getattr(c, "safety_ratings", None) or []
            if safety_ratings:
                entry["safety_ratings"] = [
                    {
                        "category": getattr(r, "category", None),
                        "probability": getattr(r, "probability", None),
                        "blocked": getattr(r, "blocked", None),
                    }
                    for r in safety_ratings
                ]
            parts = (
                getattr(c.content, "parts", None)
                if (hasattr(c, "content") and c.content)
                else None
            )
            if parts is not None:
                parts_info = []
                for p in parts or []:
                    if hasattr(p, "inline_data") and p.inline_data:
                        parts_info.append(
                            {
                                "kind": "inline_data",
                                "size_bytes": len(getattr(p.inline_data, "data", b"")),
                            }
                        )
                    elif hasattr(p, "text") and p.text:
                        parts_info.append({"kind": "text", "length": len(p.text)})
                    else:
                        parts_info.append({"kind": "other"})
                entry["content_parts"] = parts_info
            else:
                entry["content"] = None
            candidates.append(entry)
        out["candidates"] = candidates
    else:
        out["candidates"] = []


def _format_safety_rating(rating: Any, include_blocked: bool = False) -> str:
    """将单条 safety_rating 格式化为可读字符串，用于日志与错误信息。"""
    category = getattr(rating, "category", "UNKNOWN")
    probability = getattr(rating, "probability", "UNKNOWN")
    if include_blocked:
        severity = getattr(rating, "blocked", False)
        return f"{category}={probability}(blocked={severity})"
    return f"{category}={probability}"


def _log_image_generation_failure(prompt: Optional[str], response: Any) -> None:
    """生图失败时在日志中记录提示词（过长时截断）与 Gemini 返回结果。loguru 使用 {} 占位符。"""
    if prompt is None:
        prompt_for_log = "(无)"
    elif len(prompt) <= _MAX_PROMPT_LOG_LEN:
        prompt_for_log = prompt
    else:
        prompt_for_log = (
            prompt[:_MAX_PROMPT_LOG_LEN]
            + "… [truncated, total len="
            + str(len(prompt))
            + "]"
        )
    logger.error(
        "生图失败 - 完整提示词: {}",
        prompt_for_log,
    )
    logger.error(
        "生图失败 - Gemini 返回: {}",
        _serialize_gemini_response_for_log(response),
    )


def _extract_image_part_from_gemini_response(
    prompt: Optional[str], response: Any
) -> types.Part:
    """
    校验 Gemini generate_content 响应并提取图片 part。
    成功时返回含有 inline_data 的 part；失败时记录日志并抛出 ValueError。
    """
    # 检查 prompt_feedback（响应级别的反馈）
    if hasattr(response, "prompt_feedback") and response.prompt_feedback:
        prompt_feedback = response.prompt_feedback
        logger.warning("Prompt feedback: {}", prompt_feedback)
        if hasattr(prompt_feedback, "block_reason"):
            block_reason = prompt_feedback.block_reason
            logger.warning("请求被阻止，原因: {}", block_reason)
            _log_image_generation_failure(prompt, response)
            raise ValueError(
                f"Image generation request blocked by safety filter: {block_reason}"
            )

    if not response.candidates:
        logger.error("Gemini 未返回任何候选结果")
        _log_image_generation_failure(prompt, response)
        raise ValueError("Gemini returned no candidates")

    candidate = response.candidates[0]

    # 检查 finish_reason（完成原因）
    finish_reason = getattr(candidate, "finish_reason", None)
    if finish_reason:
        logger.warning("候选结果完成原因: {}", finish_reason)
        if finish_reason == "SAFETY":
            safety_ratings = getattr(candidate, "safety_ratings", None) or []
            safety_details = [
                _format_safety_rating(r, include_blocked=True)
                for r in safety_ratings
            ]
            error_msg = "Image generation blocked by safety filter"
            if safety_details:
                error_msg += f"; details: {', '.join(safety_details)}"
            logger.error(error_msg)
            _log_image_generation_failure(prompt, response)
            raise ValueError(error_msg)
        elif finish_reason not in ("STOP", None):
            logger.warning("候选结果以非正常原因结束: {}", finish_reason)

    # 检查 safety_ratings（即使 finish_reason 不是 SAFETY，也可能有安全评级）
    candidate_safety_ratings = getattr(candidate, "safety_ratings", None) or []
    blocked_ratings = [
        _format_safety_rating(r)
        for r in candidate_safety_ratings
        if hasattr(r, "blocked") and r.blocked
    ]
    if blocked_ratings:
        error_msg = f"Image generation blocked by safety filter: {', '.join(blocked_ratings)}"
        logger.error(error_msg)
        _log_image_generation_failure(prompt, response)
        raise ValueError(error_msg)

    # 检查 content 和 parts
    if not candidate.content or not candidate.content.parts:
        logger.error("候选结果中没有内容，finish_reason={}", finish_reason)
        error_msg = "No content in candidates"
        if finish_reason:
            error_msg += f" (finish_reason: {finish_reason})"
        _log_image_generation_failure(prompt, response)
        raise ValueError(error_msg)

    # 查找图片部分
    image_part = None
    for part in candidate.content.parts:
        if hasattr(part, "inline_data") and part.inline_data:
            image_part = part
            break

    if not image_part:
        _log_image_generation_failure(prompt, response)
        raise ValueError("No image data found in response")

    return image_part


class ImageGenerationService:
    """图片生成服务，是提供了内部服务中间件抽象的对 Gemini 图像生成的封装"""

    def build_image_prompt(
        self,
        agent_data: dict,
        chat_history: List[dict],
        user_message: str,
        user_info: str = "",
    ) -> str:
        """
        构建生图提示词

        Args:
            agent_data: Agent数据，包含personality、scenario等
            chat_history: 聊天历史记录
            user_message: 用户当前请求的消息内容
            user_info: 用户信息块（##User Information...），可为空

        Returns:
            完整的生图提示词
        """
        # 提取角色背景信息
        agent_background = agent_data.get("scenario", "")
        agent_personality = agent_data.get("personality", "")

        # TODO: 需要使用 jinja2 template 渲染 agent_background 和 agent_personality
        # 来填充 {{ char }} 和 {{ user }} 变量。
        # 目前不太好弄，因为传入的对象类型是 dict，而不是 Agent 对象，不好分辨。

        # 如果没有scenario，尝试使用intro
        if not agent_background:
            agent_background = agent_data.get("intro", "")

        # 格式化聊天历史
        history_text = ""
        if chat_history:
            history_lines = []
            for msg in chat_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    history_lines.append(f"用户: {content}")
                elif role == "assistant":
                    history_lines.append(f"AI: {content}")
            history_text = "\n".join(history_lines)

        # 使用统一的图片生成提示词模板
        template = agent_prompts.IMAGE_GENERATION_PROMPT_TEMPLATE

        # 替换模板变量
        prompt = template.format(
            agent_background=agent_background,
            agent_personality=agent_personality,
            chat_history=history_text,
            user_message=user_message,
            user_info=user_info,
        )

        logger.debug("构建的生图提示词: {}", prompt)
        return prompt

    def _tokenize_text(self, text_input: str) -> set:
        """
        简单的文本分词，用于相似度计算
        对中文进行字符级分词，对英文进行单词级分词

        Args:
            text_input: 输入文本

        Returns:
            词汇集合
        """
        if not text_input:
            return set()

        # 移除标点符号和空白字符，保留中文字符、英文字母和数字
        text_input = re.sub(r"[^\w\s\u4e00-\u9fff]", "", text_input)
        # 分割空白字符
        tokens = re.findall(r"[\u4e00-\u9fff]|\w+", text_input.lower())
        return set(tokens)

    def calculate_prompt_similarity(self, prompt1: str, prompt2: str) -> float:
        """
        计算两个提示词的相似度（使用Jaccard相似度）

        Args:
            prompt1: 第一个提示词
            prompt2: 第二个提示词

        Returns:
            相似度分数（0-1之间）
        """
        if not prompt1 or not prompt2:
            return 0.0

        tokens1 = self._tokenize_text(prompt1)
        tokens2 = self._tokenize_text(prompt2)

        if not tokens1 or not tokens2:
            return 0.0

        # 计算Jaccard相似度：交集/并集
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        if union == 0:
            return 0.0

        similarity = intersection / union
        return similarity

    async def get_generated_images_for_agent(
        self,
        db: AsyncSession,
        agent_id: str,
        exclude_user_id: Optional[str] = None,
        only_user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        查询指定agent的已生成图片（从resources表查询）

        Args:
            db: 数据库会话
            agent_id: Agent ID
            exclude_user_id: 排除指定用户的图片（用于优先匹配其他用户）
            only_user_id: 仅查询指定用户的图片

        Returns:
            包含图片信息的列表，每个元素包含：
            - image_url: 图片GCS URI
            - prompt: 生成图片的提示词
            - width: 图片宽度
            - height: 图片高度
            - format: 图片格式
            - user_id: 生成该图片的用户ID
            - generated_at: 生成时间（created_at）
        """
        try:
            # TODO：如何确保 Cache 可以稳定的在数据库更新后获得更新从而拿到最新数据？
            from app import models

            # 构建查询条件
            conditions = [
                models.Resource.agent_id == agent_id,
                models.Resource.type == ResourceType.IMAGE,
                models.Resource.resource_metadata.isnot(None),
            ]

            if exclude_user_id:
                conditions.append(models.Resource.user_id != exclude_user_id)

            if only_user_id:
                conditions.append(models.Resource.user_id == only_user_id)

            query = (
                select(models.Resource)
                .where(*conditions)
                .order_by(models.Resource.created_at.desc())
            )

            result = await db.execute(query)
            resources = result.scalars().all()

            images = []
            for resource in resources:
                try:
                    metadata = resource.resource_metadata
                    if not metadata:
                        continue

                    prompt = metadata.get("generation_prompt")
                    if not prompt:
                        continue

                    size = metadata.get("size", {})
                    width = size.get("width") if isinstance(size, dict) else None
                    height = size.get("height") if isinstance(size, dict) else None

                    # 从content_type提取格式
                    content_type = metadata.get("content_type", "image/jpeg")
                    format_str = (
                        content_type.split("/")[-1] if "/" in content_type else "jpeg"
                    )

                    images.append(
                        {
                            "image_url": resource.url,  # GCS URI
                            "prompt": prompt,
                            "width": width,
                            "height": height,
                            "format": format_str,
                            "user_id": resource.user_id,
                            "generated_at": (
                                resource.created_at.isoformat()
                                if resource.created_at
                                else None
                            ),
                        }
                    )
                except Exception as e:
                    logger.warning(
                        "解析资源元数据失败: {}, resource_url: {}",
                        str(e),
                        resource.url,
                    )
                    continue

            logger.debug(
                "查询到 Agent {} 的 {} 张已生成图片（exclude_user_id={}, only_user_id={}）",
                agent_id,
                len(images),
                exclude_user_id,
                only_user_id,
            )
            return images

        except Exception as e:
            logger.error("查询已生成图片失败: {}", str(e))
            traceback.print_exc()
            return []

    def _find_best_match_in_images(
        self, images: List[Dict[str, Any]], current_prompt: str
    ) -> Optional[Dict[str, Any]]:
        """
        在图片列表中找到最匹配的图片

        Args:
            images: 图片列表
            current_prompt: 当前提示词

        Returns:
            最相似的图片，如果没有匹配则返回None
        """
        if not images:
            return None

        best_match = None
        best_similarity = 0.0

        for image in images:
            saved_prompt = image.get("prompt", "")
            if not saved_prompt:
                continue

            similarity = self.calculate_prompt_similarity(current_prompt, saved_prompt)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = image.copy()
                best_match["similarity"] = similarity

        if best_match and best_similarity > 0:
            return best_match
        return None

    async def find_most_similar_image(
        self,
        db: AsyncSession,
        agent_id: str,
        current_prompt: str,
        current_user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        根据提示词相似度找到最匹配的图片
        优先匹配其他用户生成的图片，其次匹配当前用户的图片

        Args:
            db: 数据库会话
            agent_id: Agent ID
            current_prompt: 当前提示词
            current_user_id: 当前用户ID（用于优先级匹配）

        Returns:
            最相似的图片信息，如果未找到则返回None
        """
        try:
            # 第一步：优先匹配其他用户的图片
            if current_user_id:
                other_users_images = await self.get_generated_images_for_agent(
                    db, agent_id, exclude_user_id=current_user_id
                )
                if other_users_images:
                    best_match = self._find_best_match_in_images(
                        other_users_images, current_prompt
                    )
                    if best_match:
                        logger.info(
                            f"找到其他用户的匹配图片，相似度: {best_match.get('similarity', 0):.3f}, "
                            f"user_id: {best_match.get('user_id')}"
                        )
                        return best_match

            # 第二步：匹配当前用户的图片
            if current_user_id:
                current_user_images = await self.get_generated_images_for_agent(
                    db, agent_id, only_user_id=current_user_id
                )
            else:
                # 如果没有current_user_id，查询所有图片
                current_user_images = await self.get_generated_images_for_agent(
                    db, agent_id
                )

            if current_user_images:
                best_match = self._find_best_match_in_images(
                    current_user_images, current_prompt
                )
                if best_match:
                    logger.info(
                        "找到当前用户的匹配图片，相似度: {:.3f}",
                        best_match.get("similarity", 0),
                    )
                    return best_match

            logger.debug("Agent {} 没有匹配的图片", agent_id)
            return None

        except Exception as e:
            logger.error("查找最相似图片失败: {}", str(e))
            traceback.print_exc()
            return None

    async def generate_chat_image_with_gemini(
        self,
        db: AsyncSession,
        session_id: str,
        message_id: int,
        agent_data: dict,
        message_content: str,
        user_id: Optional[str] = None,
        history_count: Optional[int] = None,
        model: Optional[str] = None,
    ) -> Dict:
        """
        使用 Gemini 模型（generate_content）生成聊天图片并更新到消息 meta_data。

        与 Imagen generate_images 不同：本路径使用 generate_content，返回内联图片
        (candidate.content.parts[].inline_data)，无 output_gcs_uri；应用侧从响应中
        取出图片字节后调用 upload_to_gcs 上传到 GCS。

        Args:
            db: 数据库会话
            session_id: 聊天会话ID
            message_id: 要更新的消息ID
            agent_data: Agent数据
            message_content: 触发生图的消息内容
            user_id: 用户ID
            history_count: 要使用的历史消息数量
            model: Vertex AI 模型 ID，如 gemini-3-pro-image-preview、gemini-2.5-flash-image。
                   None 时使用 gemini-2.5-flash-image 以保持向后兼容。

        Returns:
            包含图片信息的字典
        """
        logger.debug(
            "使用 Gemini 模型及 Google GenAI SDK 生成图片，session_id={}, model={}",
            session_id,
            model,
        )
        # 提前定义 2 个变量，在后续代码中赋值，并用于记录日志
        prompt: Optional[str] = None
        response: Any = None
        try:
            # 测试模式：通过环境变量触发模拟失败（仅用于测试匹配逻辑）
            # 设置环境变量: TEST_IMAGE_GEN_FAIL=safety_filter 或 TEST_IMAGE_GEN_FAIL=network_error
            test_fail_mode = os.environ.get("TEST_IMAGE_GEN_FAIL", "").lower()
            if test_fail_mode == "safety_filter":
                logger.warning("测试模式：模拟安全过滤器阻止")
                raise ValueError(
                    "Image generation blocked by safety filter: test mode trigger"
                )
            elif test_fail_mode == "network_error":
                logger.warning("测试模式：模拟网络错误")
                raise ConnectionError("Connection timeout: test mode trigger")

            # 确定历史消息数量
            if history_count is None:
                history_count = (
                    global_config_loaded_from_config_yaml.agent.image_generation_default_history_count
                )

            # 获取聊天历史
            messages_data = chat_history_service.get_messages_paginated(
                session_id=session_id,
                limit=history_count,
                offset=0,
            )
            chat_history = messages_data.get("messages", [])

            # 获取用户信息（若有 user_id）
            user_info = ""
            user_photo_url = None
            if user_id:
                # TODO：是否可以缓存？
                user_info = await build_user_info_prompt_block(db, user_id)
                # 查询用户的自拍照片
                from app.models.user import User

                # TODO：是否可以缓存？
                user_result = await db.execute(
                    select(User.user_photo).where(User.id == user_id)
                )
                user_photo_url = user_result.scalar_one_or_none()

            # 构建提示词
            prompt = self.build_image_prompt(
                agent_data=agent_data,
                chat_history=chat_history,
                user_message=message_content,
                user_info=user_info,
            )

            # 获取Agent参考图（优先使用背景图，如果不存在则使用头像）
            reference_url = agent_data.get("background") or agent_data.get("avatar")
            if not reference_url:
                raise ValueError(
                    "Agent has no background or avatar; cannot generate image"
                )

            # 确保参考图是完整URL
            # 如果是GCS路径，转换为URL
            if reference_url.startswith(GCS_GS_PREFIX):
                reference_url = reference_url.replace(
                    GCS_GS_PREFIX, GCS_PUBLIC_HTTPS_PREFIX
                )
            if not reference_url.startswith("http"):
                raise ValueError(f"Invalid reference image path: {reference_url}, must start with 'http'")

            # 记录使用的参考图类型
            reference_type = "背景图" if agent_data.get("background") else "头像"
            logger.info(
                "开始生成图片，session_id={}, 使用{}: {}",
                session_id,
                reference_type,
                reference_url,
            )

            # 复用现有的 Gemini 客户端（自动从 service account 读取配置）
            client = WrappedClient(client=get_genai_client())
            contents = []
            contents.append(reference_url)

            # 如果用户有自拍照片，添加为额外参考图
            if user_photo_url:
                # 确保用户照片是完整 URL（与 reference_url 一致，使用 GCS 常量）
                if user_photo_url.startswith(GCS_GS_PREFIX):
                    user_photo_url = user_photo_url.replace(
                        GCS_GS_PREFIX, GCS_PUBLIC_HTTPS_PREFIX
                    )
                if user_photo_url.startswith("http"):
                    contents.append(user_photo_url)
                    logger.info("添加用户自拍照片作为参考图: {}", user_photo_url)
                else:
                    logger.error("用户自拍照片不是完整URL: {}", user_photo_url)

            contents.append(prompt)

            gemini_model = model or NANO_BANANA.id_on_provider
            try:
                image_part = await client.async_generate_image(
                    model=gemini_model, contents=contents
                )
            except GeminiImageExtractionError as e:
                _log_image_generation_failure(prompt, e.response)
                raise

            agent_id = agent_data.get("id")
            if not agent_id:
                raise ValueError("Agent data missing ID; cannot generate image path")
            gcs_uri_base = f"chat_images/{agent_id}"
            result = _process_image_part_to_generated_image(
                image_part, gcs_uri_base=gcs_uri_base
            )
            metadata_update = {"generated_image": result["generated_image"]}
            if prompt is not None:
                metadata_update["generated_image"]["prompt"] = prompt
            image_data = result["image_data"]
            gcs_uri = result["gcs_uri"]
            width = result["generated_image"]["width"]
            height = result["generated_image"]["height"]
            image_format = result["generated_image"]["format"]
            cdn_url = image_transform_service.transform_desktop(gcs_uri)

            success = await chat_history_service.update_message_metadata(
                db=db,
                session_id=session_id,
                message_id=message_id,
                metadata_update=metadata_update,
            )

            if not success:
                raise ValueError(f"Failed to update meta_data for message {message_id}")

            # agent_id 已在上面获取
            if agent_id:
                await agent_service.append_agent_background_image(
                    db=db, agent_id=agent_id, image_url=gcs_uri
                )
            else:
                logger.warning("Agent数据缺少ID，无法追加生成图片到背景图历史")

            # 保存到resources表（用于后续匹配查询）
            if user_id:
                try:
                    # 确定图片格式
                    image_format_enum = ImageFormat.JPEG
                    if image_format.lower() == "png":
                        image_format_enum = ImageFormat.PNG
                    elif image_format.lower() == "gif":
                        image_format_enum = ImageFormat.GIF
                    elif image_format.lower() == "webp":
                        image_format_enum = ImageFormat.WEBP

                    # 创建ImageSize对象
                    image_size = ImageSize(width=width, height=height)

                    # 保存到resources表（使用GCS URI作为url）
                    await async_create_image_resource(
                        async_db=db,
                        user_id=user_id,
                        url=gcs_uri,  # 使用GCS URI作为主键
                        size=image_size,
                        format=image_format_enum,
                        byte_size=len(image_data),
                        compressed=False,
                        cropped=False,
                        gcs_url=gcs_uri,
                        generation_prompt=prompt,
                        reference_image_url=reference_url,
                    )

                    # 设置agent_id（async_create_image_resource没有agent_id参数）
                    from app import models

                    update_stmt = (
                        update(models.Resource)
                        .where(models.Resource.url == gcs_uri)
                        .values(agent_id=agent_id)
                    )
                    await db.execute(update_stmt)
                    await db.commit()

                    logger.info("图片已保存到resources表: {}", gcs_uri)
                except Exception as e:
                    logger.warning("保存图片到resources表失败: {}", str(e))
                    traceback.print_exc()
                    # 不影响主流程，继续执行
            else:
                logger.warning("未传入user_id，无法保存到resources表")

            logger.info(
                "图片生成成功并更新到消息 meta_data，message_id={}, cdn_url={}",
                message_id,
                cdn_url,
            )

            return {
                "message_id": message_id,
                "image_url": cdn_url,  # 返回 CDN URL
                "image_metadata": {
                    "width": width,
                    "height": height,
                    "format": image_format.lower(),
                },
                "prompt": prompt,
            }

        except Exception as e:
            logger.error("使用 Gemini 生成聊天图片失败: {}", str(e))
            _log_image_generation_failure(prompt, response)
            traceback.print_exc()
            raise

    async def generate_chat_image_with_fal(
        self,
        db: AsyncSession,
        session_id: str,
        message_id: int,
        agent_data: dict,
        message_content: str,
        model: str,
        user_id: Optional[str] = None,
        history_count: Optional[int] = None,
    ) -> Dict:
        """
        使用 fal.ai image-to-image 生成聊天图片并更新到消息 meta_data

        Args:
            db: 数据库会话
            session_id: 聊天会话ID
            message_id: 要更新的消息ID
            agent_data: Agent数据
            message_content: 触发生图的消息内容
            model: fal 模型名，如 "fal-ai/z-image/turbo/image-to-image"
            user_id: 用户ID（用于保存到resources表）
            history_count: 要使用的历史消息数量

        Returns:
            包含图片信息的字典
        """
        import httpx

        from app.external_services.fal import FalAIClient

        try:
            # 确定历史消息数量
            if history_count is None:
                history_count = (
                    global_config_loaded_from_config_yaml.agent.image_generation_default_history_count
                )

            # 获取聊天历史
            messages_data = chat_history_service.get_messages_paginated(
                session_id=session_id,
                limit=history_count,
                offset=0,
            )
            chat_history = messages_data.get("messages", [])

            # 获取用户信息（若有 user_id）
            user_info = ""
            if user_id:
                user_info = await build_user_info_prompt_block(db, user_id)

            # 构建提示词
            prompt = self.build_image_prompt(
                agent_data=agent_data,
                chat_history=chat_history,
                user_message=message_content,
                user_info=user_info,
            )

            # 获取Agent参考图（优先使用背景图，如果不存在则使用头像）
            reference_url = agent_data.get("background") or agent_data.get("avatar")
            if not reference_url:
                raise ValueError(
                    "Agent has no background or avatar; cannot generate image"
                )

            # 确保参考图是完整URL
            if not reference_url.startswith("http"):
                if reference_url.startswith("gs://"):
                    reference_url = reference_url.replace(
                        "gs://", "https://storage.googleapis.com/"
                    )
                else:
                    raise ValueError(f"Invalid reference image path: {reference_url}")

            reference_type = "背景图" if agent_data.get("background") else "头像"
            logger.info(
                "开始使用 fal.ai 生成图片，session_id={}, model={}, 使用{}: {}",
                session_id,
                model,
                reference_type,
                reference_url,
            )

            # 调用 fal.ai image-to-image
            fal_api_key = global_config_loaded_from_config_yaml.fal.api_key
            client = FalAIClient(api_key=fal_api_key)

            fal_result = client.image_to_image(
                model=model,
                image_url=reference_url,
                prompt=prompt,
                strength=0.75,
                num_images=1,
            )

            if not fal_result.images:
                raise ValueError("fal.ai returned no images")

            fal_image = fal_result.images[0]
            image_url = fal_image.url

            logger.info("fal.ai 生成图片成功: {}", image_url)

            # 下载图片
            async with httpx.AsyncClient(timeout=60.0) as http_client:
                response = await http_client.get(image_url)
                response.raise_for_status()
                image_data = response.content

            # 获取图片尺寸
            pil_image = PIL.Image.open(io.BytesIO(image_data))
            width, height = pil_image.size
            image_format = pil_image.format or "JPEG"
            logger.info(
                "成功下载图片: {}x{}, 格式: {}, 大小: {} bytes",
                width,
                height,
                image_format,
                len(image_data),
            )

            # 生成GCS路径
            agent_id = agent_data.get("id")
            if not agent_id:
                raise ValueError("Agent data missing ID; cannot generate image path")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            gcs_path = f"chat_images/{agent_id}/{timestamp}_{uuid.uuid4().hex[:8]}.jpg"

            # 上传到GCS
            bucket_name = global_config_loaded_from_config_yaml.gcs.bucket
            public_url = upload_to_gcs(
                file_data=image_data,
                content_type="image/jpeg",
                bucket_name=bucket_name,
                path=gcs_path,
            )
            logger.info("图片已上传到 GCS: {}", public_url)

            # 转换为 gs:// URI 格式用于存储
            gcs_uri = f"gs://{bucket_name}/{gcs_path}"

            # 转换为CDN URL
            cdn_url = image_transform_service.transform_desktop(gcs_uri)

            # 更新消息的 meta_data
            metadata_update = {
                "generated_image": {
                    "image_url": gcs_uri,
                    "width": width,
                    "height": height,
                    "format": image_format.lower(),
                    "prompt": prompt,
                    "model": model,
                    "generated_at": datetime.utcnow().isoformat(),
                }
            }

            success = await chat_history_service.update_message_metadata(
                db=db,
                session_id=session_id,
                message_id=message_id,
                metadata_update=metadata_update,
            )

            if not success:
                raise ValueError(f"Failed to update meta_data for message {message_id}")

            # 追加到 Agent 背景图历史
            if agent_id:
                await agent_service.append_agent_background_image(
                    db=db, agent_id=agent_id, image_url=gcs_uri
                )

            # 保存到resources表
            if user_id:
                try:
                    image_format_enum = ImageFormat.JPEG
                    if image_format.lower() == "png":
                        image_format_enum = ImageFormat.PNG
                    elif image_format.lower() == "gif":
                        image_format_enum = ImageFormat.GIF
                    elif image_format.lower() == "webp":
                        image_format_enum = ImageFormat.WEBP

                    image_size = ImageSize(width=width, height=height)

                    await async_create_image_resource(
                        async_db=db,
                        user_id=user_id,
                        url=gcs_uri,
                        size=image_size,
                        format=image_format_enum,
                        byte_size=len(image_data),
                        compressed=False,
                        cropped=False,
                        gcs_url=gcs_uri,
                        generation_prompt=prompt,
                        reference_image_url=reference_url,
                    )

                    from app import models

                    update_stmt = (
                        update(models.Resource)
                        .where(models.Resource.url == gcs_uri)
                        .values(agent_id=agent_id)
                    )
                    await db.execute(update_stmt)
                    await db.commit()

                    logger.info("图片已保存到resources表: {}", gcs_uri)
                except Exception as e:
                    logger.warning("保存图片到resources表失败: {}", str(e))
                    traceback.print_exc()

            logger.info(
                "fal.ai 图片生成成功并更新到消息 meta_data，message_id={}, cdn_url={}",
                message_id,
                cdn_url,
            )

            return {
                "message_id": message_id,
                "image_url": cdn_url,
                "image_metadata": {
                    "width": width,
                    "height": height,
                    "format": image_format.lower(),
                },
                "prompt": prompt,
            }

        except Exception as e:
            logger.error("使用 fal.ai 生成聊天图片失败: {}", str(e))
            traceback.print_exc()
            raise


# 创建服务实例
image_generation_service = ImageGenerationService()
