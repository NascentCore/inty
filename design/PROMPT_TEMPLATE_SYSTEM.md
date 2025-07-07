# 提示词模版系统

## 概述

为了提升提示词管理的灵活性和可维护性，我们将原有的直接字符串拼接方式改为模版化处理。

## 主要改进

### 1. 模版化处理

- 使用 `string.Template` 进行模版化处理
- 支持变量替换和默认值
- 提供模版验证功能

### 2. 系统架构

#### 核心组件

1. **PromptTemplate** - 单个提示词模版类
2. **PromptTemplateManager** - 模版管理器
3. **Agent** - 修改后的 Agent 类，使用模版系统

#### 文件结构

```
app/core/agent/
├── prompt_template.py  # 新增：提示词模版系统
├── agent.py            # 修改：使用模版系统
└── ...
```

## 使用方法

### 1. 基本用法

```python
from app.core.agent.prompt_template import prompt_template_manager

# 渲染提示词
agent_data = {
    'name': 'AI助手',
    'prompt': '你是一个友好的AI助手',
    'description': '专业的客服机器人'
}

final_prompt = prompt_template_manager.render_prompt(agent_data)
```

### 2. 创建 Agent 实例

```python
from app.core.agent.agent import Agent

agent = Agent(
    agent_id='test_agent',
    name='测试Agent',
    model_config={...},
    system_prompt='你是一个测试Agent',
    description='这是一个测试用的Agent',
    template_name='default'  # 指定使用的模版
)
```

### 3. 获取最终提示词

```python
# 获取最终渲染的提示词
final_prompt = agent.get_final_prompt()

# 获取模版信息
template_info = agent.get_template_info()
```

## API 接口

### 1. 获取 Agent 提示词

```
GET /api/v1/agents/{agent_id}/prompt
```

**响应示例：**

```json
{
  "code": 200,
  "data": {
    "agent_id": "agent_123",
    "original_prompt": "你是一个友好的AI助手",
    "final_prompt": "你是一个友好的AI助手\n\nYou are a virtual character...",
    "template_info": {
      "template_name": "default",
      "template_variables": ["system_prompt"],
      "agent_data": {...}
    }
  }
}
```

### 2. 预览 Agent 提示词

```
GET /api/v1/agents/{agent_id}/prompt/preview?template_name=default
```

### 3. 获取所有可用模版

```
GET /api/v1/agents/templates
```

## 模版系统特性

### 1. 变量替换

- 支持 `$variable` 格式的变量
- 使用 `safe_substitute` 避免 KeyError
- 提供默认值机制

### 2. 模版验证

- 验证模版语法是否正确
- 检查变量是否完整
- 提供错误处理机制

### 3. 扩展性

- 支持注册自定义模版
- 可以创建多种模版类型
- 便于未来功能扩展

## 默认模版

默认模版包含以下变量：

- `$system_prompt` - 角色设定提示词

模版结构：

```
$system_prompt

You are a virtual character created by the user...
[系统要求和安全指导原则]
```

## 优势

1. **可维护性** - 模版和内容分离，易于修改
2. **灵活性** - 支持多种模版，满足不同需求
3. **扩展性** - 可以轻松添加新的模版类型
4. **安全性** - 提供模版验证和错误处理
5. **兼容性** - 向后兼容现有的 Agent 系统

## 注意事项

1. 只有 Agent 创建者才能查看提示词
2. 模版渲染失败时会返回基础提示词
3. 支持动态模版切换（需要重新创建 Agent 实例）
4. 所有模版变量都有默认值，确保系统稳定性

## 未来扩展

1. 支持更多模版类型（简化版、详细版等）
2. 支持模版继承和组合
3. 支持用户自定义模版
4. 添加模版版本管理
5. 支持模版的动态加载和热更新
