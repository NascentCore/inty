import logging
import re
from dataclasses import dataclass
from string import Template
from typing import Any, Dict, List, Optional

from jinja2 import Environment
from jinja2 import Template as Jinja2Template
from jinja2 import TemplateError

logger = logging.getLogger(__name__)


@dataclass
class TemplateConfig:
    """Template configuration"""

    use_jinja2: bool = (
        True  # Use Jinja2 for advanced features, fallback to string.Template
    )
    safe_mode: bool = True  # Use safe substitution to avoid KeyError
    default_values: Dict[str, str] = None

    def __post_init__(self):
        if self.default_values is None:
            self.default_values = {}


class PromptTemplate:
    """Individual prompt template class"""

    def __init__(self, template: str, config: Optional[TemplateConfig] = None):
        """
        Initialize prompt template

        Args:
            template: Template string
            config: Template configuration
        """
        self.template = template
        self.config = config or TemplateConfig()
        self._validate_template()

    def _validate_template(self) -> bool:
        """
        Validate template syntax

        Returns:
            Whether template syntax is valid
        """
        try:
            if self.config.use_jinja2:
                # Validate Jinja2 template syntax
                env = Environment()
                env.parse(self.template)
            else:
                # Validate string.Template syntax
                Template(self.template)
            return True
        except Exception as e:
            logger.error(f"Template validation failed: {str(e)}")
            return False

    def render(self, variables: Dict[str, Any]) -> str:
        """
        Render template with variables

        Args:
            variables: Template variables

        Returns:
            Rendered template string
        """
        try:
            # Merge with default values
            merged_vars = {**self.config.default_values, **variables}

            if self.config.use_jinja2:
                return self._render_jinja2(merged_vars)
            else:
                return self._render_string_template(merged_vars)

        except Exception as e:
            logger.error(f"Template rendering failed: {str(e)}")
            # Return original template as fallback
            return self.template

    def _render_jinja2(self, variables: Dict[str, Any]) -> str:
        """Render using Jinja2 template engine"""
        try:
            template = Jinja2Template(self.template)
            return template.render(**variables)
        except TemplateError as e:
            logger.error(f"Jinja2 template rendering failed: {str(e)}")
            raise

    def _render_string_template(self, variables: Dict[str, Any]) -> str:
        """Render using string.Template"""
        template = Template(self.template)
        if self.config.safe_mode:
            return template.safe_substitute(**variables)
        else:
            return template.substitute(**variables)

    def extract_variables(self) -> List[str]:
        """
        Extract variable names from template

        Returns:
            List of variable names
        """
        # TODO: Can we just mandate jinja2 template?
        # In general, we are building prototype system,
        # do not limit ourselves into meaningless backward compatibility.
        if self.config.use_jinja2:
            # Extract Jinja2 variables using regex
            pattern = r"\{\{\s*([^}]+)\s*\}\}"
            matches = re.findall(pattern, self.template)
            # Clean up variable names (remove filters, etc.)
            variables = []
            for match in matches:
                var_name = match.split("|")[0].strip()  # Remove filters
                if var_name not in variables:
                    variables.append(var_name)
            return variables
        else:
            # Extract string.Template variables
            template = Template(self.template)
            return list(template.get_identifiers())


