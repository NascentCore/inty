# Agent系统角色卡集成方案

## 概述

本文档描述如何改造现有的Agent聊天系统以支持角色卡功能，重点关注personality、scenario、first_message、message_example等字段的集成。

名词定义：

* user/用户：app 使用者，使用 app 各项功能，此处指使用 app 与角色聊天
* character/角色：指用户对谈的对象，LLM 驱动的对话智能体（conversational agent）
* character card/角色卡：指酒馆定义的角色信息描述存储格式，JSON 格式，同时内嵌在 PNG 图片内，因此得名角色卡
* prompt/提示词：统称，泛指所有作为输入提供给大语言模型，并让大模型接续生成内容的数据；
  常被滥用，使用时应区分具体所指的提示词；提示词常分为 3 类：system prompt/系统提示词、
  character prompt/角色提示词、chats prompt/聊天提示词，以下详述：
  * system prompt/系统提示词：指影响模型、对用户不可见的提示词；比如酒馆中用于说明沟通方式的主提示词（main prompt）：
  * character prompt/角色提示词：指描述角色信息的提示词；是角色卡中的主要内容，比如：
    * 角色身份信息：性别、年龄、性别、外貌、职业、等等
    *

## 当前架构分析

### 现有Agent类结构

```python
class Agent:
    def __init__(self, agent_id, name, model_config, system_prompt, description, template_name):
        # 基础属性
        self.agent_id = agent_id
        self.name = name
        self.system_prompt = system_prompt
        self.description = description
        
        # LangGraph agent
        self.agent = create_react_agent(
            name=name,
            model=model,
            tools=[...],
            prompt=self.final_prompt,
            store=postgres_store,
            checkpointer=self.checkpointer
        )
```

### 当前提示词生成流程

1. 从数据库加载Agent配置
2. 通过`prompt_template_manager`渲染模板
3. 注入用户信息上下文
4. 传递给LangGraph agent

## 改造方案

### 1. Agent构造函数扩展

```python
class Agent:
    def __init__(self, 
                 agent_id: str, 
                 name: str, 
                 model_config: dict, 
                 system_prompt: str, 
                 description: str = "", 
                 template_name: str = "default",
                 # 新增角色卡相关参数
                 personality: str = "",
                 scenario: str = "",
                 first_message: str = "",
                 message_example: str = "",
                 creator_notes: str = "",
                 tags: List[str] = None,
                 character_version: str = "1.0",
                 extensions: Dict[str, Any] = None):
        
        # 现有属性
        self.agent_id = agent_id
        self.name = name
        self.system_prompt = system_prompt
        self.description = description
        self.template_name = template_name
        
        # 角色卡相关属性
        self.personality = personality
        self.scenario = scenario
        self.first_message = first_message
        self.message_example = message_example
        self.creator_notes = creator_notes
        self.tags = tags or []
        self.character_version = character_version
        self.extensions = extensions or {}
        
        # 更新agent_data以包含角色卡信息
        self._agent_data = {
            'id': agent_id,
            'name': name,
            'prompt': system_prompt,
            'description': description,
            'model_config': model_config,
            'personality': personality,
            'scenario': scenario,
            'first_message': first_message,
            'message_example': message_example,
            'creator_notes': creator_notes,
            'tags': tags,
            'character_version': character_version,
            'extensions': extensions
        }
        
        # 使用增强的提示词生成
        self.final_prompt = self._build_enhanced_prompt()
```

### 2. 增强的提示词生成

```python
def _build_enhanced_prompt(self) -> str:
    """
    构建包含角色卡信息的增强提示词
    """
    # 基础模板渲染
    base_prompt = prompt_template_manager.render_prompt(
        agent_data=self._agent_data,
        template_name=self.template_name
    )
    
    # 角色卡信息增强
    character_context = self._build_character_context()
    
    if character_context:
        # 将角色卡上下文与基础提示词结合
        enhanced_prompt = f"{base_prompt}\n\n{character_context}"
    else:
        enhanced_prompt = base_prompt
    
    return enhanced_prompt

def _build_character_context(self) -> str:
    """
    构建角色卡上下文信息
    """
    context_parts = []
    
    # 性格特征
    if self.personality:
        context_parts.append(f"[角色性格]\n{self.personality}")
    
    # 场景设定
    if self.scenario:
        context_parts.append(f"[场景背景]\n{self.scenario}")
    
    # 对话示例
    if self.message_example:
        context_parts.append(f"[对话风格参考]\n{self.message_example}")
    
    # 标签信息（用于角色行为指导）
    if self.tags:
        context_parts.append(f"[角色标签]\n{', '.join(self.tags)}")
    
    if context_parts:
        return "\n\n".join(context_parts)
    
    return ""
```

