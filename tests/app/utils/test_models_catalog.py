"""Tests for models_catalog resolve_nickname, must_resolve_nickname, resolve_id_on_provider and CHAT_IMAGE_GEN_MODELS."""

from types import SimpleNamespace

import pytest

from app.utils.models_catalog import (
    ALL_GENAI_CATALOG_MODELS,
    CHAT_IMAGE_FAL_IDS,
    CHAT_IMAGE_FAL_MODELS,
    DEEPSEEK_V3_2,
    IMAGEN_4_FAST,
    ModelNameFamily,
    NANO_BANANA,
    NANO_BANANA_2,
    NANO_BANANA_PRO,
    NEWAPI_NANO_BANANA_2,
    SEEDREAM_V4_5_EDIT,
    Z_IMAGE_TURBO_IMAGE_TO_IMAGE,
    detect_model_name_family,
    is_fal_model,
    is_gemini_model,
    must_resolve_nickname,
    normalize_model_name,
    prompt_tokens_context_utilization,
    resolve_catalog_genai_model,
    resolve_id_on_provider,
    resolve_nickname,
)


def test_resolve_nickname_valid_nicknames():
    """允许的 nickname 返回对应的 GenAIModel。"""
    assert resolve_nickname("Nano Banana") is NANO_BANANA
    assert resolve_nickname("Nano Banana 2") is NANO_BANANA_2
    assert resolve_nickname("Nano Banana Pro") is NANO_BANANA_PRO
    assert resolve_nickname("NewAPI Nano Banana 2") is NEWAPI_NANO_BANANA_2
    assert resolve_nickname("Seedream V4.5 Edit") is SEEDREAM_V4_5_EDIT
    assert resolve_nickname("Z Image Turbo Image to Image") is Z_IMAGE_TURBO_IMAGE_TO_IMAGE


def test_resolve_nickname_returns_id_on_provider():
    """返回的 GenAIModel 可访问 id_on_provider。"""
    model = resolve_nickname("Nano Banana")
    assert model.id_on_provider == NANO_BANANA.id_on_provider
    assert model.id_on_provider == "gemini-2.5-flash-image"


def test_resolve_nickname_unknown_returns_none():
    """未知 nickname 返回 None。"""
    assert resolve_nickname("Unknown Model") is None


def test_must_resolve_nickname_unknown_raises():
    """must_resolve_nickname 对未知 nickname 抛出 ValueError。"""
    with pytest.raises(ValueError) as exc_info:
        must_resolve_nickname("Unknown Model")
    assert "Unknown Model" in str(exc_info.value)
    assert "not allowed" in str(exc_info.value)


def test_resolve_nickname_disallowed_catalog_model_returns_none():
    """不在 CHAT_IMAGE_GEN_MODELS 中的 catalog 模型 nickname 返回 None。"""
    assert resolve_nickname("Imagen 4.0 Fast") is None


def test_resolve_id_on_provider_valid():
    """允许的 id_on_provider 返回对应的 GenAIModel。"""
    assert resolve_id_on_provider(NANO_BANANA.id_on_provider) is NANO_BANANA
    assert resolve_id_on_provider(SEEDREAM_V4_5_EDIT.id_on_provider) is SEEDREAM_V4_5_EDIT


def test_resolve_id_on_provider_unknown_returns_none():
    """未知的 id_on_provider 返回 None。"""
    assert resolve_id_on_provider("unknown-provider-id") is None


def test_chat_image_fal_ids_matches_fal_models():
    """CHAT_IMAGE_FAL_IDS 与 CHAT_IMAGE_FAL_MODELS 的 id_on_provider 一致。"""
    assert CHAT_IMAGE_FAL_IDS == tuple(m.id_on_provider for m in CHAT_IMAGE_FAL_MODELS)
    assert set(CHAT_IMAGE_FAL_IDS) == {
        SEEDREAM_V4_5_EDIT.id_on_provider,
        Z_IMAGE_TURBO_IMAGE_TO_IMAGE.id_on_provider,
    }


def test_normalize_model_name_supports_fal_alias():
    """fal/<id> 会被规范化为 fal-ai/<id>。"""
    assert normalize_model_name("fal/z-image/turbo") == "fal-ai/z-image/turbo"
    assert normalize_model_name("  FAL/Z-IMAGE/TURBO  ") == "fal-ai/z-image/turbo"