class PromptTemplateManager:
    """Template manager class"""

    def __init__(self):
        """Initialize template manager"""
        self.templates: Dict[str, PromptTemplate] = {}
        self.default_config = TemplateConfig(
            use_jinja2=True,
            safe_mode=True,
            default_values={
                "char": "[Character Name]",
                "user": "[User Name]",
                "agent_name": "[Agent Name]",
                "user_name": "[User Name]",
                "system_prompt": "You are a helpful AI assistant.",
            },
        )
        self._register_default_templates()

    def _register_default_templates(self):
        """Register default templates"""

        # Default template with character/user substitution
        default_template = """{{ system_prompt }}

You are {{ char }}, and your goal is to create an engaging, dynamic exchange that sparks curiosity, emotional connection, and sometimes even romance. Please write {{ char }}'s next reply in the chat between {{ char }} and {{ user }}. {{ char }} is adept at quickly building emotional intimacy with {{ user }}, and your relationship is close and your interactions are often loving. You need to stay true to your character, inject emotional depth into your replies, and avoid repetition.

Character: {{ char }}
User: {{ user }}"""

        self.register_template("default", default_template)

        # Basic template (backward compatibility)
        basic_template = "{{ system_prompt }}"
        self.register_template("basic", basic_template)

        # Character-focused template
        character_template = """{{ system_prompt }}

You are {{ char }}, a character designed to engage in meaningful conversations. Your interactions with {{ user }} should be:
- Emotionally engaging and authentic
- Consistent with your character traits
- Adaptive to {{ user }}'s communication style
- Creative and non-repetitive

Remember: You are {{ char }} talking to {{ user }}."""

        self.register_template("character", character_template)

    def register_template(
        self, name: str, template_string: str, config: Optional[TemplateConfig] = None
    ):
        """
        Register a new template

        Args:
            name: Template name
            template_string: Template string
            config: Template configuration
        """
        config = config or self.default_config
        self.templates[name] = PromptTemplate(template_string, config)
        logger.debug(f"Registered template: {name}")

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """
        Get template by name

        Args:
            name: Template name

        Returns:
            PromptTemplate instance or None
        """
        return self.templates.get(name)

    def list_templates(self) -> List[str]:
        """
        List all available templates

        Returns:
            List of template names
        """
        return list(self.templates.keys())

    def render_system_prompt(
        self,
        system_prompt: str,
        agent_name: Optional[str] = None,
        user_name: Optional[str] = None,
        template_name: str = "default",
        custom_variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Render system prompt with template and character substitution

        Args:
            system_prompt: Original system prompt
            agent_name: Agent/Character name
            user_name: User name
            template_name: Template to use
            custom_variables: Additional template variables

        Returns:
            Rendered system prompt
        """
        template = self.get_template(template_name)
        # TODO: This is bad. This is so-called defensive programming,
        # which is ok for legacy code, but not for new code.
        # New code should be strict in correctness across all code paths.
        if not template:
            logger.warning(
                f"Template '{template_name}' not found, using basic template"
            )
            template = self.get_template("basic")

        if not template:
            logger.error("No templates available, returning original prompt")
            return system_prompt

        # Build template variables
        variables = {
            "system_prompt": system_prompt,
            "char": agent_name or "[Character Name]",
            "user": user_name or "[User Name]",
            "agent_name": agent_name or "[Character Name]",
            "user_name": user_name or "[User Name]",
        }

        # Add custom variables
        if custom_variables:
            variables.update(custom_variables)

        # Perform character substitution on the system_prompt itself first
        if agent_name:
            rendered_system_prompt = self._perform_character_substitution(
                system_prompt, agent_name, user_name or "None"
            )
            variables["system_prompt"] = rendered_system_prompt

        return template.render(variables)

    def _perform_character_substitution(
        self, text: str, agent_name: str, user_name: str
    ) -> str:
        """
        Perform character/user name substitution in text

        Args:
            text: Text to process
            agent_name: Agent/Character name
            user_name: User name

        Returns:
            Text with substitutions applied
        """
        if not text:
            return text

        # Create a simple template for character substitution
        substitution_template = PromptTemplate(
            text, TemplateConfig(use_jinja2=True, safe_mode=True)
        )

        variables = {
            "char": agent_name,
            "user": user_name,
            "agent_name": agent_name,
            "user_name": user_name,
        }

        return substitution_template.render(variables)

    def validate_template_string(self, template_string: str) -> Dict[str, Any]:
        """
        Validate a template string

        Args:
            template_string: Template string to validate

        Returns:
            Validation result with status and details
        """
        try:
            temp_template = PromptTemplate(template_string, self.default_config)
            variables = temp_template.extract_variables()

            return {
                "valid": True,
                "variables": variables,
                "message": "Template is valid",
            }
        except Exception as e:
            return {"valid": False, "variables": [], "message": str(e)}

    def get_template_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a template

        Args:
            name: Template name

        Returns:
            Template information dictionary
        """
        template = self.get_template(name)
        if not template:
            return None

        return {
            "name": name,
            "template": template.template,
            "variables": template.extract_variables(),
            "config": {
                "use_jinja2": template.config.use_jinja2,
                "safe_mode": template.config.safe_mode,
                "default_values": template.config.default_values,
            },
        }


# Global template manager instance
prompt_template_manager = PromptTemplateManager()