### 3. 会话开始逻辑改造

```python
def _chat_sync(self, user_id: str, session_id: str, messages: dict[str, Any]) -> str:
    """同步聊天方法，支持角色卡功能"""
    self._update_last_used()
    
    # 获取用户信息上下文
    user_info_context = self._get_user_info_context_sync(user_id)
    
    # 检查是否是新会话的第一条消息
    is_first_message = self._is_first_message_in_session(session_id)
    
    pool = get_connection_pool()
    with pool.connection() as conn_local:
        try:
            history = PostgresChatMessageHistory(
                table_name,
                session_id,
                sync_connection=conn_local
            )
            
            # 构建增强消息
            enhanced_messages = messages["messages"].copy()
            
            # 注入用户信息
            if user_info_context:
                context_message = SystemMessage(content=user_info_context)
                enhanced_messages.insert(0, context_message)
            
            # 如果是第一条消息且有开场白，优先使用角色卡的first_message
            if is_first_message and self.first_message:
                # 添加角色的开场白作为系统消息
                greeting_message = SystemMessage(
                    content=f"[角色开场白]\n{self.first_message}\n请以此作为对话的开始。"
                )
                enhanced_messages.insert(0, greeting_message)
            
            # 保存原始用户消息到历史记录
            history.add_messages(messages["messages"])
            
            # 执行对话
            thread_id = f"{user_id}_{self.agent_id}"
            config = {'configurable': {'user_id': user_id, 'thread_id': thread_id}}
            
            enhanced_messages_dict = {"messages": enhanced_messages}
            response = self.agent.invoke(enhanced_messages_dict, config)
            
            # 处理响应
            ai_messages = [message for message in response.get("messages", []) 
                          if isinstance(message, AIMessage)]
            response_text = ai_messages[-1].content if ai_messages else "抱歉，我无法理解您的消息。请再试一次。"
            
            # 保存AI响应到历史记录
            history.add_messages([AIMessage(content=response_text)])
            
            return response_text
            
        except Exception as e:
            logger.error(f"聊天处理失败 - Agent: {self.agent_id}, Session: {session_id}, Error: {str(e)}")
            raise

def _is_first_message_in_session(self, session_id: str) -> bool:
    """
    检查是否是会话中的第一条消息
    """
    try:
        pool = get_connection_pool()
        with pool.connection() as conn:
            # 检查session_id对应的历史记录数量
            from psycopg import sql
            query = sql.SQL("""
                SELECT COUNT(*) 
                FROM chat_history 
                WHERE session_id = %s
            """)
            result = conn.execute(query, (session_id,))
            count = result.fetchone()[0]
            return count == 0
    except Exception as e:
        logger.error(f"检查首次消息失败: {str(e)}")
        return False
```

### 4. AgentManager改造

```python
async def get_agent(self, agent_data: dict) -> Agent:
    """
    获取或创建Agent实例（支持角色卡）
    """
    # ... 现有逻辑 ...
    
    # 创建新的Agent实例时传递角色卡数据
    try:
        agent = Agent(
            agent_id=agent_id,
            name=agent_data['name'],
            model_config=model_config,
            system_prompt=system_prompt,
            description=description,
            template_name=template_name,
            # 角色卡相关参数
            personality=agent_data.get('personality', ''),
            scenario=agent_data.get('scenario', ''),
            first_message=agent_data.get('first_message', ''),
            message_example=agent_data.get('message_example', ''),
            creator_notes=agent_data.get('creator_notes', ''),
            tags=agent_data.get('tags', []),
            character_version=agent_data.get('character_version', '1.0'),
            extensions=agent_data.get('extensions', {})
        )
        
        # ... 其余逻辑 ...
        
    except Exception as e:
        logger.error(f"创建Agent实例失败 - Agent ID: {agent_id}, 错误: {str(e)}")
        raise
```

