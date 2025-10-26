#角色卡系统文档

## 概述

InTy头像支持SillyTavern角色卡V2规范，允许用户导入和导出标准化的AI角色配置。角色卡系统提供了一种标准化的方式来定义AI角色的个性、背景、对话风格等特征。

## 角色卡V2规范

### 基本结构```json
{
  "spec": "chara_card_v2",
  "spec_version": "2.0",
  "data": {
    // 角色数据
  }
}
```

### 核心字段说明

#### 必需字段

- **`name`**: 角色名称，最大30个字符
- **`description`**: 角色描述，包含外貌、背景等基础信息

#### 基础字段

- **`personality`**: 性格特征，描述角色的行为方式和价值观
- **`scenario`**: 场景设定，定义角色所处的环境和背景故事
- **`first_mes`**: 第一条消息，角色的开场白
- **`mes_example`**: 对话示例，展示角色的说话风格

#### 高级字段

- **`creator_notes`**: 创作者备注，不会出现在提示中的说明信息
- **`tags`**: 标签数组，用于分类和搜索
- **`creator`**: 创作者名称
- **`character_version`**: 角色版本号
- **`extensions`**：扩展数据，用于存储自定义信息

## 功能特点

###支持的功能

1. **基础信息导入**：名称、描述、个性、场景
2. **对话风格**：first_mes，mes_example
3. **元数据**：creator_notes、tags、creator、character_version
4. **扩展数据**：扩展字段支持自定义数据

### 暂时不支持的功能

1. **system_prompt**：系统提示词（计划在后续版本支持）
2. **character_book**：角色书/世界书（计划在后续版本支持）
3. **alternate_greetings**：替代问候语（计划在后续版本支持）

###导入格式支持

- **JSON文件**：直接的角色卡JSON数据
- **PNG图片**: 从PNG图片的元数据中提取角色卡数据（需要PIL库）

## API接口

### 导入角色卡

####从JSON数据导入```http
POST /api/v1/agents/import-character-card
Content-Type: application/json

{
  "card_data": {
    "spec": "chara_card_v2",
    "spec_version": "2.0",
    "data": {
      "name": "角色名称",
      "description": "角色描述",
      // ... 其他字段
    }
  },
  "override_existing": false,
  "import_character_book": true,
  "import_alternate_greetings": true
}
```

#### 从文件导入

```http
POST /api/v1/agents/import-character-card-file
Content-Type: multipart/form-data

file: [角色卡文件]
override_existing: false
import_character_book: true
import_alternate_greetings: true
```

### 导出角色卡

#### 导出为角色卡格式

```http
POST /api/v1/agents/export-character-card
Content-Type: application/json

{
  "agent_id": "agent_123",
  "include_character_book": true,
  "include_alternate_greetings": true,
  "include_extensions": true
}
```

#### 获取角色卡数据

```http
GET /api/v1/agents/{agent_id}/character-card?include_character_book=true
```

### 验证角色卡

```http
POST /api/v1/agents/validate-character-card
Content-Type: application/json

{
  // 角色卡数据
}
```

### 获取支持的功能

```http
GET /api/v1/agents/character-card/features
```## 数据库映射

### 代理模型扩展字段```sql
-- 角色卡相关字段
character_card_spec VARCHAR,           -- 角色卡规范版本
character_card_data JSON,              -- 原始角色卡数据
personality TEXT,                      -- 性格特征
scenario TEXT,                         -- 场景设定
first_message TEXT,                    -- 第一条消息
message_example TEXT,                  -- 对话示例
creator_notes TEXT,                    -- 创作者备注
post_history_instructions TEXT,        -- 历史后指令
alternate_greetings JSON,              -- 替代问候语
character_book JSON,                   -- 角色书
tags JSON,                             -- 标签
character_version VARCHAR,             -- 版本号
extensions JSON                        -- 扩展数据
```### 字段映射关系

| 角色卡字段 |代理领域 | 说明 |
| ----------------- | ----------------- | ---------- |
|名称 |名称 | 角色名称 |
|描述 |简介 | 角色描述 |
|个性|个性| 性格特征 |
|场景|场景| 场景设定 |
|第一个消息 |第一条消息 | 第一条消息 |
|消息示例 |消息示例 | 对话示例 |
|创建者笔记 |创建者笔记 | 创作者备注 |
|标签 |标签 | 标签 储备 |
|字符版本 |字符版本 | 版本号 |
|扩展 |扩展 | 扩展数据|

## 使用示例

###创建角色卡```python
from app.schemas.character_card import CharacterCardV2, CharacterCardDataV2

# 创建角色卡数据
card_data = CharacterCardDataV2(
    name="测试角色",
    description="一个友好的AI助手",
    personality="友好、耐心、专业",
    scenario="现代办公环境",
    first_mes="你好！我是测试角色，很高兴为您服务！",
    mes_example="用户: 你好\n测试角色: 你好！有什么可以帮助您的吗？",
    tags=["助手", "友好", "专业"],
    creator="测试用户",
    character_version="1.0"
)

# 创建完整角色卡
card = CharacterCardV2(data=card_data)
```

### 导入角色卡

```python
from app.services.character_card_service import character_card_service
from app.schemas.character_card import CharacterCardImportRequest

# 创建导入请求
request = CharacterCardImportRequest(
    card_data=card_data,
    override_existing=False,
    import_character_book=True,
    import_alternate_greetings=True
)

# 导入角色卡
result = await character_card_service.import_character_card(
    request=request,
    user_id="user_123",
    db=db_session
)
```

## 错误处理

### 常见错误

1. **格式错误**: 角色卡数据格式不符合V2规范
2. **字段缺失**: 缺少必需的name字段
3. **字段长度**: 名称超过30个字符限制
4. **重名冲突**: 存在同名角色且未启用覆盖模式
5. **文件解析**: 无法从上传文件中解析角色卡数据

### 错误响应格式

```json
{
  "success": false,
  "message": "错误描述",
  "code": 400,
  "data": {
    "errors": [
      {
        "field": "name",
        "message": "角色名称不能为空",
        "code": "FIELD_REQUIRED"
      }
    ],
    "warnings": ["建议添加角色性格描述"]
  }
}
```## 性能考虑

1. **文件大小限制**: 上传文件最大10MB
2. **批量导入建议**：暂时不支持批量导入，逐个导入
3. **缓存**：解析后的角色卡数据会缓存在数据库中
4. **兼容**：保持与现有Agent系统的完全兼容

## 最佳实践

1. **命名规范名称**：使用有意义的角色，避免特殊字符
2. **内容质量**：提供详细的个性和场景描述
3. **标签管理**：使用合适的标签进行分类和搜索
4. **版本控制**：为角色更新设置合适的版本号
5. **测试验证**：导入前使用验证接口检查数据格式

## 兼容性说明

- **兼容**：现有Agent不出行，可以正常使用
- **向前兼容**：通过扩展字段支持未来的扩展
- **标准兼容**：严格遵循SillyTavern V2规范
- **跨平台**：导出的角色卡可在其他支持V2规范的平台使用

##后续规划

1. **system_prompt支持**: 允许角色卡覆盖系统提示词
2. **character_book支持**：现实角色书/世界书功能
3. **alternate_greetingsSupport**: 支持多种开场白
4. **批量操作**：支持批量导入/导出角色卡
5. **社区分享**：角色卡市场和分享功能