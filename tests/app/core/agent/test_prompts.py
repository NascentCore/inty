from app.core.agent.prompts import (
    AVAILABLE_MAIN_PROMPTS,
    AVAILABLE_MODE_PROMPTS,
    _load_prompts_data,
    get_main_prompt_by_id,
    get_mode_output_format_prompt_by_id,
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
        assert (
            comment_substring not in value
        ), f"YAML comment content {comment_substring!r} must not appear in loaded prompt {key!r}"


def test_get_mode_output_format_prompt_by_id():
    mode_ids = {prompt.id for prompt in AVAILABLE_MODE_PROMPTS}
    assert "purity_mode_0725" in mode_ids
    assert "flirting_mode_20250902" in mode_ids

    purity_output_format_prompt = get_mode_output_format_prompt_by_id(
        "purity_mode_0725"
    )
    assert "D. Output Format" in purity_output_format_prompt

    flirting_output_format_prompt = get_mode_output_format_prompt_by_id(
        "flirting_mode_20250902"
    )
    assert (
        "All dialogues must be enclosed in quotation marks"
        in flirting_output_format_prompt
    )
