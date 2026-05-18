import asyncio
from typing import Optional

from google.genai import types
from loguru import logger
from sqlalchemy import select

from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.cache_service import cache_service
from app.utils.gemini import get_genai_client


class SelfiePersonaService:
    MAX_SUMMARY_LENGTH = 160
    SELFIE_PERSONA_PROMPT = """
Analyze the selfie and write ONE short user profile sentence for a chat assistant.

Requirements:
- English only.
- Keep it under 25 words.
- Focus on broad visible vibe/style (for example: calm, confident, sporty, elegant).
- Do NOT infer sensitive traits (race, religion, health, sexual orientation, politics, income).
- If uncertain, return a neutral and safe sentence.
- Return only the sentence with no prefix.
"""

    def enqueue_selfie_persona_inference(
        self, user_id: str, user_photo_url: str
    ) -> None:
        if not self._is_feature_enabled():
            return
        if not user_photo_url:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning(
                "No running event loop; skip selfie persona inference: user_id={}",
                user_id,
            )
            return

        task = loop.create_task(
            self._infer_and_save_selfie_persona(
                user_id=user_id,
                user_photo_url=user_photo_url,
            )
        )
        task.add_done_callback(self._on_background_task_done)

    @staticmethod
    def _on_background_task_done(task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return

        error = task.exception()
        if error is not None:
            logger.error(f"selfie persona background task failed: {error}")

    async def _infer_and_save_selfie_persona(
        self,
        user_id: str,
        user_photo_url: str,
    ) -> None:
        if not self._is_feature_enabled():
            return
        summary = await self._infer_selfie_persona_summary(user_photo_url)
        if not summary:
            logger.debug(
                "No selfie persona summary generated: user_id={}",
                user_id,
            )
            return

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user is None:
                logger.warning(
                    "User not found while saving selfie persona: user_id={}",
                    user_id,
                )
                return

            # 跳过过期任务：仅为当前自拍照片写入画像结论。
            if user.user_photo != user_photo_url:
                logger.debug(
                    "Skip outdated selfie persona task: user_id={}",
                    user_id,
                )
                return

            user.selfie_persona_summary = summary
            await db.commit()

        cache_service.invalidate_user_info(user_id)
        cache_service.invalidate_user_auth_snapshot(user_id)
        logger.debug("Selfie persona summary updated: user_id={}", user_id)

    async def _infer_selfie_persona_summary(
        self, user_photo_url: str
    ) -> Optional[str]:
        image_uri = self._normalize_image_uri(user_photo_url)
        if not image_uri:
            return None

        client = get_genai_client()
        image_part = types.Part.from_uri(
            file_uri=image_uri,
            mime_type="image/jpeg",
        )

        contents = [
            types.Content(
                role="user",
                parts=[
                    image_part,
                    types.Part.from_text(text=self.SELFIE_PERSONA_PROMPT),
                ],
            )
        ]
        config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.8,
            max_output_tokens=80,
        )

        response = await asyncio.to_thread(
            client.models.generate_content,
            model=global_config_loaded_from_config_yaml.agent.selfie_persona_gemini_model,
            contents=contents,
            config=config,
        )
        raw_text = self._extract_response_text(response)
        return self._normalize_persona_summary(raw_text)

    @staticmethod
    def _normalize_image_uri(user_photo_url: str) -> str:
        if user_photo_url.startswith("http://") or user_photo_url.startswith(
            "https://"
        ):
            return user_photo_url
        if user_photo_url.startswith("gs://"):
            return user_photo_url.replace(
                "gs://", "https://storage.googleapis.com/", 1
            )
        return ""

    @staticmethod
    def _extract_response_text(response: object) -> Optional[str]:
        candidates = getattr(response, "candidates", None)
        if not candidates:
            return None

        candidate = candidates[0]
        content = getattr(candidate, "content", None)
        if content is None:
            return None

        parts = getattr(content, "parts", None)
        if not parts:
            return None

        chunks = [part.text for part in parts if getattr(part, "text", None)]
        if not chunks:
            return None
        return " ".join(chunks).strip()

    def _normalize_persona_summary(
        self, raw_text: Optional[str]
    ) -> Optional[str]:
        if raw_text is None:
            return None

        summary = " ".join(raw_text.split()).strip().strip("\"'")
        if not summary:
            return None

        prefixes = ("selfie persona:", "persona:", "summary:")
        lower_summary = summary.lower()
        for prefix in prefixes:
            if lower_summary.startswith(prefix):
                summary = summary[len(prefix) :].strip()
                break

        if not summary:
            return None

        if len(summary) > self.MAX_SUMMARY_LENGTH:
            summary = summary[: self.MAX_SUMMARY_LENGTH].rstrip(" ,.;:") + "..."

        return summary

    @staticmethod
    def _is_feature_enabled() -> bool:
        return (
            global_config_loaded_from_config_yaml.app.features.enable_selfie_persona_summary
        )


selfie_persona_service = SelfiePersonaService()
