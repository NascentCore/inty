# CREATED_BY_AGENT
import time
from textwrap import dedent
from typing import Callable, Dict, Any, List, Tuple

from gemini_client import GeminiClient
from models import (
    CharacterGenerationRequest,
    CharacterIdentityCard,
    CharacterIntroPack,
    RoleplayPrompt,
    ImagePrompt,
    AudioProfile,
    GenerationStage,
    StageStatus,
    MultiStageCharacterPayload,
    MultiStageGenerationResponse,
)
from loguru import logger


class MultiStageCharacterGenerator:
    """Runs a deterministic multistage pipeline for character creation."""

    def __init__(self, gemini_client: GeminiClient | None = None):
        self.client = gemini_client or GeminiClient()

    def generate(
        self, request: CharacterGenerationRequest
    ) -> MultiStageGenerationResponse:
        """Execute the staged pipeline and return a telemetry-rich response."""

        logger.info("Launching multistage character generation")
        start_time = time.time()
        stages: List[GenerationStage] = []

        def run_stage(
            key: str,
            title: str,
            description: str,
            worker: Callable[[], Tuple[Any, Dict[str, Any]]],
        ):
            stage = GenerationStage(
                key=key, title=title, description=description
            )
            stage.status = StageStatus.RUNNING
            stage_start = time.time()

            try:
                payload, artifacts = worker()
                stage.status = StageStatus.COMPLETED
                stage.artifacts = artifacts
                return payload
            except Exception as exc:
                logger.error(f"Stage '{key}' failed: {exc}")
                stage.status = StageStatus.FAILED
                stage.artifacts = {"error": str(exc)}
                raise
            finally:
                stage.duration_seconds = round(time.time() - stage_start, 3)
                stages.append(stage)

        try:
            identity = run_stage(
                "identity",
                "角色身份",
                "根据简述生成独特名字与定位。",
                lambda: self._stage_identity(request),
            )
            intro = run_stage(
                "introduction",
                "角色介绍",
                "整理长短介绍、界限与开场引导。",
                lambda: self._stage_intro(request, identity),
            )
            roleplay_prompts = run_stage(
                "roleplay",
                "互动提示",
                "输出可直接用于扮演的提示语。",
                lambda: self._stage_roleplay_prompts(request, identity, intro),
            )
            asset_bundle = run_stage(
                "assets",
                "多模模版",
                "规划图片提示与音频人设。",
                lambda: self._stage_assets(request, identity, roleplay_prompts),
            )

            payload = MultiStageCharacterPayload(
                identity=identity,
                introduction=intro,
                roleplay_prompts=roleplay_prompts,
                image_prompts=asset_bundle["image_prompts"],
                audio_profile=asset_bundle["audio_profile"],
            )
            success = True
            error = None
        except Exception as exc:
            payload = None
            success = False
            error = str(exc)

        total_time = round(time.time() - start_time, 3)
        logger.info(
            "Multistage pipeline finished in %.2fs with status=%s",
            total_time,
            "success" if success else "error",
        )

        return MultiStageGenerationResponse(
            success=success,
            request=request,
            payload=payload,
            stages=stages,
            error=error,
            generation_time=total_time,
        )

    # ---- Stage implementations -------------------------------------------------

    def _stage_identity(
        self, request: CharacterGenerationRequest
    ) -> Tuple[CharacterIdentityCard, Dict[str, Any]]:
        prompt = dedent(f"""
            Design an original role-play character identity from the brief "{request.brief_description}".
            Consider genre "{request.genre}" and tone "{request.tone}".
            Respond with strict JSON only:
            {{
                "name": "full name",
                "alias": "short nickname",
                "archetype": "story archetype",
                "short_bio": "2 sentence hook",
                "vibe": "one-line mood descriptor",
                "session_goal": "what the character wants out of a chat session",
                "key_traits": ["trait1", "trait2", "trait3"]
            }}
            """)

        data = self._invoke_json(prompt)
        identity = CharacterIdentityCard(
            name=data.get("name") or "Unnamed Companion",
            alias=data.get("alias") or data.get("name") or "Companion",
            archetype=data.get("archetype") or request.genre.title(),
            short_bio=data.get("short_bio") or request.brief_description,
            vibe=data.get("vibe") or request.tone,
            session_goal=data.get("session_goal")
            or "Deliver a memorable multi-turn role play.",
            key_traits=self._ensure_list(
                data.get("key_traits"), fallback=["adaptable", request.tone]
            ),
        )

        return identity, {
            "name": identity.name,
            "alias": identity.alias,
            "traits_preview": identity.key_traits[:3],
        }

    def _stage_intro(
        self,
        request: CharacterGenerationRequest,
        identity: CharacterIdentityCard,
    ) -> Tuple[CharacterIntroPack, Dict[str, Any]]:
        prompt = dedent(f"""
            We already defined this identity: {identity.model_dump_json()}.
            Create public-facing copy for onboarding a role-play partner.
            JSON schema:
            {{
                "elevator_pitch": "short stylish intro",
                "detailed_introduction": "2-3 paragraph background in first person",
                "relationship_hooks": ["why the user matters"],
                "boundaries": ["soft safety limits for scenes"],
                "conversation_openers": ["friendly starter lines"]
            }}
            """)

        data = self._invoke_json(prompt)
        intro = CharacterIntroPack(
            elevator_pitch=data.get("elevator_pitch") or identity.short_bio,
            detailed_introduction=data.get("detailed_introduction")
            or f"I'm {identity.name}, {identity.short_bio}.",
            relationship_hooks=self._ensure_list(
                data.get("relationship_hooks"),
                fallback=["We grow through shared scenes."],
            ),
            boundaries=self._ensure_list(
                data.get("boundaries"),
                fallback=["Keep content collaborative and respectful."],
            ),
            conversation_openers=self._ensure_list(
                data.get("conversation_openers"),
                fallback=[
                    f"So, ready to explore {request.genre} corners with me?"
                ],
            ),
        )

        return intro, {
            "pitch": intro.elevator_pitch,
            "hooks": intro.relationship_hooks[:2],
        }

    def _stage_roleplay_prompts(
        self,
        request: CharacterGenerationRequest,
        identity: CharacterIdentityCard,
        intro: CharacterIntroPack,
    ) -> Tuple[List[RoleplayPrompt], Dict[str, Any]]:
        desired = max(3, min(5, request.num_images or 3))
        prompt = self._roleplay_prompt_request(
            identity, intro, request, desired
        )
        data = self._invoke_json(prompt)
        prompts_raw = data.get("roleplay_prompts") or []

        if not prompts_raw:
            prompts_raw = self._fallback_roleplay_prompts(
                identity, intro, desired
            )

        prompts = self._hydrate_roleplay_prompts(
            prompts_raw, identity, request, desired
        )

        return prompts, {
            "titles": [prompt.title for prompt in prompts],
            "count": len(prompts),
        }

    def _stage_assets(
        self,
        request: CharacterGenerationRequest,
        identity: CharacterIdentityCard,
        roleplay_prompts: List[RoleplayPrompt],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        requested_images = max(3, request.num_images or 3)
        prompt = self._asset_prompt_request(
            request, identity, requested_images, roleplay_prompts
        )

        data = self._invoke_json(prompt)
        images_raw = data.get("image_prompts") or []
        audio_raw = data.get("audio_profile") or {}

        if len(images_raw) < requested_images:
            images_raw = self._fallback_image_prompts(
                identity, request, requested_images
            )

        image_prompts = self._hydrate_image_prompts(
            images_raw, identity, request, requested_images
        )

        audio_profile = self._build_audio_profile(audio_raw, identity)

        return (
            {"image_prompts": image_prompts, "audio_profile": audio_profile},
            {
                "image_titles": [img.title for img in image_prompts],
                "audio_archetype": audio_profile.archetype,
            },
        )

    # ---- Helpers ----------------------------------------------------------------

    def _invoke_json(self, prompt: str) -> Dict[str, Any]:
        return self.client.generate_structured_json(prompt)

    def _ensure_list(self, value, fallback: List[str]) -> List[str]:
        if isinstance(value, list) and value:
            return value
        if isinstance(value, str) and value:
            return [value]
        return fallback

    def _fallback_roleplay_prompts(
        self,
        identity: CharacterIdentityCard,
        intro: CharacterIntroPack,
        count: int,
    ) -> List[Dict[str, Any]]:
        prompts = []
        for idx in range(count):
            prompts.append(
                {
                    "title": f"Improv scene {idx + 1}",
                    "prompt": f"Stay in-character as {identity.name} and build upon '{intro.elevator_pitch}'.",
                    "npc_goal": identity.session_goal,
                    "player_hook": "Invite the user to co-create vivid imagery.",
                    "sample_dialogue": f'"{identity.alias}: I can feel the {identity.vibe} energy spiraling around us."',
                    "tags": ["fallback", identity.vibe],
                }
            )
        return prompts

    def _fallback_image_prompts(
        self,
        identity: CharacterIdentityCard,
        request: CharacterGenerationRequest,
        count: int,
    ) -> List[Dict[str, Any]]:
        prompts = []
        base_prompt = (
            f"{identity.name}, known as {identity.alias}, {identity.short_bio.lower()} "
            f"set within a {request.genre} ambience."
        )
        for idx in range(count):
            prompts.append(
                {
                    "title": f"{request.genre.title()} vista {idx + 1}",
                    "prompt": f"{base_prompt} Highlight trait {identity.key_traits[idx % len(identity.key_traits)]}.",
                    "style": request.image_style,
                    "camera": "Medium full shot",
                    "lighting": "Cinematic contrast",
                    "color_palette": "magenta cyan duotone",
                }
            )
        return prompts

    def _roleplay_prompt_request(
        self,
        identity: CharacterIdentityCard,
        intro: CharacterIntroPack,
        request: CharacterGenerationRequest,
        desired: int,
    ) -> str:
        return dedent(f"""
            We have identity {identity.model_dump_json()} and intro {intro.model_dump_json()}.
            Build {desired} distinct role-play prompts that keep tone "{request.tone}".
            JSON:
            {{
                "roleplay_prompts": [
                    {{
                        "title": "short name",
                        "prompt": "system style instructions for the character",
                        "npc_goal": "what the character tries to accomplish",
                        "player_hook": "how to invite the user",
                        "sample_dialogue": "first-person opening line",
                        "tags": ["mood", "genre"]
                    }}
                ]
            }}
            """)

    def _asset_prompt_request(
        self,
        request: CharacterGenerationRequest,
        identity: CharacterIdentityCard,
        requested_images: int,
        roleplay_prompts: List[RoleplayPrompt],
    ) -> str:
        scene_titles = [prompt.title for prompt in roleplay_prompts[:3]]
        return dedent(f"""
            Craft visual and audio production notes for identity {identity.model_dump_json()}.
            Use genre "{request.genre}" and tone "{request.tone}".
            Anchor visuals to these scene titles: {scene_titles}.
            Provide JSON:
            {{
                "image_prompts": [
                    {{
                        "title": "scene label",
                        "prompt": "detailed description referencing the character",
                        "style": "{request.image_style}",
                        "camera": "shot composition",
                        "lighting": "lighting notes",
                        "color_palette": "colors"
                    }}
                ],
                "audio_profile": {{
                    "archetype": "voice archetype",
                    "accent": "accent or language hint",
                    "energy": "low / medium / high",
                    "pace": "slow / neutral / upbeat",
                    "timbre": "tonal description",
                    "sample_lines": ["line a", "line b"]
                }}
            }}
            Ensure at least {requested_images} image prompts.
            """)

    def _hydrate_roleplay_prompts(
        self,
        prompts_raw: List[Dict[str, Any]],
        identity: CharacterIdentityCard,
        request: CharacterGenerationRequest,
        desired: int,
    ) -> List[RoleplayPrompt]:
        prompts: List[RoleplayPrompt] = []
        for idx, item in enumerate(prompts_raw[:desired]):
            prompts.append(
                RoleplayPrompt(
                    title=item.get("title") or f"Scene {idx + 1}",
                    prompt=item.get("prompt")
                    or f"Embody {identity.name} in a {request.genre} vignette.",
                    npc_goal=item.get("npc_goal") or identity.session_goal,
                    player_hook=item.get("player_hook")
                    or "Describe how you'd join forces.",
                    sample_dialogue=item.get("sample_dialogue")
                    or f'"{identity.alias}: Step closer, the night is still young."',
                    tags=self._ensure_list(
                        item.get("tags"), fallback=[request.tone]
                    ),
                )
            )
        return prompts

    def _hydrate_image_prompts(
        self,
        images_raw: List[Dict[str, Any]],
        identity: CharacterIdentityCard,
        request: CharacterGenerationRequest,
        requested_images: int,
    ) -> List[ImagePrompt]:
        prompts: List[ImagePrompt] = []
        for idx, item in enumerate(images_raw[:requested_images]):
            prompts.append(
                ImagePrompt(
                    title=item.get("title") or f"Visual {idx + 1}",
                    prompt=item.get("prompt")
                    or f"{identity.name} ({identity.alias}) in a {request.genre} tableau.",
                    style=item.get("style") or request.image_style,
                    camera=item.get("camera") or "Medium shot",
                    lighting=item.get("lighting") or "Soft rim lighting",
                    color_palette=item.get("color_palette")
                    or "neon blues and warm ambers",
                )
            )
        return prompts

    def _build_audio_profile(
        self, audio_raw: Dict[str, Any], identity: CharacterIdentityCard
    ) -> AudioProfile:
        return AudioProfile(
            archetype=audio_raw.get("archetype")
            or f"{identity.vibe.title()} confidante",
            accent=audio_raw.get("accent") or "Neutral global English",
            energy=audio_raw.get("energy") or "medium",
            pace=audio_raw.get("pace") or "measured",
            timbre=audio_raw.get("timbre") or "velvety with playful edges",
            sample_lines=self._ensure_list(
                audio_raw.get("sample_lines"),
                fallback=[
                    "Take a breath, I've got the next move handled.",
                    "Tell me what you crave and I'll improvise the rest.",
                ],
            ),
        )
