# DevTest - 开发测试页面

## 📖 简介

DevTest 是一个用于测试 Inty SDK 各项功能的开发测试页面。所有功能被拆分为独立的组件，方便管理和维护。

## 🔧 配置说明

### Base URL 配置

项目统一使用相对路径 `/` 作为 Base URL，请求会通过代理转发到实际服务器：

- **开发环境**: 请求通过 `config/proxy.ts` 转发到 `https://dev.inty.sxwl.ai`
- **生产环境**: 请求直接发送到生产服务器

配置位置：

- SDK 配置: `src/constants/index.ts` → `INTY_SDK_CONFIG.BASE_URL`
- 代理配置: `config/proxy.ts`

## 🚀 访问地址

```
http://localhost:8000/dev-test
```

## 📂 文件结构

```
DevTest/
├── index.tsx                    # 主页面
├── index.less                   # 页面样式
├── README.md                    # 本文档
└── components/                  # 测试组件
    ├── GuestLogin.tsx          # 游客登录
    ├── UserProfile.tsx         # 获取用户信息
    ├── RecommendAgents.tsx     # 获取推荐角色列表
    ├── ChatCreate.tsx          # 创建聊天会话
    ├── ChatList.tsx            # 获取聊天列表
    ├── ChatDelete.tsx          # 删除聊天会话
    ├── MessageHistory.tsx      # 获取消息历史
    ├── ChatSettings.tsx        # 获取聊天设置
    └── UpdateChatSettings.tsx  # 更新聊天设置
```

## 🎯 功能模块

### 1. 认证模块

#### 游客登录 (`GuestLogin.tsx`)

- **功能**: 创建游客账号并获取 Token
- **参数**:
  - Device ID (可选，自动生成)
  - 系统语言 (可选，默认 zh-CN)
- **注意**: Token 会自动保存到本地存储

### 2. 用户模块

#### 获取个人信息 (`UserProfile.tsx`)

- **功能**: 获取当前用户的个人信息
- **前置条件**: 需要先执行游客登录获取 Token

### 3. AI 角色模块

#### 获取推荐角色列表 (`RecommendAgents.tsx`)

- **功能**: 获取推荐的 AI 角色列表
- **参数**:
  - 页码 (可选，默认 1)
  - 每页数量 (可选，默认 20，最大 100)
  - 排序方式 (可选)
    - `score_based_random` - 基于评分的随机排序
    - `random` - 随机排序
    - `created_asc` - 创建时间升序
    - `created_desc` - 创建时间降序
  - 排序种子 (随机排序时使用，可选)

### 4. 聊天会话模块

#### 创建聊天会话 (`ChatCreate.tsx`)

- **功能**: 为指定 Agent 创建聊天会话
- **参数**:
  - Agent ID (必填)

#### 获取聊天列表 (`ChatList.tsx`)

- **功能**: 获取当前用户的聊天会话列表
- **参数**:
  - 页码 (可选，默认 1)
  - 每页数量 (可选，默认 20)

#### 删除聊天会话 (`ChatDelete.tsx`)

- **功能**: 删除指定的聊天会话
- **参数**:
  - Chat ID (必填)

### 5. 消息与设置模块

#### 获取消息历史 (`MessageHistory.tsx`)

- **功能**: 获取与指定 Agent 的聊天消息历史
- **参数**:
  - Agent ID (必填)
  - 页码 (可选，默认 1)
  - 每页数量 (可选，默认 50)

#### 获取聊天设置 (`ChatSettings.tsx`)

- **功能**: 获取与指定 Agent 的聊天设置
- **参数**:
  - Agent ID (必填)

#### 更新聊天设置 (`UpdateChatSettings.tsx`)

- **功能**: 更新与指定 Agent 的聊天设置
- **参数**:
  - Agent ID (必填)
  - Voice ID (可选)
  - 自动语音开关 (可选)

#### 生成消息语音 (`GenerateMessageVoice.tsx`)

- **功能**: 为指定消息生成语音
- **参数**:
  - Agent ID (必填)
  - Message ID (必填)
  - 语言代码 (可选)

#### 发送消息 V1 (`SendMessageV1.tsx`)

- **功能**: 使用 V1 API 发送消息（已废弃）
- **参数**:
  - Agent ID (必填)
  - 消息内容 (必填)
  - 是否流式响应 (可选)
  - 语言 (可选)
  - 模型 (可选)
