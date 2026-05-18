from __future__ import annotations

import json
from pathlib import Path

import pytest

from experimental.agentic_ai_companion.chat_image_gen import (
    CompanionProfile,
    GenerateImageToolInput,
    RuntimePaths,
    UserProfile,
    build_chat_image_prompt,
    generate_image_with_chat_to_image_behavior,
    select_reference_images,
)
from experimental.agentic_ai_companion.tools import execute_generate_image


def _minimal_png_bytes(width: int = 32, height: int = 24) -> bytes:
    # 仅用于单元测试，构造一个最小可识别 PNG 头。
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )
    ihdr = (
        len(ihdr_data).to_bytes(4, "big")
        + b"IHDR"
        + ihdr_data
        + b"\x00\x00\x00\x00"
    )
    iend = b"\x00\x00\x00\x00IEND\xaeB`\x82"
    return signature + ihdr + iend


class _FakeInlineData:
    def __init__(self, data: bytes) -> None:
        self.data = data


class _FakePart:
    def __init__(self, data: bytes) -> None:
        self.inline_data = _FakeInlineData(data)
        self.text = None


class _FakeContent:
    def __init__(self, data: bytes) -> None:
        self.parts = [_FakePart(data)]


class _FakeCandidate:
    def __init__(self, data: bytes) -> None:
        self.content = _FakeContent(data)


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self.candidates = [_FakeCandidate(data)]


class _FakeModels:
    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = outcomes
        self.calls: list[str] = []

    def generate_content(self, *, model, contents, config):
        self.calls.append(model)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _FakeClient:
    def __init__(self, outcomes: list[object]) -> None:
        self.models = _FakeModels(outcomes)


def _write_dummy_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_minimal_png_bytes())


def test_build_chat_image_prompt_contains_rendered_profile_and_history():
    companion_profile = CompanionProfile(
        personality="{{ char }} is warm and playful with {{ user }}.",
        scenario="{{ char }} and {{ user }} are in a cozy room.",
    )
    prompt = build_chat_image_prompt(
        companion_profile=companion_profile,
        chat_history=[
            {"role": "user", "content": "Hold me tighter."},
            {"role": "assistant", "content": "I smile and move closer."},
        ],
        scene_description="We are fantasizing about a romantic night.",
        user_info="##User Information\nName: Alex",
        char_name="Sophie",
        user_name="Alex",
    )
    assert "Sophie is warm and playful with Alex." in prompt
    assert "User: Hold me tighter." in prompt
    assert "Assistant: I smile and move closer." in prompt
    assert "Name: Alex" in prompt


def test_select_reference_images_resolves_profile_paths(tmp_path: Path):
    companion_dir = tmp_path / "companion_profile"
    user_dir = tmp_path / "user_profile"
    companion_avatar = companion_dir / "avatar.png"
    user_avatar = user_dir / "avatar.png"
    _write_dummy_image(companion_avatar)
    _write_dummy_image(user_avatar)

    runtime_paths = RuntimePaths(
        companion_profile_dir=companion_dir,
        user_profile_dir=user_dir,
        output_dir=tmp_path / "out",
        history_index_path=tmp_path / "history.json",
    )
    input_data = GenerateImageToolInput(
        scene_description="romantic scene",
        messages=[],
        runtime_paths=runtime_paths,
    )
    selection = select_reference_images(
        input_data=input_data,
        companion_profile=CompanionProfile(),
        user_profile=UserProfile(),
    )
    assert selection.ai_reference_image_path == str(companion_avatar.resolve())
    assert selection.user_reference_image_path == str(user_avatar.resolve())
    assert selection.only_include_ai_character is False


def test_generate_image_raises_on_429_without_model_fallback(tmp_path: Path):
    companion_dir = tmp_path / "companion_profile"
    user_dir = tmp_path / "user_profile"
    _write_dummy_image(companion_dir / "avatar.png")
    _write_dummy_image(user_dir / "avatar.png")

    runtime_paths = RuntimePaths(
        companion_profile_dir=companion_dir,
        user_profile_dir=user_dir,
        output_dir=tmp_path / "out",
        history_index_path=tmp_path / "history.json",
    )
    fake_client = _FakeClient(
        outcomes=[
            RuntimeError("429 RESOURCE_EXHAUSTED"),
        ]
    )

    with pytest.raises(RuntimeError, match="429 RESOURCE_EXHAUSTED"):
        generate_image_with_chat_to_image_behavior(
            client=fake_client,
            input_data=GenerateImageToolInput(
                scene_description="romantic role-play scene",
                messages=[
                    {"role": "user", "content": "Show us in a warm embrace."}
                ],
                runtime_paths=runtime_paths,
                model="gemini-3-pro-image-preview",
            ),
        )
    assert fake_client.models.calls == ["gemini-3-pro-image-preview"]


def test_generate_image_raises_when_generation_fails_without_similarity_fallback(
    tmp_path: Path,
):
    companion_dir = tmp_path / "companion_profile"
    user_dir = tmp_path / "user_profile"
    _write_dummy_image(companion_dir / "avatar.png")
    _write_dummy_image(user_dir / "avatar.png")

    runtime_paths = RuntimePaths(
        companion_profile_dir=companion_dir,
        user_profile_dir=user_dir,
        output_dir=tmp_path / "out",
        history_index_path=tmp_path / "history.json",
    )
    fake_client = _FakeClient(outcomes=[RuntimeError("network timeout")])
    with pytest.raises(RuntimeError, match="network timeout"):
        generate_image_with_chat_to_image_behavior(
            client=fake_client,
            input_data=GenerateImageToolInput(
                scene_description="Create a romantic embrace in a candle-lit room.",
                messages=[
                    {"role": "user", "content": "Please make it romantic."}
                ],
                runtime_paths=runtime_paths,
            ),
        )


def test_execute_generate_image_returns_tool_message_and_path(tmp_path: Path):
    companion_dir = tmp_path / "companion_profile"
    user_dir = tmp_path / "user_profile"
    _write_dummy_image(companion_dir / "avatar.png")
    _write_dummy_image(user_dir / "avatar.png")

    # tools.execute_generate_image 内部会使用默认 runtime 路径，这里通过 profile.json 指向临时目录。
    (companion_dir / "profile.json").write_text(
        json.dumps({"reference_image": "avatar.png"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (user_dir / "profile.json").write_text(
        json.dumps({"reference_image": "avatar.png"}, ensure_ascii=False),
        encoding="utf-8",
    )

    fake_client = _FakeClient(
        outcomes=[_FakeResponse(_minimal_png_bytes(50, 40))]
    )
    message, image_path = execute_generate_image(
        messages=[
            {"role": "user", "content": "Generate a romantic image for us."}
        ],
        client=fake_client,
        input="romantic role-play in a warm room",
        ai_reference_image=str((companion_dir / "avatar.png").resolve()),
        user_reference_image=str((user_dir / "avatar.png").resolve()),
    )
    assert image_path is not None
    assert Path(image_path).exists()
    assert "metadata=" in message
