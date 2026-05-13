# 角色图片相册访问权限说明

> CREATED_BY_AGENT

## 概述

本文档说明管理员和普通用户对角色生成图片（背景图）的访问权限控制机制。

## 管理员权限

管理员可以通过运营平台查看**所有用户**为指定角色生成的图片。

### API 端点

- **路径**：`GET /api/v1/evaluation/agents/{agent_id}/generated-images`
- **权限要求**：需要 `is_superuser` 权限
- **功能**：获取指定角色的所有聊天生成图片

### 实现细节

```python
# backend/ops/api/v1/evaluation.py
if not current_user.is_superuser:
    return schemas.APIResponse.error(message="Unauthorized access")
```

该端点会：
- 查询 `resources` 表中指定 `agent_id` 的所有图片资源
- **不按 `user_id` 过滤**，返回所有用户的图片
- 返回数据包含每张图片的详细信息：
  - 图片 URL（CDN 和 GCS）
  - 生成提示词（`generation_prompt`）
  - 图片尺寸
  - 创建时间
  - **生成者信息**：`user_id`、`user_nickname`、`user_email`、`user_photo`

### 运营平台界面

在运营平台的"生成图片管理"页面（`GeneratedImagesPage.tsx`）中，管理员可以：
- 按角色查看所有生成的图片
- 查看图片元数据（生成提示词、尺寸、创建时间等）
- 查看生成者信息

## 普通用户权限

普通用户**只能看到自己生成的图片**，无法查看其他用户生成的图片。

### 访问方式

普通用户通过聊天消息接口查看自己生成的图片：

- **路径**：`GET /api/v1/chats/agents/{agent_id}/messages`
- **权限要求**：需要登录认证（`get_current_active_user`）
- **功能**：获取用户与指定角色的聊天消息历史

### 实现细节

```python
# app/api/v1/endpoints/chats.py
messages_data = chat_history_service.get_messages_paginated(
    session_id=session_id, 
    limit=limit, 
    offset=offset, 
    user_id=current_user.id
)
```

该机制通过以下方式实现隔离：
- 每个用户与每个角色有**独立的 chat session**
- 通过 `session_id` 隔离不同用户的消息
- 聊天消息中包含用户自己生成的图片信息（在 `meta_data.generated_image` 中）

### 数据存储

图片资源存储在 `resources` 表中，每条记录包含：
- `user_id`：标识生成该图片的用户
- `agent_id`：标识图片所属的角色
- `resource_metadata`：包含生成提示词等元数据

虽然数据库中存在所有用户的图片记录，但普通用户无法通过 API 访问其他用户的图片。

## 总结

| 用户类型 | 可访问的图片范围 | 访问方式 |
|---------|----------------|---------|
| **管理员** | 所有用户生成的图片 | 运营平台 `/evaluation/agents/{agent_id}/generated-images` |
| **普通用户** | 仅自己生成的图片 | 聊天消息接口 `/chats/agents/{agent_id}/messages` |

## 相关代码文件

- `backend/ops/api/v1/evaluation.py`：管理员图片查看端点
- `app/api/v1/endpoints/chats.py`：用户聊天消息端点
- `app/models/resource.py`：图片资源数据模型
- `app/services/chat_history_service.py`：聊天消息服务
- `evaluation/pages/GeneratedImagesPage.tsx`：运营平台图片管理页面
