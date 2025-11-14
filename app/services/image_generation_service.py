"""
图片生成服务：基于聊天上下文和角色背景图生成图片
使用 Gemini 2.5 Flash Image 模型实现角色外观一致性
"""

import io
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import PIL.Image
from google.genai import types
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.gcs import upload_to_gcs
from app.services import agent_service, chat_history_service
from app.services.image_transform_service import image_transform_service
from app.utils.gemini import get_genai_client


class ImageGenerationService:
    """图片生成服务 - 使用 Gemini 2.5 Flash Image"""

    def build_image_prompt(
        self,
        agent_data: dict,
        chat_history: List[dict],
        user_message: str,
    ) -> str:
        """
        构建生图提示词

        Args:
            agent_data: Agent数据，包含personality、scenario等
            chat_history: 聊天历史记录
            user_message: 用户当前请求的消息内容

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

        # 使用配置的模板
        template = (
            global_config_loaded_from_config_yaml.agent.image_generation_prompt_template
        )

        # 替换模板变量
        prompt = template.format(
            agent_background=agent_background,
            agent_personality=agent_personality,
            chat_history=history_text,
            user_message=user_message,
        )

        logger.debug(f"构建的生图提示词: {prompt}")
        return prompt

    async def generate_chat_image_with_gemini(
        self,
        db: AsyncSession,
        session_id: str,
        message_id: int,
        agent_data: dict,
        message_content: str,
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

            # 构建提示词
            prompt = self.build_image_prompt(
                agent_data=agent_data,
                chat_history=chat_history,
                user_message=message_content,
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

            # 生成GCS路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            gcs_path = f"chat_images/{timestamp}_{uuid.uuid4().hex[:8]}.jpg"

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

            agent_id = agent_data.get("id")
            if agent_id:
                await agent_service.append_agent_background_image(
                    db=db, agent_id=agent_id, image_url=gcs_uri
                )
            else:
                logger.warning("Agent数据缺少ID，无法追加生成图片到背景图历史")

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


# 创建服务实例
image_generation_service = ImageGenerationService()