- **注意**: 此 API 已废弃，建议仅用于测试

#### 发送消息 V2 (`SendMessageV2.tsx`)

- **功能**: 使用 V2 API 发送消息（已废弃）
- **参数**:
  - Agent ID (必填)
  - 消息内容 (必填)
  - 是否流式响应 (可选)
- **注意**: 此 API 已废弃，建议仅用于测试

## 📝 使用步骤

1. **启动项目**

   ```bash
   npm run dev
   # 或
   yarn dev
   ```

2. **访问测试页面**
   - 打开浏览器访问: `http://localhost:8000/dev-test`

3. **打开浏览器控制台**
   - 按 `F12` 或右键点击 "检查" 打开开发者工具
   - 切换到 "Console" 标签页查看测试结果

4. **执行测试流程**
   - 先执行 "游客登录" 获取 Token
   - Token 会自动保存，后续接口会自动使用
   - 依次测试其他功能模块

## 🔍 测试示例

### 示例 1: 完整测试流程

```
1. 游客登录
   - 点击 "自动填充" 填充 Device ID
   - 点击 "执行测试"
   - 在控制台查看返回的 Token

2. 获取个人信息
   - 直接点击 "执行测试"
   - 在控制台查看用户信息

3. 获取推荐角色列表
   - 选择排序方式（默认: 基于评分的随机排序）
   - 可选填写排序种子（用于确保随机排序的一致性）
   - 点击 "执行测试"
   - 在控制台查看推荐角色列表

4. 创建聊天会话
   - 输入一个有效的 Agent ID
   - 点击 "执行测试"
   - 在控制台查看创建的会话信息

4. 获取聊天列表
   - 直接点击 "执行测试"
   - 在控制台查看会话列表
```

## 🛠 开发说明

### 添加新的测试功能

1. 在 `components/` 目录下创建新的组件文件
2. 在主页面 `index.tsx` 中导入并使用新组件
3. 按照现有组件的结构编写测试逻辑

### 组件开发规范

```typescript
import React, { useState } from 'react';
import { Button, Input, Space, message } from 'antd';
import Inty from 'inty';
import { storage } from '@/utils/storage';
import { STORAGE_KEYS } from '@/constants';

const YourTestComponent: React.FC = () => {
  const [loading, setLoading] = useState(false);

  const handleTest = async () => {
    setLoading(true);
    console.log('========== 开始测试: 功能名称 ==========');

    try {
      // 获取 Token
      const token = await getGuestToken();

      // 创建客户端
      const client = new Inty({ apiKey: token });

      // 调用 API
      const response = await client.api.v1.xxx();

      // 输出结果
      console.log('✅ 测试成功:', response);
      console.log('========================================\n');
      message.success('测试成功');
    } catch (err) {
      console.error('❌ 测试失败:', err);
      console.log('========================================\n');
      message.error('测试失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="test-component">
      <h4>功能名称</h4>
      <Button
        type="primary"
        onClick={handleTest}
        loading={loading}
        block
      >
        执行测试
      </Button>
    </div>
  );
};

export default YourTestComponent;
```

## 🎨 样式说明

- 所有测试组件共享 `.test-component` 样式类
- 样式定义在 `index.less` 中
- 支持响应式设计

## 💡 注意事项

1. **Token 管理**
   - Token 会自动保存到本地存储
   - 如果遇到认证错误，请重新执行游客登录

2. **控制台输出**
   - 所有测试结果都会输出到浏览器控制台
   - 使用统一的格式：开始标记 → 详细信息 → 结束标记

3. **错误处理**
   - 所有组件都包含完善的错误处理
   - 会区分认证错误、参数错误等不同类型

4. **测试数据**
   - 测试时请使用真实有效的 Agent ID
   - 可以先在主应用中创建 Agent，然后使用其 ID 进行测试

## 📚 相关文档

- [Inty SDK 使用文档](../../../backend/docs/inty-sdk使用文档.md)
- [Inty SDK 快速参考](../../../backend/docs/inty-sdk快速参考.md)

## 🤝 贡献

如需添加新的测试功能或改进现有功能，请遵循以下步骤：

1. 创建新的组件文件
2. 遵循现有代码风格
3. 添加完善的注释
4. 确保 TypeScript 类型正确
5. 测试功能正常工作

---

**最后更新**: 2025-10-31
