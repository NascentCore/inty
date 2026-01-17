from jinja2 import Template as Jinja2Template


def render_prompt_jinja2_template(
    tmpl: str,
    char: str,
    user: str | None,
    extra_context: dict[str, str] | None = None,
) -> str:
    """Render Jinja2 template for prompt with standard context."""
    context = {"char": char, "user": user}
    if extra_context:
        context.update(extra_context)
    jinja2_template = Jinja2Template(tmpl)
    rendered_prompt = jinja2_template.render(**context)
    return rendered_prompt


def has_template_variable(tmpl: str) -> bool:
    """Check if the template has variable name"""
    return "{{" in tmpl and "}}" in tmpl
