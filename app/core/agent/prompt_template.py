from typing import Dict, Any, Optional
from string import Template
import logging

logger = logging.getLogger(__name__)

class PromptTemplate:
    """
    提示词模版类，支持字符串模版化
    """
    
    # 默认的系统要求提示词模版
    DEFAULT_SYSTEM_TEMPLATE = """$system_prompt

You are a virtual character created by the user. You must engage in conversation with the user entirely as a human, without revealing any information about being an AI, a large model, or a virtual assistant.
"""

    def __init__(self, template: Optional[str] = None):
        """
        初始化提示词模版
        
        Args:
            template: 自定义模版字符串，如果为None则使用默认模版
        """
        self.template = template or self.DEFAULT_SYSTEM_TEMPLATE
        self._compiled_template = Template(self.template)

    def render(self, **kwargs) -> str:
        """
        渲染模版，替换变量
        
        Args:
            **kwargs: 模版变量字典
            
        Returns:
            渲染后的字符串
        """
        try:
            # 提供默认值
            default_values = {
                'system_prompt': kwargs.get('system_prompt', '你是一个聊天助手，请用中文回答用户的问题。'),
                'agent_name': kwargs.get('agent_name', ''),
                'agent_description': kwargs.get('agent_description', ''),
                'additional_instructions': kwargs.get('additional_instructions', ''),
            }
            
            # 合并用户提供的值和默认值
            render_values = {**default_values, **kwargs}
            
            # 使用safe_substitute避免KeyError
            rendered = self._compiled_template.safe_substitute(**render_values)
            
            logger.debug(f"提示词模版渲染完成, 变量数量: {len(render_values)}")
            return rendered
            
        except Exception as e:
            logger.error(f"提示词模版渲染失败: {str(e)}")
            # 如果模版渲染失败，返回基础的提示词
            return kwargs.get('system_prompt', '你是一个聊天助手，请用中文回答用户的问题。')

    def get_template_variables(self) -> list[str]:
        """
        获取模版中的变量名列表
        
        Returns:
            变量名列表
        """
        try:
            # 从模版中提取变量名
            import re
            pattern = r'\$([a-zA-Z_][a-zA-Z0-9_]*)'
            variables = re.findall(pattern, self.template)
            return list(set(variables))  # 去重
        except Exception as e:
            logger.error(f"获取模版变量失败: {str(e)}")
            return []

    def validate_template(self) -> bool:
        """
        验证模版是否有效
        
        Returns:
            True if valid, False otherwise
        """
        try:
            # 尝试用空值渲染模版
            test_values = {var: '' for var in self.get_template_variables()}
            self._compiled_template.safe_substitute(**test_values)
            return True
        except Exception as e:
            logger.error(f"模版验证失败: {str(e)}")
            return False

    @classmethod
    def create_custom_template(cls, template: str) -> 'PromptTemplate':
        """
        创建自定义模版
        
        Args:
            template: 自定义模版字符串
            
        Returns:
            PromptTemplate实例
        """
        return cls(template=template)

    @classmethod
    def get_default_template(cls) -> 'PromptTemplate':
        """
        获取默认模版
        
        Returns:
            使用默认模版的PromptTemplate实例
        """
        return cls()


class PromptTemplateManager:
    """
    提示词模版管理器
    """
    
    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._register_default_templates()

    def _register_default_templates(self):
        """注册默认的提示词模版"""
        # 注册默认的系统模版
        self._templates['default'] = PromptTemplate.get_default_template()
        
        # 可以添加更多预定义的模版
        # self._templates['simple'] = PromptTemplate.create_custom_template("$system_prompt")
        # self._templates['detailed'] = PromptTemplate.create_custom_template("详细的模版内容...")

    def get_template(self, template_name: str = 'default') -> PromptTemplate:
        """
        获取指定名称的模版
        
        Args:
            template_name: 模版名称
            
        Returns:
            PromptTemplate实例
        """
        return self._templates.get(template_name, self._templates['default'])

    def register_template(self, name: str, template: PromptTemplate):
        """
        注册新的模版
        
        Args:
            name: 模版名称
            template: PromptTemplate实例
        """
        self._templates[name] = template
        logger.info(f"注册提示词模版: {name}")

    def list_templates(self) -> list[str]:
        """
        列出所有可用的模版名称
        
        Returns:
            模版名称列表
        """
        return list(self._templates.keys())

    def render_prompt(self, agent_data: Dict[str, Any], template_name: str = 'default') -> str:
        """
        渲染指定模版的提示词
        
        Args:
            agent_data: Agent数据字典
            template_name: 模版名称
            
        Returns:
            渲染后的提示词
        """
        template = self.get_template(template_name)
        
        # 优先使用角色卡字段构建系统提示词
        system_prompt = self._build_system_prompt_from_character_card(agent_data)
        
        # 如果角色卡字段为空，回退到原始prompt字段
        if not system_prompt:
            system_prompt = agent_data.get('prompt', '你是一个聊天助手，请用中文回答用户的问题。')
        
        agent_name = agent_data.get('name', '')
        agent_description = agent_data.get('description', '')
        
        # 渲染提示词
        return template.render(
            system_prompt=system_prompt,
            agent_name=agent_name,
            agent_description=agent_description
        )
    
    def _build_system_prompt_from_character_card(self, agent_data: Dict[str, Any]) -> str:
        """
        从角色卡字段构建系统提示词
        
        Args:
            agent_data: Agent数据字典
            
        Returns:
            构建的系统提示词，如果角色卡字段为空则返回空字符串
        """
        personality = agent_data.get('personality', '').strip()
        scenario = agent_data.get('scenario', '').strip()
        
        # 如果没有角色卡信息，返回空字符串
        if not personality and not scenario:
            return ''
        
        # 构建系统提示词
        prompt_parts = []
        
        if personality:
            prompt_parts.append(f"角色性格: {personality}")
        
        if scenario:
            prompt_parts.append(f"背景设定: {scenario}")
        
        # 添加基础行为指令
        base_instruction = "你是一个虚拟角色，请完全按照上述设定与用户对话，不要透露你是AI的身份。"
        prompt_parts.append(base_instruction)
        
        return '\n\n'.join(prompt_parts)


# 全局提示词模版管理器实例
prompt_template_manager = PromptTemplateManager() 