def test_detect_model_name_family_fal():
    """fal 系列模型应识别为 FAL。"""
    assert detect_model_name_family("fal-ai/z-image/turbo") == ModelNameFamily.FAL
    assert detect_model_name_family("fal/z-image/turbo") == ModelNameFamily.FAL
    assert detect_model_name_family(SEEDREAM_V4_5_EDIT.nickname) == ModelNameFamily.FAL
    assert is_fal_model("fal/z-image/turbo") is True


def test_detect_model_name_family_gemini():
    """gemini 系列模型应识别为 GEMINI。"""
    assert detect_model_name_family("gemini-2.5-flash-image") == ModelNameFamily.GEMINI
    assert (
        detect_model_name_family("google/gemini-2.5-flash-image")
        == ModelNameFamily.GEMINI
    )
    assert detect_model_name_family(NANO_BANANA.nickname) == ModelNameFamily.GEMINI
    assert is_gemini_model("google/gemini-2.5-flash-image") is True


def test_detect_model_name_family_other():
    """非 fal/gemini 模型归类为 OTHER。"""
    assert detect_model_name_family("google/imagen-4.0-fast-generate-001") == ModelNameFamily.OTHER
    assert detect_model_name_family("openai/gpt-image-1") == ModelNameFamily.OTHER
    assert detect_model_name_family("unknown-model") == ModelNameFamily.OTHER


def test_all_genai_catalog_models_deduped_count():
    """ALL_GENAI_CATALOG_MODELS 去重后长度与唯一对象数一致（与目录常量总数对齐）。"""
    assert len(ALL_GENAI_CATALOG_MODELS) == 28
    assert len({id(m) for m in ALL_GENAI_CATALOG_MODELS}) == len(ALL_GENAI_CATALOG_MODELS)


def test_resolve_catalog_genai_model_by_id_and_nickname():
    """resolve_catalog_genai_model 支持 id、nickname、fal 别名。"""
    assert resolve_catalog_genai_model("deepseek/deepseek-v3.2") is DEEPSEEK_V3_2
    assert resolve_catalog_genai_model("Gemini 2.5 Flash") is not None
    assert resolve_catalog_genai_model("fal/z-image/turbo") is not None
    assert resolve_catalog_genai_model("fal/z-image/turbo").id_on_provider == "fal-ai/z-image/turbo"
    assert resolve_catalog_genai_model("unknown/custom") is None


def test_prompt_tokens_context_utilization():
    """prompt / 目录窗口比率；窗口为 0 或未知模型返回 None。"""
    r = prompt_tokens_context_utilization(
        model="deepseek/deepseek-v3.2", prompt_tokens=163_840
    )
    assert r is not None and abs(r - 1.0) < 1e-9
    assert prompt_tokens_context_utilization(model="deepseek/deepseek-v3.2", prompt_tokens=None) is None
    assert (
        prompt_tokens_context_utilization(
            model=IMAGEN_4_FAST.id_on_provider, prompt_tokens=100
        )
        is None
    )
    assert NANO_BANANA_2.context_window_tokens == 200_000
    assert (
        prompt_tokens_context_utilization(
            model=NANO_BANANA_2.id_on_provider, prompt_tokens=100_000
        )
        == 0.5
    )


def test_runtime_inspect_merge_last_chat_completion_usage():
    """runtime_inspect_merge_last_chat_completion_usage 写入 response_usage 与比率。"""
    from app.core.companion_harness.tools.runtime_inspect_context import (
        runtime_inspect_begin_turn,
        runtime_inspect_end_turn,
        runtime_inspect_get_bundle,
        runtime_inspect_merge_last_chat_completion_usage,
        runtime_inspect_set_last_chat_completion_request,
    )

    tok = runtime_inspect_begin_turn()
    try:
        runtime_inspect_set_last_chat_completion_request(
            {"model": "deepseek/deepseek-v3.2", "messages": []}
        )
        resp = SimpleNamespace(
            usage=SimpleNamespace(
                prompt_tokens=81_920,
                completion_tokens=128,
                total_tokens=82_048,
            )
        )
        runtime_inspect_merge_last_chat_completion_usage("deepseek/deepseek-v3.2", resp)
        bundle = runtime_inspect_get_bundle()
        assert bundle is not None
        last = bundle["last_chat_completion_request"]
        assert last["response_usage"]["prompt_tokens"] == 81_920
        assert last["catalog_context_window_tokens"] == DEEPSEEK_V3_2.context_window_tokens
        assert abs(last["prompt_to_context_window_ratio"] - (81_920 / 163_840)) < 1e-9
    finally:
        runtime_inspect_end_turn(tok)
