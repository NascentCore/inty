# InTy API 文档

## 规范
- 所有接口的响应都遵循统一的格式：
  - code: 状态码，200表示成功
  - message: 状态描述
  - data: 具体的业务数据
- 对于分页接口，统一包含：
  - total: 总记录数
  - page: 当前页码
  - page_size: 每页大小
  - items: 具体数据列表

## 1. 用户认证模块

### 1.1 用户注册（仅手机号注册）

```http
POST /api/v1/auth/register
```
请求参数:
```json
{
  "auth_type": "PHONE",    // 认证类型: 仅支持 PHONE
  "auth_data": {
    "phone": "string",    // 手机号
    "code": "string"      // 验证码
  },
  // 首次注册时需要补充的用户信息
  "user_info": {
    "gender": "enum",          // 性别: MALE/FEMALE/OTHER
    "age_group": "string",     // 年龄段
    "system_language": "string" // 系统语言
  }
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "string",           // JWT token
    "user": {
      "id": "string",
      "nickname": "string",
      "avatar": "string",
      "email": "string",
      "phone": "string",
      "auth_type": "string",     // 用户认证类型
      "is_new_user": "boolean"   // 是否新用户
    }
  }
}
```

- 仅支持手机号注册，Google 注册请使用 /api/v1/auth/google/login。

### 1.2 用户登录
```http
POST /api/v1/auth/login
```
请求参数:
```json
{
  "phone": "string",
  "code": "string"    // 验证码
}
```

### 1.3 Google 账号登录
```http
POST /api/v1/auth/google/login
```
请求参数:
```json
{
  "id_token": "string",         // Google Sign-In SDK 获取到的 id_token
  "user_info": {                // 首次注册时补充的用户信息（可选）
    "gender": "enum",           // 性别: MALE/FEMALE/OTHER
    "age_group": "string",      // 年龄段
    "system_language": "string" // 系统语言
  }
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "string",           // 你自己系统的 JWT token
    "user": {
      "id": "string",
      "nickname": "string",
      "avatar": "string",
      "email": "string",
      "phone": "string",
      "auth_type": "GOOGLE",
      "is_new_user": true        // 是否新用户
    }
  }
}
```

### 1.4 生成游客ID
```http
POST /api/v1/auth/guest
```
请求参数:
```json
{
  "device_id": "string",         // 设备唯一标识（如可选，防止同一设备重复生成）
  "system_language": "string"    // 系统语言（可选）
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "guest_id": "string",        // 游客唯一ID
    "token": "string",           // 游客身份token
    "is_new_guest": "boolean"    // 是否新游客
  }
}
```

## 2. AI角色模块

### 2.1 获取AI角色列表
```http
GET /api/v1/ai/agents
```
查询参数:
```json
{
  "page": "integer",
  "page_size": "integer",
  "category": "string",     // 可选，角色类型：动漫/游戏/话题/情感咨询
  "gender": "string"        // 可选，性别筛选
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": "integer",
    "page": "integer",
    "page_size": "integer",
    "items": [{
      "id": "string",
      "name": "string",
      "avatar": "string",
      "description": "string",
      "category": "string",
      "gender": "string",
      "opening": "string",
      "is_followed": "boolean",
      "voice_preview": "string"
    }]
  }
}
```

### 2.2 获取AI角色详情
```http
GET /api/v1/ai/agents/{agent_id}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "string",
    "name": "string",
    "gender": "enum",
    "avatar": "string",
    "voice_id": "string",
    "settings": "string",
    "intro": "string",
    "opening": "string",
    "visibility": "enum",
    "photos": ["string"],
    "category": "string",
    "is_followed": "boolean",
    "status": "string",    // PENDING/APPROVED/REJECTED
    "creator": {
      "id": "string",
      "nickname": "string",
      "avatar": "string"
    }
  }
}
```

### 2.3 关注AI角色
```http
POST /api/v1/ai/agents/{agent_id}/follow
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "is_followed": "boolean",  // true: 已关注, false: 已取消关注
    "follower_count": "integer" // 被关注用户的粉丝数
  }
}
```

### 2.4 创建AI角色
```http
POST /api/v1/ai/agents
```
请求参数:
```json
{
  "name": "string",          // 昵称，最大30个字符
  "gender": "enum",          // 性别：MALE/FEMALE/OTHER
  "avatar": "string",        // 头像URL
  "voice_id": "string",      // 语音包ID
  "settings": "string",      // 对话效果设置
  "intro": "string",         // 角色简介
  "opening": "string",       // 开场白
  "visibility": "enum",      // 开放类型：PUBLIC/PRIVATE
  "photos": ["string"],      // 相册图片URL数组
  "category": "string"
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "string",
    "name": "string",
    "gender": "enum",
    "avatar": "string",
    "voice_id": "string",
    "settings": "string",
    "intro": "string",
    "opening": "string",
    "visibility": "enum",
    "photos": ["string"],
    "category": "string",
    "status": "string"    // PENDING/APPROVED/REJECTED
  }
}
```

