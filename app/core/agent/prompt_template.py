from jinja2 import Template as Jinja2Template


def render_prompt_jinja2_template(tmpl: str, char: str, user: str) -> str:
    """Render Jinja2 template for prompt, which has {{ char }} and {{ user }}"""
    jinja2_template = Jinja2Template(tmpl)
    rendered_prompt = jinja2_template.render(char=char, user=user)
    return rendered_prompt
