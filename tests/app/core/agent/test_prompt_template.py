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


def test_render_prompt_jinja2_template_extra_context():
    rendered_prompt = prompt_template.render_prompt_jinja2_template(
        "Manual: {{ intellimate_user_manual }}",
        "Agent",
        "User",
        extra_context={"intellimate_user_manual": "MANUAL"},
    )
    assert rendered_prompt == "Manual: MANUAL"
