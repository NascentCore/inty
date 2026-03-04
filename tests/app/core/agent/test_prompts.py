from app.core.agent.prompts import (
    AVAILABLE_MAIN_PROMPTS,
    AVAILABLE_MODE_PROMPTS,
    _load_prompts_data,
    get_main_prompt_by_id,
    get_mode_prompt_by_id,
)


def test_prompts_data_yaml_comments_not_in_loaded_values():
    """
    验证 prompts_data.yaml 中的注释不会被读入代码：
    _load_prompts_data() 使用 yaml.safe_load，解析后的字符串不应包含 YAML 注释内容。
    """
    data = _load_prompts_data()
    comment_substring = "这一句要做调整"
    for key, value in data.items():
        assert isinstance(value, str), f"Prompt {key!r} must be str"
        assert comment_substring not in value, (
            f"YAML comment content {comment_substring!r} must not appear in loaded prompt {key!r}"
        )


def test_ai_companion_placeholder_presets_are_available_and_resolvable():
    main_prompt = next((p for p in AVAILABLE_MAIN_PROMPTS if p.id == "ai_companion_main"), None)
    mode_prompt = next((p for p in AVAILABLE_MODE_PROMPTS if p.id == "ai_companion_mode"), None)

    assert main_prompt is not None
    assert mode_prompt is not None
    assert main_prompt.name == "AI companion"
    assert mode_prompt.name == "AI companion"
    assert get_main_prompt_by_id("ai_companion_main").strip() == "AI companion"
    assert get_mode_prompt_by_id("ai_companion_mode").strip() == "AI companion"
