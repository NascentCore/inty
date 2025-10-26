# 代理扩展系统文档

## 概述

Agent Extensions 系统是 InTy 悬浮的一个灵活的扩展机制，允许在 Agent 模型中存储自定义的 JSON 数据。该系统主要用于存储非核心的、可选的 Agent 属性，如头像截取坐标、自定义配置等。

## 核心概念

### 扩展字段

- **数据库字段**：`agents.extensions`(JSON 类型)
- **架构支持**：`AgentBase` 和 `AgentUpdate` 都包含 `extensions: Optional[Dict[str, Any]] = None`- **存储方式**: 以 JSON 对象形式存储在 PostgreSQL 数据库中
- **持久化**：数据永久保存，重启服务不会丢失

## 流程数据

### 1.前端数据准备```typescript
// 定义扩展数据类型
interface AvatarCropData {
  x: number; // 截取区域左上角 X 坐标
  y: number; // 截取区域左上角 Y 坐标
  width: number; // 截取区域宽度
  height: number; // 截取区域高度
  imageWidth: number; // 原始图片宽度
  imageHeight: number; // 原始图片高度
}

// 准备更新数据
const updateData = {
  extensions: {
    avatar_crop: cropData,
  },
};
```

### 2. API 调用

```typescript
// 更新 Agent 的 extensions 数据
await api.inty.api.v1.ai.agents.update(agentId, updateData);
```

### 3. 后端处理

#### 数据库模型

```python
# app/models/agent.py
class Agent(Base):
    # ... 其他字段
    extensions = Column(JSON, nullable=True)  # 扩展数据
```#### 模式定义```python
# app/schemas/agent.py
class AgentBase(BaseModel):
    # ... 其他字段
    extensions: Optional[Dict[str, Any]] = None

class AgentUpdate(AgentBase):
    # 继承 extensions 字段
    pass
```

#### 服务层处理

```python
# app/services/agent_service.py
def _update_agent_in_db(agent_in: schemas.AgentUpdate, db_agent: models.Agent):
    # 更新其他字段
    for field, value in agent_in.model_dump(exclude_unset=True).items():
        setattr(db_agent, field, value)
    # extensions 字段会被自动更新
```

### 4. 数据读取

```typescript
// 前端读取 extensions 数据
const avatarCrop = agent.extensions?.avatar_crop as AvatarCropData | undefined;

if (avatarCrop && agent.background) {
  // 使用坐标数据从 agent.background 动态显示截取的头像
  // ...
}
```

## 使用场景

### 1. 头像截取功能

**用途**: 存储用户自定义的头像截取坐标

**设计说明**: `avatar_crop` 不存储源图片 URL，而是默认从 `agent.background` 截取，确保数据一致性。

**数据结构**:

```json
{
  "extensions": {
    "avatar_crop": {
      "x": 0,
      "y": 106,
      "width": 1080,
      "height": 1080,
      "imageWidth": 1080,
      "imageHeight": 2400
    }
  }
}
```

**前端使用**:

```typescript
// AvatarDisplay 组件
const avatarCrop = agent.extensions?.avatar_crop as AvatarCropData | undefined;

if (avatarCrop && agent.background) {
  // 计算显示位置和缩放
  const scale = size / avatarCrop.width;
  const imageDisplayWidth = avatarCrop.imageWidth * scale;
  const imageDisplayHeight = avatarCrop.imageHeight * scale;
  const offsetX = -avatarCrop.x * scale;
  const offsetY = -avatarCrop.y * scale;

  // 渲染截取的头像
  return (
    <div style={{ width: size, height: size, overflow: 'hidden' }}>
      <img
        src={agent.background}
        style={{
          width: imageDisplayWidth,
          height: imageDisplayHeight,
          position: 'absolute',
          left: offsetX,
          top: offsetY,
          objectFit: 'cover'
        }}
      />
    </div>
  );
}
```

### 2. 清理扩展数据

**场景**: 当用户上传新头像时，清理旧的截取数据

```typescript
// 编辑 Agent 时清理旧的 avatar_crop 数据
if (editAvatarFile) {
  updateData.extensions = {
    ...currentAgent.extensions,
    avatar_crop: null, // 清理旧的截取数据
  };
}
```

## 技术实现细节

### 1. 数据库层面

- **字段类型**: `JSON`（PostgreSQL）
- **索引**：可以创建GIN索引，支持JSON查询
- **约束**：无特殊约束，支持各方 JSON 结构

### 2.存储机制```python
# app/services/agent_service.py
# Agent 数据会被缓存，包括 extensions 字段
cache_service.set_agent_config(agent_id, agent_data, ttl=1800)
```### 3. API 兼容性

- **流畅兼容**：现有代理不出行
- **可选字段**：扩展为可选，不影响现有功能
- **类型安全**：前端使用 TypeScript 类型定义确保类型安全

## 最佳实践

### 1.数据结构设计```typescript
// 为每个扩展功能定义明确的接口
interface AvatarCropData {
  x: number;
  y: number;
  width: number;
  height: number;
  imageWidth: number;
  imageHeight: number;
}

