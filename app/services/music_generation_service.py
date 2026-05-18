"""
聊天音乐生成服务
基于聊天上下文调用 fal 音频模型生成音乐片段。
"""

import os
from typing import Any, Optional
from urllib.parse import urlparse

import fal_client
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.services import chat_history_service
from app.services.user_service import build_user_info_prompt_block


class MusicGenerationService:
    """聊天音乐生成服务。"""

    def build_music_prompt(
        self,
        agent_data: dict,
        chat_history: list[dict],
        user_message: str,
        user_info: str = "",
    ) -> str:
        """构建音乐生成提示词。"""
        agent_name = agent_data.get("name") or "the AI companion"
        agent_personality = agent_data.get("personality") or ""
        agent_scenario = (
            agent_data.get("scenario") or agent_data.get("intro") or ""
        )

        history_lines: list[str] = []
        for message in chat_history:
            role = str(message.get("role", "")).lower()
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            if role == "user":
                history_lines.append(f"User: {content}")
            elif role == "assistant":
                history_lines.append(f"Assistant: {content}")
            else:
                history_lines.append(content)
        history_text = "\n".join(history_lines)

        prompt_parts = [
            "Create one short instrumental background music clip for a private emotional chat.",
            "Output should be clean, cinematic, non-vocal, and emotionally coherent.",
            f"Companion profile: {agent_name}.",
        ]
        if agent_personality:
            prompt_parts.append(f"Companion personality: {agent_personality}.")
        if agent_scenario:
            prompt_parts.append(f"Scene context: {agent_scenario}.")
        if user_info:
            prompt_parts.append(f"User info: {user_info}")
        if history_text:
            prompt_parts.append(f"Recent conversation:\n{history_text}")
        prompt_parts.append(f"Focus message: {user_message}")
        prompt_parts.append(
            "Musical constraints: avoid vocals, avoid abrupt ending, soft fade-out."
        )
        prompt = "\n\n".join(prompt_parts)
        logger.debug("构建聊天音乐提示词完成，长度={}。", len(prompt))
        return prompt

    def _extract_audio_url_from_fal_result(
        self, result: dict[str, Any]
    ) -> Optional[str]:
        """
        从 fal 返回中提取音频 URL。

        不同模型返回结构可能不同，这里统一做兼容提取。
        """
        if not isinstance(result, dict):
            return None

        candidates: list[Optional[str]] = []
        audio_obj = result.get("audio")
        if isinstance(audio_obj, dict):
            candidates.append(audio_obj.get("url"))

        audio_file_obj = result.get("audio_file")
        if isinstance(audio_file_obj, dict):
            candidates.append(audio_file_obj.get("url"))

        audios = result.get("audios")
        if isinstance(audios, list) and audios:
            first_audio = audios[0]
            if isinstance(first_audio, dict):
                candidates.append(first_audio.get("url"))

        output_obj = result.get("output")
        if isinstance(output_obj, dict):
            candidates.append(output_obj.get("url"))

        candidates.append(result.get("url"))

        for value in candidates:
            if isinstance(value, str) and value.startswith("http"):
                return value
        return None

    def _extract_duration_seconds_from_fal_result(
        self, result: dict[str, Any]
    ) -> Optional[float]:
        """尽力从 fal 返回中提取时长（秒）。"""
        if not isinstance(result, dict):
            return None

        possible_values: list[Any] = [
            result.get("duration"),
            result.get("duration_seconds"),
        ]
        audio_obj = result.get("audio")
        if isinstance(audio_obj, dict):
            possible_values.extend(
                [audio_obj.get("duration"), audio_obj.get("duration_seconds")]
            )

        for value in possible_values:
            if value is None:
                continue
            try:
                duration = float(value)
            except (TypeError, ValueError):
                continue
            if duration > 0:
                return duration
        return None

    def _guess_audio_format(self, audio_url: str) -> str:
        path = urlparse(audio_url).path.lower()
        if path.endswith(".wav"):
            return "wav"
        if path.endswith(".ogg") or path.endswith(".opus"):
            return "ogg"
        if path.endswith(".flac"):
            return "flac"
        return "mp3"

    async def _generate_music_with_fal(
        self,
        model_id: str,
        prompt: str,
    ) -> dict[str, Any]:
        fal_key = global_config_loaded_from_config_yaml.fal.api_key
        if fal_key:
            os.environ["FAL_KEY"] = fal_key

        handler = await fal_client.submit_async(
            model_id,
            arguments={"prompt": prompt},
        )
        raw_result = await handler.get()
        audio_url = self._extract_audio_url_from_fal_result(raw_result)
        if not audio_url:
            raise ValueError(
                "Music generation succeeded but returned no audio URL"
            )
        duration_seconds = self._extract_duration_seconds_from_fal_result(
            raw_result
        )
        audio_format = self._guess_audio_format(audio_url)
        return {
            "audio_url": audio_url,
            "duration_seconds": duration_seconds,
            "format": audio_format,
            "raw_result": raw_result,
        }

    async def generate_chat_music_for_message(
        self,
        db: AsyncSession,
        session_id: str,
        message_id: int,
        agent_data: dict,
        message_content: str,
        model: str,
        user_id: Optional[str] = None,
        history_count: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        生成聊天音乐并返回统一结果。

        关键步骤（MVP）：
        1) 汇总聊天上下文与用户信息；2) 构建提示词；3) 调用 fal 生成；
        4) 规范化输出给 chat_service 做持久化。
        """
        actual_history_count = history_count
        if actual_history_count is None:
            actual_history_count = (
                global_config_loaded_from_config_yaml.agent.music_generation_default_history_count
            )
        messages_data = chat_history_service.get_messages_paginated(
            session_id=session_id,
            limit=actual_history_count,
            offset=0,
        )
        chat_history = messages_data.get("messages", [])
        user_info = (
            await build_user_info_prompt_block(db, user_id)
            if user_id is not None
            else ""
        )
        prompt = self.build_music_prompt(
            agent_data=agent_data,
            chat_history=chat_history,
            user_message=message_content,
            user_info=user_info,
        )
        fal_result = await self._generate_music_with_fal(
            model_id=model, prompt=prompt
        )
        return {
            "message_id": message_id,
            "audio_url": fal_result["audio_url"],
            "audio_metadata": {
                "duration_sec": fal_result["duration_seconds"],
                "format": fal_result["format"],
                "provider": "fal",
            },
            "prompt": prompt,
            "model": model,
        }


music_generation_service = MusicGenerationService()