### 2.5 更新AI角色
```http
PUT /api/v1/ai/agents/{cagent_id}
```
请求参数:
```json
{
  "name": "string",          // 昵称，最大30个字符
  "gender": "enum",          // 性别：MALE/FEMALE/OTHER
  "avatar": "string",        // 头像URL
  "voice_id": "string",      // 语音包ID
  "settings": "string",      // 对话效果设置
  "intro": "string",         // 角色简介
  "opening": "string",       // 开场白
  "visibility": "enum",      // 开放类型：PUBLIC/PRIVATE
  "photos": ["string"],      // 相册图片URL数组
  "category": "string"
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "string",
    "name": "string",
    "gender": "enum",
    "avatar": "string",
    "voice_id": "string",
    "settings": "string",
    "intro": "string",
    "opening": "string",
    "visibility": "enum",
    "photos": ["string"],
    "category": "string",
    "status": "string"    // PENDING/APPROVED/REJECTED
  }
}
```

## 3. 聊天模块

### 3.1 获取聊天记录
```http
GET /api/v1/chats/{agent_id}/messages
```
查询参数:
```json
{
  "page": "integer",
  "page_size": "integer"
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": "integer",
    "page": "integer",
    "page_size": "integer",
    "items": [{
      "id": "string",
      "content": "string",
      "type": "string",      // TEXT/VOICE/IMAGE
      "sender_type": "string", // USER/AI
      "sender": {
        "id": "string",
        "name": "string",
        "avatar": "string"
      },
      "created_at": "timestamp"
    }]
  }
}
```

### 3.2 发送消息
```http
POST /api/v1/chats/{agent_id}/messages
```
请求参数:
```json
{
  "content": "string",
  "type": "enum"    // 消息类型：TEXT/VOICE/IMAGE
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "message_id": "string",
    "status": "string"    // SENT/FAILED
  }
}
```

### 3.3 获取对话设置
```http
GET /api/v1/chats/{agent_id}/settings
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "language": "string",
    "voice_enabled": "boolean",
    "keep_talking": "boolean",
    "agent": {
      "id": "string",
      "name": "string",
      "avatar": "string"
    }
  }
}
```

### 3.4 更新对话设置
```http
PUT /api/v1/chats/{agent_id}/settings
```
请求参数:
```json
{
  "language": "string",
  "voice_enabled": "boolean",
  "keep_talking": "boolean",
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "updated": "boolean"
  }
}
```

## 4. 消息中心模块

### 4.1 获取消息列表
```http
GET /api/v1/messages
```
查询参数:
```json
{
  "type": "enum",    // ALL/FOLLOWED
  "page": "integer",
  "page_size": "integer"
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": "integer",
    "page": "integer",
    "page_size": "integer",
    "items": [{
      "id": "string",
      "type": "string",      // CHAT/SYSTEM
      "title": "string",
      "content": "string",
      "sender": {
        "id": "string",
        "name": "string",
        "avatar": "string"
      },
      "unread_count": "integer",
      "last_message_time": "timestamp"
    }]
  }
}
```

### 4.2 获取系统通知
```http
GET /api/v1/messages/system
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": "integer",
    "items": [{
      "id": "string",
      "title": "string",
      "content": "string",
      "type": "string",      // ANNOUNCEMENT/NOTIFICATION
      "created_at": "timestamp",
      "is_read": "boolean"
    }]
  }
}
```

## 5. 用户信息模块

### 5.1 获取个人信息
```http
GET /api/v1/users/profile
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "string",
    "nickname": "string",
    "avatar": "string",
    "gender": "string",
    "age_group": "string",
    "description": "string",
    "email": "string",
    "phone": "string",
    "created_at": "timestamp",
    "stats": {
      "following_count": "integer",
      "followers_count": "integer",
      "agents_count": "integer"
    }
  }
}
```

### 5.2 更新个人信息
```http
PUT /api/v1/users/profile
```
请求参数:
```json
{
  "nickname": "string",
  "avatar": "string",
  "gender": "enum",
  "age_group": "string",
  "description": "string"
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "updated": "boolean"
  }
}
```

### 5.3 获取他人主页信息
```http
GET /api/v1/users/{user_id}/profile
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "string",
    "nickname": "string",
    "avatar": "string",
    "description": "string",
    "is_following": "boolean",
    "stats": {
      "following_count": "integer",
      "followers_count": "integer",
      "agents_count": "integer"
    },
    "agents": [{
      "id": "string",
      "name": "string",
      "avatar": "string",
      "description": "string"
    }]
  }
}
```

