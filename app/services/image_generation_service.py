"""
图片生成服务：基于聊天上下文和角色背景图生成图片
使用 Gemini 2.5 Flash Image 模型实现角色外观一致性。

本模块使用 generate_content（非 Imagen generate_images）：图片以内联数据返回，
由本服务调用 upload_to_gcs 上传；Imagen 的 generate_images 则通过
output_gcs_uri 由 SDK 直接写 GCS。
"""

import asyncio
import os
import re
import traceback
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from app.core.google_genai.wrapped_client import get_wrapped_client
from langsmith.run_helpers import traceable
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent import prompts as agent_prompts
from app.core.agent.prompt_template import render_prompt_jinja2_template
from app.core.config import global_config_loaded_from_config_yaml
from app.core.images.fal import (
    FalSeedreamV4_5EditInput,
    ZImageTurboImageToImageInput,
    seedream_v4_5_edit,
    z_image_turbo_image_to_image,
)
from app.core.images.types import GeneratedImageProcessResult
from app.external_services.gcs import (
    GCS_GS_PREFIX,
    GCS_PUBLIC_HTTPS_PREFIX,
)
from app.models.resource import Resource, ResourceType
from app.models.user import User
from app.services import agent_service, chat_history_service
from app.services.image_transform_service import image_transform_service
from app.services.resource_service import async_create_image_resource
from app.services.user_service import (
    build_user_info_prompt_block,
    get_user_display_name_for_prompt,
)
from app.utils.langsmith import get_current_trace_info
from app.utils.models_catalog import (
    CHAT_IMAGE_FAL_IDS,
    CHAT_IMAGE_GEN_MODELS,
    ModelNameFamily,
    NANO_BANANA_MODELS,
    SEEDREAM_V4_5_EDIT,
    Z_IMAGE_TURBO_IMAGE_TO_IMAGE,
    detect_model_name_family,
    resolve_id_on_provider,
    resolve_nickname,
)

# 生图失败时日志中提示词最大长度，避免泄露过多用户内容并控制日志体积
_MAX_PROMPT_LOG_LEN = 800000
_MAX_TRACE_TEXT_PREVIEW_LEN = 500


class ChatImageGenInput(BaseModel):
    """
    这是从聊天历史中收集到的信息，用于构建生图模型的提示词。
    """

    history_count: int
    chat_history: List[Any]
    user_info: str
    user_photo_url: Optional[str] = None
    char_name: str
    user_name: str
    prompt: str
    reference_url: str
    reference_type: Literal["背景图", "头像"]


class ChatImageGenModelInput(BaseModel):
    """
    统一聊天生图模型输入：用于模型路由与 provider 输入适配。
    """

    prompt: str
    reference_image_url: str
    message_history: List[Dict[str, Any]] = Field(default_factory=list)
    model_id_on_provider: str
    user_reference_image_url: Optional[str] = None
    append_history_to_prompt: bool = True


def _truncate_trace_text(value: Any) -> str:
    text = str(value)
    if len(text) <= _MAX_TRACE_TEXT_PREVIEW_LEN:
        return text
    return text[:_MAX_TRACE_TEXT_PREVIEW_LEN] + "…"


def _process_inputs_generate_chat_image(inputs: Dict[str, Any]) -> Dict[str, Any]:
    agent_data = inputs.get("agent_data") or {}
    message_content = inputs.get("message_content") or ""
    output: Dict[str, Any] = {
        "session_id": inputs.get("session_id"),
        "message_id": inputs.get("message_id"),
        "agent_id": agent_data.get("id"),
        "model": inputs.get("model"),
        "user_id": inputs.get("user_id"),
        "history_count": inputs.get("history_count"),
        "message_content_len": len(message_content),
        "message_content": message_content,
    }
    return output


def _process_outputs_generate_chat_image(outputs: Any) -> Any:
    if not isinstance(outputs, dict):
        return outputs
    prompt = outputs.get("prompt")
    out = dict(outputs)
    if isinstance(prompt, str):
        out["prompt_len"] = len(prompt)
        out["prompt_preview"] = _truncate_trace_text(prompt)
        out["prompt"] = "[omitted in trace, see prompt_preview]"
    return out


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


