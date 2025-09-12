from app.core.prompting.prompting import SystemPromptingMode, pick_prompt


def test_pick_prompt():
    assert pick_prompt(SystemPromptingMode.STATIC, "default", "configured", "override") == "configured"
    assert pick_prompt(SystemPromptingMode.FILL_MISSING, "default", "configured", "override") == "configured"
    assert pick_prompt(SystemPromptingMode.FILL_MISSING, "default", None, "override") == "default"
    assert pick_prompt(SystemPromptingMode.OVERRIDE, "default", "configured", "override") == "override"
    assert pick_prompt(SystemPromptingMode.OVERRIDE, "default", "configured", None) == "configured"
    assert pick_prompt(SystemPromptingMode.OVERRIDE, "default", None, None) == "default"