### 5. 流式聊天改造

```python
async def chat_stream(self, user_id: str, session_id: str, messages: dict[str, Any], db_session=None):
    """异步流式聊天方法（支持角色卡）"""
    self._update_last_used()
    
    def _stream_generator():
        # 获取用户信息上下文
        user_info_context = self._get_user_info_context_sync(user_id)
        
        # 检查是否是第一条消息
        is_first_message = self._is_first_message_in_session(session_id)
        
        pool = get_connection_pool()
        with pool.connection() as conn_local:
            try:
                history = PostgresChatMessageHistory(
                    table_name,
                    session_id,
                    sync_connection=conn_local
                )
                
                # 构建增强消息（与同步版本相同的逻辑）
                enhanced_messages = messages["messages"].copy()
                
                if user_info_context:
                    context_message = SystemMessage(content=user_info_context)
                    enhanced_messages.insert(0, context_message)
                
                # 处理开场白
                if is_first_message and self.first_message:
                    greeting_message = SystemMessage(
                        content=f"[角色开场白]\n{self.first_message}\n请以此作为对话的开始。"
                    )
                    enhanced_messages.insert(0, greeting_message)
                
                # 执行流式对话
                thread_id = f"{user_id}_{self.agent_id}"
                config = {'configurable': {'user_id': user_id, 'thread_id': thread_id}}
                
                enhanced_messages_dict = {"messages": enhanced_messages}
                
                all_messages = []
                for message_chunk, metadata in self.agent.stream(enhanced_messages_dict, config, stream_mode="messages"):
                    all_messages.append(message_chunk)
                    yield message_chunk, metadata
                
                # 保存调试信息
                if settings.agent.enable_debug_logging:
                    stream_response = {"messages": all_messages}
                    self._save_debug_messages(user_id, session_id, stream_response, conn_local)
                    
            except Exception as e:
                logger.error(f"流式聊天处理失败 - Agent: {self.agent_id}, Session: {session_id}, Error: {str(e)}")
                raise
    
    # ... 其余异步处理逻辑 ...
```

## 实现细节

### 1. 提示词优先级

1. **系统提示词** (最高优先级)
2. **角色卡上下文** (personality, scenario, message_example)
3. **用户信息上下文**
4. **对话历史**

### 2. 开场白处理

* 检测会话是否为首次对话
* 如果是首次且有`first_message`，注入为系统消息
* 不直接作为AI回复，而是指导AI的第一次回应

### 3. 对话风格指导

* `message_example`作为风格参考注入到提示词中
* 不强制复制，而是作为对话风格的示例
* 通过`personality`进一步强化角色特征

### 4. 性能优化

* 角色卡信息在Agent初始化时构建，避免每次对话重新构建
* 缓存用户信息上下文，减少数据库查询
* 首次消息检测使用简单的计数查询

### 5. 错误处理

* 角色卡字段缺失时使用默认值
* 提示词构建失败时回退到基础模板
* 保持与现有Agent的完全兼容性

## 测试策略

### 1. 单元测试

* 提示词生成逻辑
* 角色卡字段解析
* 首次消息检测

### 2. 集成测试

* 完整的对话流程
* 角色卡导入后的对话测试
* 流式聊天功能

### 3. 兼容性测试

* 现有Agent不受影响
* 无角色卡数据的Agent正常工作
* 部分角色卡字段缺失的处理

## 部署注意事项

1. **数据库兼容**: 新字段已通过迁移添加，现有数据不受影响
2. **性能影响**: 提示词长度可能增加，需要监控token使用量
3. **缓存策略**: Agent实例缓存包含角色卡信息，内存使用略有增加
4. **日志记录**: 增加角色卡相关的调试信息

## 后续扩展

1. **动态提示词**: 根据对话上下文动态调整角色表现
2. **情境感知**: 基于scenario字段实现情境感知对话
3. **风格学习**: 基于message_example训练个性化对话模型
4. **标签驱动**: 使用tags实现更精细的行为控制
