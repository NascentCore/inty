"""
图片生成服务：基于聊天上下文和角色背景图生成图片
使用 Gemini 2.5 Flash Image 模型实现角色外观一致性
"""

import io
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import PIL.Image
from google.genai import types
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent import prompts as agent_prompts
from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.gcs import upload_to_gcs
from app.models.resource import ResourceType
from app.services import agent_service, chat_history_service
from app.services.image_transform_service import image_transform_service
from app.services.resource_service import async_create_image_resource
from app.services.user_service import build_user_info_prompt_block
from app.utils.gemini import get_genai_client
from app.utils.image import ImageFormat, ImageSize


class ImageGenerationService:
    """图片生成服务 - 使用 Gemini 2.5 Flash Image"""

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

        logger.debug(f"构建的生图提示词: {prompt}")
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
                        f"解析资源元数据失败: {str(e)}, resource_url: {resource.url}"
                    )
                    continue

            logger.debug(
                f"查询到 Agent {agent_id} 的 {len(images)} 张已生成图片"
                f"（exclude_user_id={exclude_user_id}, only_user_id={only_user_id}）"
            )
            return images

        except Exception as e:
            logger.error(f"查询已生成图片失败: {str(e)}")
            import traceback

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
                        f"找到当前用户的匹配图片，相似度: {best_match.get('similarity', 0):.3f}"
                    )
                    return best_match

            logger.debug(f"Agent {agent_id} 没有匹配的图片")
            return None

        except Exception as e:
            logger.error(f"查找最相似图片失败: {str(e)}")
            import traceback

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
    ) -> Dict:
        """
        使用 Gemini 2.5 Flash Image 生成聊天图片并更新到消息 meta_data

        Args:
            db: 数据库会话
            session_id: 聊天会话ID
            message_id: 要更新的消息ID
            agent_data: Agent数据
            message_content: 触发生图的消息内容
            history_count: 要使用的历史消息数量

        Returns:
            包含图片信息的字典
        """
        try:
            # 测试模式：通过环境变量触发模拟失败（仅用于测试匹配逻辑）
            # 设置环境变量: TEST_IMAGE_GEN_FAIL=safety_filter 或 TEST_IMAGE_GEN_FAIL=network_error
            import os

            test_fail_mode = os.environ.get("TEST_IMAGE_GEN_FAIL", "").lower()
            if test_fail_mode == "safety_filter":
                logger.warning("测试模式：模拟安全过滤器阻止")
                raise ValueError("图片生成被安全过滤器阻止: 测试模式触发")
            elif test_fail_mode == "network_error":
                logger.warning("测试模式：模拟网络错误")
                raise ConnectionError("Connection timeout: 测试模式触发")

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
                raise ValueError("Agent 没有背景图或头像，无法生成图片")

            # 确保参考图是完整URL
            if not reference_url.startswith("http"):
                # 如果是GCS路径，转换为URL
                if reference_url.startswith("gs://"):
                    reference_url = reference_url.replace(
                        "gs://", "https://storage.googleapis.com/"
                    )
                else:
                    raise ValueError(f"无效的参考图路径: {reference_url}")

            # 记录使用的参考图类型
            reference_type = "背景图" if agent_data.get("background") else "头像"
            logger.info(
                f"开始生成图片，session_id={session_id}, 使用{reference_type}: {reference_url}"
            )

            # 复用现有的 Gemini 客户端（自动从 service account 读取配置）
            client = get_genai_client()

            # 准备输入：参考图 + 文字提示
            reference_image = types.Part.from_uri(
                file_uri=reference_url,
                mime_type="image/jpeg",
            )

            contents = [
                types.Content(
                    role="user",
                    parts=[
                        reference_image,
                        types.Part.from_text(text=prompt),
                    ],
                )
            ]

            # 配置生成参数
            generate_config = types.GenerateContentConfig(
                temperature=1.0,
                top_p=0.95,
                max_output_tokens=8192,
                response_modalities=["IMAGE"],  # 只返回图片
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="BLOCK_MEDIUM_AND_ABOVE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_MEDIUM_AND_ABOVE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="BLOCK_MEDIUM_AND_ABOVE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_MEDIUM_AND_ABOVE",
                    ),
                ],
                image_config=types.ImageConfig(
                    aspect_ratio="9:16",
                ),
            )

            # 调用 Gemini 2.5 Flash Image 生成图片
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=contents,
                config=generate_config,
            )

            # 检查 prompt_feedback（响应级别的反馈）
            if hasattr(response, "prompt_feedback") and response.prompt_feedback:
                prompt_feedback = response.prompt_feedback
                logger.warning(f"Prompt feedback: {prompt_feedback}")
                if hasattr(prompt_feedback, "block_reason"):
                    block_reason = prompt_feedback.block_reason
                    logger.warning(f"请求被阻止，原因: {block_reason}")
                    raise ValueError(f"图片生成请求被安全过滤器阻止: {block_reason}")

            # 提取图片数据
            if not response.candidates or len(response.candidates) == 0:
                logger.error("Gemini 未返回任何候选结果")
                raise ValueError("Gemini 未返回任何候选结果")

            candidate = response.candidates[0]

            # 检查 finish_reason（完成原因）
            finish_reason = getattr(candidate, "finish_reason", None)
            if finish_reason:
                logger.warning(f"候选结果完成原因: {finish_reason}")
                if finish_reason == "SAFETY":
                    # 检查安全评级以获取详细信息
                    safety_ratings = getattr(candidate, "safety_ratings", [])
                    safety_details = []
                    if safety_ratings:
                        for rating in safety_ratings:
                            category = getattr(rating, "category", "UNKNOWN")
                            probability = getattr(rating, "probability", "UNKNOWN")
                            severity = getattr(rating, "blocked", False)
                            safety_details.append(
                                f"{category}={probability}(blocked={severity})"
                            )
                    error_msg = "图片生成被安全过滤器阻止"
                    if safety_details:
                        error_msg += f"，原因: {', '.join(safety_details)}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                elif finish_reason not in ("STOP", None):
                    logger.warning(f"候选结果以非正常原因结束: {finish_reason}")

            # 检查 safety_ratings（即使 finish_reason 不是 SAFETY，也可能有安全评级）
            if hasattr(candidate, "safety_ratings") and candidate.safety_ratings:
                blocked_ratings = []
                for rating in candidate.safety_ratings:
                    if hasattr(rating, "blocked") and rating.blocked:
                        category = getattr(rating, "category", "UNKNOWN")
                        probability = getattr(rating, "probability", "UNKNOWN")
                        blocked_ratings.append(f"{category}={probability}")
                if blocked_ratings:
                    error_msg = (
                        f"图片生成被安全过滤器阻止: {', '.join(blocked_ratings)}"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)

            # 检查 content 和 parts
            if not candidate.content or not candidate.content.parts:
                logger.error(f"候选结果中没有内容，finish_reason={finish_reason}")
                error_msg = "候选结果中没有内容"
                if finish_reason:
                    error_msg += f"（完成原因: {finish_reason}）"
                raise ValueError(error_msg)

            # 查找图片部分
            image_part = None
            for part in candidate.content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    image_part = part
                    break

            if not image_part:
                raise ValueError("响应中没有找到图片数据")

            # 获取图片数据
            import base64

            # 调试：检查 inline_data 的类型和内容
            logger.debug(f"inline_data 类型: {type(image_part.inline_data)}")
            logger.debug(f"inline_data.data 类型: {type(image_part.inline_data.data)}")
            if hasattr(image_part.inline_data, "mime_type"):
                logger.debug(
                    f"inline_data.mime_type: {image_part.inline_data.mime_type}"
                )

            # 获取原始数据
            raw_data = image_part.inline_data.data

            # 判断是否需要 base64 解码
            if isinstance(raw_data, str):
                # 如果是字符串，需要 base64 解码
                image_data = base64.b64decode(raw_data)
                logger.debug("数据是 base64 字符串，已解码")
            elif isinstance(raw_data, bytes):
                # 如果已经是 bytes，直接使用
                image_data = raw_data
                logger.debug("数据已经是 bytes，直接使用")
            else:
                logger.error(f"未知的数据类型: {type(raw_data)}")
                raise ValueError(f"不支持的图片数据类型: {type(raw_data)}")

            logger.info(f"成功提取图片数据，大小: {len(image_data)} bytes")

            # 调试：打印前几个字节来识别格式
            if len(image_data) == 0:
                raise ValueError("图片数据为空")

            header = image_data[:20] if len(image_data) >= 20 else image_data
            logger.debug(f"图片数据头部（hex）: {header.hex()}")

            # 检查常见图片格式的魔术数字
            if image_data[:2] == b"\xff\xd8":
                logger.debug("检测到 JPEG 格式")
            elif image_data[:8] == b"\x89PNG\r\n\x1a\n":
                logger.debug("检测到 PNG 格式")
            elif image_data[:6] in (b"GIF87a", b"GIF89a"):
                logger.debug("检测到 GIF 格式")
            elif image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
                logger.debug("检测到 WEBP 格式")
            else:
                logger.warning(f"未知的图片格式，尝试作为原始数据处理")
                # 尝试将数据写入临时文件进行调试
                import tempfile

                with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
                    tmp.write(image_data)
                    logger.debug(f"原始数据已写入: {tmp.name}")

            # 获取图片尺寸
            try:
                pil_image = PIL.Image.open(io.BytesIO(image_data))
                width, height = pil_image.size
                image_format = pil_image.format or "JPEG"
                logger.info(f"成功解析图片: {width}x{height}, 格式: {image_format}")
            except Exception as e:
                logger.error(f"PIL 无法解析图片: {str(e)}")
                # 尝试检查是否是文本响应
                try:
                    text_content = image_data.decode("utf-8")[:200]
                    logger.error(f"数据可能是文本: {text_content}")
                except:
                    pass
                raise ValueError(f"无法解析图片数据: {str(e)}")

            # 生成GCS路径（以角色组织）
            agent_id = agent_data.get("id")
            if not agent_id:
                raise ValueError("Agent数据缺少ID，无法生成图片路径")
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
            logger.info(f"图片已上传到 GCS: {public_url}")

            # 转换为 gs:// URI 格式用于存储
            gcs_uri = f"gs://{bucket_name}/{gcs_path}"

            # 转换为CDN URL
            cdn_url = image_transform_service.transform_desktop(gcs_uri)

            # 构建图片元数据
            image_metadata = {
                "width": width,
                "height": height,
                "format": image_format.lower(),
                "byte_size": len(image_data),
            }

            # 更新消息的 meta_data，将图片信息存储在其中
            metadata_update = {
                "generated_image": {
                    "image_url": gcs_uri,  # 存储 GCS URI
                    "width": width,
                    "height": height,
                    "format": image_format.lower(),
                    "prompt": prompt,
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
                raise ValueError(f"更新消息 {message_id} 的 meta_data 失败")

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

                    logger.info(f"图片已保存到resources表: {gcs_uri}")
                except Exception as e:
                    logger.warning(f"保存图片到resources表失败: {str(e)}")
                    import traceback

                    traceback.print_exc()
                    # 不影响主流程，继续执行
            else:
                logger.warning("未传入user_id，无法保存到resources表")

            logger.info(
                f"图片生成成功并更新到消息 meta_data，message_id={message_id}, cdn_url={cdn_url}"
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
            logger.error(f"使用 Gemini 生成聊天图片失败: {str(e)}")
            import traceback

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
                raise ValueError("Agent 没有背景图或头像，无法生成图片")

            # 确保参考图是完整URL
            if not reference_url.startswith("http"):
                if reference_url.startswith("gs://"):
                    reference_url = reference_url.replace(
                        "gs://", "https://storage.googleapis.com/"
                    )
                else:
                    raise ValueError(f"无效的参考图路径: {reference_url}")

            reference_type = "背景图" if agent_data.get("background") else "头像"
            logger.info(
                f"开始使用 fal.ai 生成图片，session_id={session_id}, model={model}, 使用{reference_type}: {reference_url}"
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
                raise ValueError("fal.ai 未返回任何图片")

            fal_image = fal_result.images[0]
            image_url = fal_image.url

            logger.info(f"fal.ai 生成图片成功: {image_url}")

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
                f"成功下载图片: {width}x{height}, 格式: {image_format}, 大小: {len(image_data)} bytes"
            )

            # 生成GCS路径
            agent_id = agent_data.get("id")
            if not agent_id:
                raise ValueError("Agent数据缺少ID，无法生成图片路径")
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
            logger.info(f"图片已上传到 GCS: {public_url}")

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
                raise ValueError(f"更新消息 {message_id} 的 meta_data 失败")

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
                    )

                    from app import models

                    update_stmt = (
                        update(models.Resource)
                        .where(models.Resource.url == gcs_uri)
                        .values(agent_id=agent_id)
                    )
                    await db.execute(update_stmt)
                    await db.commit()

                    logger.info(f"图片已保存到resources表: {gcs_uri}")
                except Exception as e:
                    logger.warning(f"保存图片到resources表失败: {str(e)}")
                    import traceback

                    traceback.print_exc()

            logger.info(
                f"fal.ai 图片生成成功并更新到消息 meta_data，message_id={message_id}, cdn_url={cdn_url}"
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
            logger.error(f"使用 fal.ai 生成聊天图片失败: {str(e)}")
            import traceback

            traceback.print_exc()
            raise


# 创建服务实例
image_generation_service = ImageGenerationService()