### 5.4 举报AI角色
```http
POST /api/v1/agents/{agent_id}/report
```
请求参数:
```json
{
  "reason": ["string"],
  "description": "string",
  "evidence": ["string"]  // 证据图片URL数组
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "report_id": "string",
    "status": "string"    // PENDING/PROCESSED
  }
}
```

### 5.5 关注/取消关注用户
```http
POST /api/v1/users/{user_id}/follow
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "is_followed": "boolean",   // true: 已关注, false: 已取消关注
    "follower_count": "integer" // 被关注用户的粉丝数
  }
}
```

## 6. 推荐模块

### 6.1 获取推荐AI列表
```http
GET /api/v1/recommendations/agents
```
查询参数:
```json
{
  "category": "string",
  "page": "integer",
  "page_size": "integer"
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": "integer",
    "page": "integer",
    "page_size": "integer",
    "items": [{
      "id": "string",
      "name": "string",
      "avatar": "string",
      "gender": "enum",
      "intro": "string",
      "opening": "string",
      "category": "string",
      "is_followed": "boolean",
      "creator": {
        "id": "string",
        "nickname": "string",
        "avatar": "string"
      }
    }]
  }
}
```

## 7. 设置模块

### 7.1 获取应用设置
```http
GET /api/v1/settings
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "language": "string",
    "voice_enabled": "boolean",
    "keep_talking": "boolean",
    "version": "string",
    "support_email": "string"
  }
}
```

### 7.2 更新应用设置
```http
PUT /api/v1/settings
```
请求参数:
```json
{
  "language": "string",
  "keep_talking": "boolean",
  "voice_enabled": "boolean"
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "updated": "boolean"
  }
}
```

## 8. 资源模块

### 8.1 上传图片
```http
POST /api/v1/resources/images
```
请求参数:
```
Form-data:
- file: 图片文件
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "url": "string",
    "width": "integer",
    "height": "integer",
    "size": "integer",
    "format": "string"
  }
}
```

### 8.2 获取语音包列表
```http
GET /api/v1/resources/voices
```
查询参数:
```json
{
  "category": "string",  // 语音类型：通用/扩展
  "gender": "string"     // 性别
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": "integer",
    "items": [{
      "id": "string",
      "name": "string",
      "category": "string",
      "gender": "string",
      "preview_url": "string",
      "description": "string"
    }]
  }
}
```

### 8.3 语音播放接口
```http
POST /api/v1/audio/play
```
查询参数:
```json
{
  "voice_id": "string",   // 语音包ID
  "text": "string",       // 需要转换的文本
  "message_id": "string", // 消息ID
  "features": {           // 可选，语音特征调整
    "pitch": "integer",   // 音调调整，范围-20~20
    "speed": "integer",   // 语速调整，范围0.5~2.0
    "volume": "integer"   // 音量调整，范围0~100
  }
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "audio_url": "string",    // 音频文件URL
    "duration": "integer",    // 音频时长（秒）
    "text": "string",         // 原始文本
    "format": "string",       // 音频格式，如：mp3/wav
    "expire_at": "timestamp"  // URL过期时间
  }
}
```

### 8.4 获取可用艺术风格
```http
GET /api/v1/images/art-styles
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "styles": [{
      "id": "string",
      "name": "string",
      "preview_url": "string",  // 风格预览图
      "description": "string",  // 风格描述
      "is_featured": "boolean"  // 是否为推荐风格
    }]
  }
}
```

### 8.5 生成AI图片接口
```http
POST /api/v1/images/generate
```
请求参数:
```json
{
  "reference_image": "string",   // 可选，参考图片URL
  "prompt": "string",            // 可选，图片描述提示词
  "art_style": "string",        // 艺术风格图片URL
  "settings": {                  // 可选，生成设置
    "width": "integer",          // 图片宽度
    "height": "integer",         // 图片高度
    "num_images": "integer",     // 生成图片数量，默认1
    "quality": "string"          // 图片质量：DRAFT/STANDARD/HIGH
  }
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "string",        // 生成任务ID
    "status": "string",         // PROCESSING/SUCCESS/FAILED
    "estimated_time": "integer" // 预计完成时间（秒）
  }
}
```

### 8.6 获取生成任务状态
```http
GET /api/v1/images/generate/status
```
查询参数:
```json
{
  "task_id": "string"  // 生成任务ID
}
```
响应参数:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "string",
    "status": "string",         // PROCESSING/SUCCESS/FAILED
    "progress": "integer",      // 生成进度，0-100
    "images": [{               // status为SUCCESS时返回
      "url": "string",         // 图片URL
      "width": "integer",      // 图片宽度
      "height": "integer",     // 图片高度
      "prompt": "string",      // 生成使用的提示词
      "art_style": "string"    // 使用的艺术风格
    }],
    "error": "string"          // 错误信息，status为FAILED时返回
  }
}
```