// 使用命名空间避免冲突
interface AgentExtensions {
  avatar_crop?: AvatarCropData;
  custom_settings?: CustomSettings;
  // 未来可以添加更多扩展
}
```

### 2. 前端使用

```typescript
// 安全的类型断言
const avatarCrop = agent.extensions?.avatar_crop as AvatarCropData | undefined;

// 检查数据完整性
if (avatarCrop && agent.background && avatarCrop.width > 0) {
  // 使用数据
}
```

### 3. 数据清理

```typescript
// 当不再需要某个扩展数据时，显式清理
const updateData = {
  extensions: {
    ...currentAgent.extensions,
    avatar_crop: null, // 清理特定扩展
  },
};
```## 扩展性考虑

### 1.未来的扩展

扩展字段可以轻松支持新的功能扩展：```json
{
  "extensions": {
    "avatar_crop": {
      /* 头像截取数据 */
    },
    "custom_theme": {
      /* 自定义主题 */
    },
    "widget_config": {
      /* 组件配置 */
    },
    "user_preferences": {
      /* 用户偏好 */
    }
  }
}
```

### 2. 版本控制

```typescript
// 可以为扩展数据添加版本信息
interface ExtensionsWithVersion {
  version: string;
  avatar_crop?: AvatarCropData;
  // 其他扩展数据
}
```

### 3. 数据验证

```python
# 后端可以添加扩展数据的验证
def validate_extensions(extensions: Dict[str, Any]) -> bool:
    if "avatar_crop" in extensions:
        crop_data = extensions["avatar_crop"]
        required_fields = ["x", "y", "width", "height", "imageWidth", "imageHeight", "sourceImageUrl"]
        return all(field in crop_data for field in required_fields)
    return True
```## 性能考虑

### 1. 数据库性能

- **JSON 查询**：可以使用 PostgreSQL 的 JSON 操作符进行查询
- **索引**：对常用查询字段创建GIN索引
- **大小限制**：避免扩展中存储过大的数据

### 2. 策略服务器

- **服务器包含**: 扩展数据包含在Agent服务器中
- **服务器刷新**：更新扩展时会刷新服务器
- **内存使用**：注意存储大小，避免内存泄漏

### 3.网络传输

- **数据大小**：控制扩展数据大小，避免影响API响应时间
- **压缩**: 使用 gzip 压缩减少传输大小

## 错误处理

### 1.数据格式错误```typescript
try {
  const avatarCrop = agent.extensions?.avatar_crop as AvatarCropData;
  // 使用数据
} catch (error) {
  console.error("Invalid avatar_crop data:", error);
  // 回退到默认显示
}
```

### 2. 数据缺失

```typescript
// 检查必要字段是否存在
if (!agent.extensions?.avatar_crop || !agent.background) {
  // 使用默认头像
  return <Avatar src={agent.avatar} icon={<RobotOutlined />} />;
}
```

## 监控和调试

### 1. 日志记录

```python
# 记录 extensions 数据更新
logger.info(f"Updated agent {agent_id} extensions: {extensions}")
```

### 2. 数据验证

```typescript
// 前端数据验证
const validateAvatarCrop = (data: any): data is AvatarCropData => {
  return (
    data &&
    typeof data.x === "number" &&
    typeof data.y === "number" &&
    typeof data.width === "number" &&
    typeof data.height === "number" &&
    typeof data.imageWidth === "number" &&
    typeof data.imageHeight === "number"
  );
};
```## 总结

Agent Extensions系统为存储Agent的自定义数据提供了一个灵活、可扩展的机制。通过JSON字段和类型安全的接口，系统可以轻松支持新功能而不影响现有代码。这种设计既保证了结构兼容，又为未来的功能扩展提供了良好的基础。