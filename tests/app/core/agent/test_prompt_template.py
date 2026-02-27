from app.core.agent import prompt_template


def test_render_prompt_jinja2_template():
    rendered_prompt = prompt_template.render_prompt_jinja2_template(
        "{{ char }} and {{ user }}",
        "Agent",
        "User",
    )
    assert rendered_prompt == "Agent and User"


def test_render_prompt_jinja2_template_empty_template():
    rendered_prompt = prompt_template.render_prompt_jinja2_template(
        "",
        "Agent",
        "User",
    )
    assert rendered_prompt == ""


def test_render_prompt_jinja2_template_with_extra_kwargs():
    """Extra variables via kwargs are rendered (e.g. foundational_goal, max_words)."""
    tmpl = (
        "You are {{ char }}. Your goal: {{ foundational_goal }}. "
        "Each reply must not exceed {{ max_words }} words."
    )
    rendered = prompt_template.render_prompt_jinja2_template(
        tmpl,
        char="Alice",
        user="Bob",
        foundational_goal="create an engaging conversation",
        max_words="80",
    )
    assert "You are Alice." in rendered
    assert "Your goal: create an engaging conversation." in rendered
    assert "must not exceed 80 words." in rendered


def test_render_prompt_jinja2_template_extra_kwargs_only():
    """Template with only extra kwargs (no char/user) still renders correctly."""
    rendered = prompt_template.render_prompt_jinja2_template(
        "Limit: {{ max_words }} words.",
        char="X",
        user="Y",
        max_words="100",
    )
    assert rendered == "Limit: 100 words."