class ImageGenerationService:
    """图片生成服务，是提供了内部服务中间件抽象的对 Gemini 图像生成的封装"""

    def build_image_prompt(
        self,
        agent_data: dict,
        chat_history: List[dict],
        user_message: str,
        user_info: str = "",
        char_name: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> str:
        """
        构建生图提示词

        Args:
            agent_data: Agent数据，包含personality、scenario等
            chat_history: 聊天历史记录
            user_message: 用户当前请求的消息内容
            user_info: 用户信息块（##User Information...），可为空
            char_name: 角色名，用于渲染 personality/scenario 中的 {{ char }}
            user_name: 用户显示名，用于渲染 personality/scenario 中的 {{ user }}

        Returns:
            完整的生图提示词
        """
        # 提取角色背景（scenario 优先，无则用 intro）与性格
        agent_background = agent_data.get("scenario", "") or agent_data.get("intro", "")
        agent_personality = agent_data.get("personality", "")

        # 若调用方传入 char_name 与 user_name，则用 jinja2 渲染 personality/background 中的 {{ char }} / {{ user }}
        if char_name is not None and user_name is not None:
            agent_personality = render_prompt_jinja2_template(
                agent_personality, char=char_name, user=user_name
            )
            agent_background = render_prompt_jinja2_template(
                agent_background, char=char_name, user=user_name
            )

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

    async def get_char_user_names_for_image_prompt(
        self,
        db: AsyncSession,
        user_id: Optional[str],
        agent_data: dict,
    ) -> tuple[Optional[str], str]:
        """
        解析用于生图提示词 Jinja2 渲染的 char/user 显示名。
        供 build_image_prompt 调用方统一使用，避免重复解析逻辑。
        """
        char_name = agent_data.get("name")
        user_name = (
            await get_user_display_name_for_prompt(db, user_id)
            if user_id
            else "the user"
        )
        return (char_name, user_name)

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

    def _resolve_chat_image_gen_model_id_or_nickname(self, id_or_nickname: str) -> str:
        """
        解析聊天生图模型：支持直接传 provider model id，也支持传模型 nickname。
        model 可以是 GenAIModel.nickname 或 GenAIModel.id_on_provider。
        """
        model = resolve_id_on_provider(id_or_nickname)
        if model:
            return model.id_on_provider
        model = resolve_nickname(id_or_nickname)
        if model:
            return model.id_on_provider
        allowed_nicknames = [m.nickname for m in CHAT_IMAGE_GEN_MODELS]
        allowed_ids_on_provider = [m.id_on_provider for m in CHAT_IMAGE_GEN_MODELS]
        allowed = allowed_nicknames + allowed_ids_on_provider
        raise ValueError(
            f"Chat image model {id_or_nickname!r} not allowed; allowed: {', '.join(allowed)}"
        )

    def _format_message_history_for_model_prompt(
        self, message_history: List[Dict[str, Any]]
    ) -> str:
        lines: list[str] = []
        for message in message_history:
            role = str(message.get("role", "")).lower()
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            if role == "user":
                lines.append(f"User: {content}")
            elif role == "assistant":
                lines.append(f"Assistant: {content}")
            else:
                lines.append(content)
        return "\n".join(lines)

    def _build_chat_image_prompt_for_model(
        self, prompt: str, message_history: List[Dict[str, Any]]
    ) -> str:
        history_text = self._format_message_history_for_model_prompt(message_history)
        if not history_text:
            return prompt
        if history_text in prompt:
            return prompt
        return f"{prompt}\n\nRecent conversation context:\n{history_text}"

    async def _generate_chat_image_with_resolved_gemini_model(
        self,
        model_id: str,
        prompt: str,
        reference_image_url: str,
        user_reference_image_url: Optional[str],
        gcs_uri_base: str,
        system_instructions: Optional[List[str]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> GeneratedImageProcessResult:
        if model_id not in [m.id_on_provider for m in NANO_BANANA_MODELS]:
            raise ValueError(f"{model_id!r} not supported by WrappedClient")

        client = get_wrapped_client()
        contents = [reference_image_url]
        if user_reference_image_url:
            contents.append(user_reference_image_url)
            logger.info("添加用户自拍照片作为参考图: {}", user_reference_image_url)
        contents.append(prompt)

        async def _generate_images() -> list[GeneratedImageProcessResult]:
            return await client.async_generate_images(
                model=model_id,
                contents=contents,
                gcs_uri_base=gcs_uri_base,
                system_instructions=system_instructions,
            )

        if timeout_seconds is not None and timeout_seconds > 0:
            try:
                results = await asyncio.wait_for(
                    _generate_images(),
                    timeout=float(timeout_seconds),
                )
            except asyncio.TimeoutError as e:
                raise TimeoutError(
                    f"Chat image generation timeout after {timeout_seconds}s for model {model_id}"
                ) from e
        else:
            results = await _generate_images()

        if not results:
            raise ValueError(f"No images generated for model {model_id}")
        return results[0]

    async def _generate_chat_image_with_resolved_fal_model(
        self,
        model_id: str,
        prompt: str,
        reference_image_url: str,
        user_reference_image_url: Optional[str],
        gcs_uri_base: str,
    ) -> GeneratedImageProcessResult:
        if model_id == Z_IMAGE_TURBO_IMAGE_TO_IMAGE.id_on_provider:
            args = ZImageTurboImageToImageInput(
                image_url=reference_image_url,
                prompt=prompt,
                # strength=0.6（官方推荐平衡性较好的数值、越大 strength 意味着会更按照提示词进行修改）num_images=1
            )
            return await z_image_turbo_image_to_image(args, gcs_uri_base=gcs_uri_base)

        if model_id == SEEDREAM_V4_5_EDIT.id_on_provider:
            seedream_image_urls = [reference_image_url]
            if user_reference_image_url:
                seedream_image_urls.append(user_reference_image_url)
                logger.info(
                    "Seedream 使用用户自拍作为第二参考图: {}", user_reference_image_url
                )
            if len(seedream_image_urls) < 2:
                seedream_image_urls.append(reference_image_url)
            args = FalSeedreamV4_5EditInput(
                prompt=prompt,
                image_urls=seedream_image_urls,
            )
            return await seedream_v4_5_edit(args, gcs_uri_base=gcs_uri_base)

        raise ValueError(
            f"Chat image fal model {model_id!r} not allowed; "
            f"allowed: {', '.join(CHAT_IMAGE_FAL_IDS)}"
        )

    async def generate_chat_image_by_model(
        self,
        chat_input: ChatImageGenModelInput,
        gcs_uri_base: str,
        system_instructions: Optional[List[str]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> GeneratedImageProcessResult:
        """
        统一聊天生图模型入口：
        - 输入：prompt + reference image + message history + model
        - 逻辑：解析模型并自动路由（Gemini/fal）
        - 适配：转换为各 provider 需要的输入参数
        """
        resolved_model_id = chat_input.model_id_on_provider
        if chat_input.append_history_to_prompt:
            prompt_for_model = self._build_chat_image_prompt_for_model(
                prompt=chat_input.prompt,
                message_history=chat_input.message_history,
            )
        else:
            prompt_for_model = chat_input.prompt

        model_family = detect_model_name_family(resolved_model_id)
        if model_family == ModelNameFamily.FAL:
            return await self._generate_chat_image_with_resolved_fal_model(
                model_id=resolved_model_id,
                prompt=prompt_for_model,
                reference_image_url=chat_input.reference_image_url,
                user_reference_image_url=chat_input.user_reference_image_url,
                gcs_uri_base=gcs_uri_base,
            )

        if model_family == ModelNameFamily.GEMINI:
            return await self._generate_chat_image_with_resolved_gemini_model(
                model_id=resolved_model_id,
                prompt=prompt_for_model,
                reference_image_url=chat_input.reference_image_url,
                user_reference_image_url=chat_input.user_reference_image_url,
                gcs_uri_base=gcs_uri_base,
                system_instructions=system_instructions,
                timeout_seconds=timeout_seconds,
            )
        raise ValueError(
            f"Chat image model family unsupported for {resolved_model_id!r}; "
            "expected fal or gemini"
        )

    async def get_generated_images_for_agent(
        self,
        db: AsyncSession,
        agent_id: str,
        exclude_user_id: Optional[str] = None,
        only_user_id: Optional[str] = None,
        only_include_ai_character: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        查询指定agent的已生成图片（从resources表查询）

        Args:
            db: 数据库会话
            agent_id: Agent ID
            exclude_user_id: 排除指定用户的图片（用于优先匹配其他用户）
            only_user_id: 仅查询指定用户的图片
            only_include_ai_character: 为 True 时仅返回 metadata 中 only_include_ai_character 为 True 的图（兜底候选）

        Returns:
            包含图片信息的列表，每个元素包含：
            - image_id: 稳定图片标识（Resource.url，用于兜底去重）
            - image_url: 图片GCS URI
            - prompt: 生成图片的提示词
            - width, height, format, user_id, generated_at
        """
        try:
            # TODO：如何确保 Cache 可以稳定的在数据库更新后获得更新从而拿到最新数据？
            # 构建查询条件
            conditions = [
                Resource.agent_id == agent_id,
                Resource.type == ResourceType.IMAGE,
                Resource.resource_metadata.isnot(None),
            ]

            if exclude_user_id:
                conditions.append(Resource.user_id != exclude_user_id)

            if only_user_id:
                conditions.append(Resource.user_id == only_user_id)

            if only_include_ai_character is True:
                conditions.append(
                    Resource.resource_metadata.op("->>")("only_include_ai_character")
                    == "true"
                )

            query = (
                select(Resource).where(*conditions).order_by(Resource.created_at.desc())
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
                            "image_id": resource.url,
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
                "查询到 Agent {} 的 {} 张已生成图片（exclude_user_id={}, only_user_id={}, only_include_ai_character={}）",
                agent_id,
                len(images),
                exclude_user_id,
                only_user_id,
                only_include_ai_character,
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

    def _exclude_image_ids(
        self,
        images: List[Dict[str, Any]],
        exclude_image_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """从候选列表中排除已发送过的兜底图（按 image_id 去重）。"""
        if not exclude_image_ids:
            return images
        exclude_set = set(exclude_image_ids)
        return [img for img in images if img.get("image_id") not in exclude_set]

    async def find_most_similar_image(
        self,
        db: AsyncSession,
        agent_id: str,
        current_prompt: str,
        current_user_id: Optional[str] = None,
        only_include_ai_character: bool = False,
        exclude_image_ids: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        根据提示词相似度找到最匹配的图片
        优先匹配其他用户生成的图片，其次匹配当前用户的图片。

        Args:
            only_include_ai_character: 为 True 时仅从带该标签的图中选（兜底候选）
            exclude_image_ids: 排除的 image_id 列表（如该 chat 已展示的兜底图），在相似度匹配前过滤
        Returns:
            最相似的图片信息（含 image_id），如果未找到则返回 None
        """
        try:
            # 第一步：优先匹配其他用户的图片
            if current_user_id:
                other_users_images = await self.get_generated_images_for_agent(
                    db,
                    agent_id,
                    exclude_user_id=current_user_id,
                    only_include_ai_character=only_include_ai_character,
                )
                other_users_images = self._exclude_image_ids(
                    other_users_images, exclude_image_ids
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
                    db,
                    agent_id,
                    only_user_id=current_user_id,
                    only_include_ai_character=only_include_ai_character,
                )
            else:
                current_user_images = await self.get_generated_images_for_agent(
                    db, agent_id, only_include_ai_character=only_include_ai_character
                )
            current_user_images = self._exclude_image_ids(
                current_user_images, exclude_image_ids
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

    async def _prepare_chat_image_inputs(
        self,
        db: AsyncSession,
        session_id: str,
        agent_data: dict,
        message_content: str,
        user_id: Optional[str] = None,
        history_count: Optional[int] = None,
    ) -> ChatImageGenInput:
        """
        准备聊天生图所需输入：历史消息、用户信息、提示词、参考图 URL 等。
        由 generate_chat_image_for_message 共用。
        """
        if history_count is None:
            history_count = (
                global_config_loaded_from_config_yaml.agent.image_generation_default_history_count
            )
        messages_data = chat_history_service.get_messages_paginated(
            session_id=session_id,
            limit=history_count,
            offset=0,
        )
        chat_history = messages_data.get("messages", [])

        user_info = ""
        user_photo_url = None
        if user_id:
            user_info = await build_user_info_prompt_block(db, user_id)
            user_result = await db.execute(
                select(User.user_photo).where(User.id == user_id)
            )
            user_photo_url = user_result.scalar_one_or_none()
            # 归一化为可用的 HTTPS URL，与 reference_url 一致；无效则置为 None
            if user_photo_url:
                if user_photo_url.startswith(GCS_GS_PREFIX):
                    user_photo_url = user_photo_url.replace(
                        GCS_GS_PREFIX, GCS_PUBLIC_HTTPS_PREFIX
                    )
                if not user_photo_url.startswith("http"):
                    logger.error("用户自拍照片不是完整URL: {}", user_photo_url)
                    user_photo_url = None

        char_name, user_name = await self.get_char_user_names_for_image_prompt(
            db, user_id, agent_data
        )
        # build_image_prompt 接受空字符串；get_char_user_names_for_image_prompt 可能返回 None
        char_name = char_name or ""
        user_name = user_name or ""
        prompt = self.build_image_prompt(
            agent_data=agent_data,
            chat_history=chat_history,
            user_message=message_content,
            user_info=user_info,
            char_name=char_name,
            user_name=user_name,
        )

        reference_url = agent_data.get("background") or agent_data.get("avatar")
        if not reference_url:
            raise ValueError("Agent has no background or avatar; cannot generate image")
        if reference_url.startswith(GCS_GS_PREFIX):
            reference_url = reference_url.replace(
                GCS_GS_PREFIX, GCS_PUBLIC_HTTPS_PREFIX
            )
        if not reference_url.startswith("http"):
            raise ValueError(
                f"Invalid reference image path: {reference_url}, must start with 'http'"
            )
        reference_type: Literal["背景图", "头像"] = (
            "背景图" if agent_data.get("background") else "头像"
        )

        return ChatImageGenInput(
            history_count=history_count,
            chat_history=chat_history,
            user_info=user_info,
            user_photo_url=user_photo_url,
            char_name=char_name,
            user_name=user_name,
            prompt=prompt,
            reference_url=reference_url,
            reference_type=reference_type,
        )

    @traceable(
        name="generate_chat_image",
        run_type="chain",
        process_inputs=_process_inputs_generate_chat_image,
        process_outputs=_process_outputs_generate_chat_image,
    )
    async def generate_chat_image(
        self,
        db: AsyncSession,
        session_id: str,
        message_id: int,
        agent_data: dict,
        message_content: str,
        model: str,
        user_id: Optional[str] = None,
        history_count: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        统一聊天生图入口（替代 generate_chat_image_with_gemini / generate_chat_image_with_fal）：
        1) 准备聊天生图输入（prompt/reference/history）
        2) 基于 model 路由并适配 provider 输入
        3) 回写消息 meta_data / agent background_images / resources
        4) 返回前端需要的响应结构
        """
        logger.debug(
            "统一聊天生图入口，session_id={}, message_id={}, agent_data={}, model={}",
            session_id,
            message_id,
            agent_data,
            model,
        )

        resolved_model_id = self._resolve_chat_image_gen_model_id_or_nickname(model)
        resolved_model_family = detect_model_name_family(resolved_model_id)

        # 测试模式：通过环境变量触发模拟失败（仅用于测试匹配逻辑）
        # 设置环境变量: TEST_IMAGE_GEN_FAIL=safety_filter 或 TEST_IMAGE_GEN_FAIL=network_error
        # 仅对 Gemini 路径生效，保持与历史行为一致。
        if resolved_model_family == ModelNameFamily.GEMINI:
            test_fail_mode = os.environ.get("TEST_IMAGE_GEN_FAIL", "").lower()
            if test_fail_mode == "safety_filter":
                logger.warning("测试模式：模拟安全过滤器阻止")
                raise ValueError(
                    "Image generation blocked by safety filter: test mode trigger"
                )
            if test_fail_mode == "network_error":
                logger.warning("测试模式：模拟网络错误")
                raise ConnectionError("Connection timeout: test mode trigger")

        prepared = await self._prepare_chat_image_inputs(
            db=db,
            session_id=session_id,
            agent_data=agent_data,
            message_content=message_content,
            user_id=user_id,
            history_count=history_count,
        )

        logger.info(
            "开始生成图片，session_id={}, model={}, 使用{}: {}",
            session_id,
            resolved_model_id,
            prepared.reference_type,
            prepared.reference_url,
        )

        agent_id = agent_data.get("id")
        if not agent_id:
            raise ValueError("Agent data missing ID; cannot generate image path")
        gcs_uri_base = f"chat_images/{agent_id}"

        system_instructions: Optional[List[str]] = None
        if resolved_model_family == ModelNameFamily.GEMINI:
            system_instructions = [
                agent_prompts.R_RATED_ROMANCE_DIRECTOR_SYSTEM_INSTRUCTION_PROMPT
            ]
        result = await self.generate_chat_image_by_model(
            chat_input=ChatImageGenModelInput(
                prompt=prepared.prompt,
                reference_image_url=prepared.reference_url,
                message_history=prepared.chat_history,
                model_id_on_provider=resolved_model_id,
                user_reference_image_url=prepared.user_photo_url,
                append_history_to_prompt=False,
            ),
            gcs_uri_base=gcs_uri_base,
            system_instructions=system_instructions,
            timeout_seconds=timeout_seconds,
        )

        gcs_uri = result.gcs_uri
        width = result.size.width
        height = result.size.height
        image_format = result.format.value
        generated_at_iso = result.generated_at.isoformat()
        cdn_url = image_transform_service.transform_desktop(gcs_uri)

        metadata_update = {
            "generated_image": {
                "image_url": gcs_uri,
                "width": width,
                "height": height,
                "format": image_format,
                "prompt": prepared.prompt,
                "model": resolved_model_id,
                "generated_at": generated_at_iso,
                "reference_image_url": prepared.reference_url,
                "user_reference_image_url": prepared.user_photo_url,
                "reference_image_urls": [
                    url
                    for url in [prepared.reference_url, prepared.user_photo_url]
                    if url is not None
                ],
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

        await agent_service.append_agent_background_image(
            db=db, agent_id=agent_id, image_url=gcs_uri
        )

        if user_id:
            try:
                langsmith_trace_id, langsmith_trace_url = get_current_trace_info()
                byte_size = result.raw_data_total_bytes
                if byte_size <= 0 and isinstance(result.raw_data, bytes):
                    byte_size = len(result.raw_data)
                await async_create_image_resource(
                    async_db=db,
                    user_id=user_id,
                    url=gcs_uri,
                    size=result.size,
                    format=result.format,
                    byte_size=byte_size,
                    compressed=False,
                    cropped=False,
                    gcs_url=gcs_uri,
                    generation_prompt=prepared.prompt,
                    reference_image_url=prepared.reference_url,
                    user_reference_image_url=prepared.user_photo_url,
                    agent_id=agent_id,
                    only_include_ai_character=prepared.user_photo_url is None,
                    langsmith_trace_id=langsmith_trace_id,
                    langsmith_trace_url=langsmith_trace_url,
                )
                logger.info("图片已保存到resources表: {}", gcs_uri)
            except Exception as e:
                # Rollback 以便调用方继续使用同一 session（如重复 url 导致 IntegrityError）
                await db.rollback()
                if isinstance(e, IntegrityError):
                    logger.warning(
                        "保存图片到resources表失败（可能已存在）: {}", str(e)
                    )
                else:
                    logger.warning("保存图片到resources表失败: {}", str(e))
                    traceback.print_exc()

        logger.info(
            "图片生成成功并更新到消息 meta_data，message_id={}, cdn_url={}",
            message_id,
            cdn_url,
        )
        return {
            "message_id": message_id,
            "image_url": cdn_url,
            "image_metadata": {
                "width": width,
                "height": height,
                "format": image_format,
            },
            "prompt": prepared.prompt,
        }


# 创建服务实例
image_generation_service = ImageGenerationService()
