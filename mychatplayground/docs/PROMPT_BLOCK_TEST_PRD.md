# 提示词板块效果测试工具 - 需求文档 

## 1. 功能概述

### 1.1 目标
提供一个 A/B 对比测试工具，用于验证**某个提示词板块**注入后是否对 AI 角色的回复产生影响。

### 1.2 应用场景
- 验证「用户记忆」板块是否让 AI 更了解用户
- 验证「角色背景」板块是否影响 AI 的行为风格
- 验证「输出格式要求」板块是否改变 AI 的回复结构
- 其他任意提示词板块的效果验证

### 1.3 核心机制
- **A 组**：不包含标记为「变量」的提示词板块
- **B 组**：包含标记为「变量」的提示词板块
- 同时执行 A/B 测试，对比回复差异

---

## 2. 页面结构

### 2.1 页面路径
`/prompt-block-test`

### 2.2 导航入口
在 `Sidebar.tsx` 中添加：
```
{ href: "/prompt-block-test", label: "🧪 提示词板块测试", description: "A/B 对比验证提示词板块效果" }
```

### 2.3 页面布局

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  模型选择：[下拉框]                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                      提示词板块编辑区                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ [类型: System ▼]                                    [↑][↓][×]      │   │
│  │ ┌───────────────────────────────────────────────────────────────┐  │   │
│  │ │ You are a friendly AI companion...                            │  │   │
│  │ └───────────────────────────────────────────────────────────────┘  │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ [类型: System ▼] ⭐ 变量板块（仅 B 组包含）          [↑][↓][×]      │   │
│  │ ┌───────────────────────────────────────────────────────────────┐  │   │
│  │ │ ## 关于这位用户...                                             │  │   │
│  │ └───────────────────────────────────────────────────────────────┘  │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ [类型: AI ▼]                                        [↑][↓][×]      │   │
│  │ ┌───────────────────────────────────────────────────────────────┐  │   │
│  │ │ Hello! How can I help you today?                              │  │   │
│  │ └───────────────────────────────────────────────────────────────┘  │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ [类型: Human ▼]                                     [↑][↓][×]      │   │
│  │ ┌───────────────────────────────────────────────────────────────┐  │   │
│  │ │ Hey! Nice to meet you!                                        │  │   │
│  │ └───────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  [+ 添加板块]                                                               │
│                                                                             │
│  消息预览：A 组 [4条消息] | B 组 [5条消息]  [展开查看]                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  测试模式：( ) 单轮独立测试    (•) 多轮脚本测试                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                           测试消息列表                                        │
│  [1] Hey! Nice to meet you~                              [↑][↓][编辑][×]    │
│  [2] I've been feeling stressed lately...                [↑][↓][编辑][×]    │
│  [3] What should I do this weekend?                      [↑][↓][编辑][×]    │
│  [+ 添加测试消息]                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                        [▶ 开始 A/B 对比测试]                                  │
├───────────────────────────────┬─────────────────────────────────────────────┤
│        A 组结果（不含变量板块） │        B 组结果（含变量板块）                 │
│  （实时展示，请求一条显示一条）  │  （实时展示，请求一条显示一条）               │
└───────────────────────────────┴─────────────────────────────────────────────┘
```

---

## 3. 功能详细设计

### 3.1 模型选择
- 下拉框选择 OpenRouter 模型
- 与其他页面共享模型列表加载逻辑
- 存储：`mychatplayground.promptBlockTest.modelId`

### 3.2 提示词板块编辑区

#### 3.2.1 板块结构
每个板块包含：
- **类型选择**：下拉框，选项：
  - `System` - 系统提示词（对应 role: "system"）
  - `AI` - AI 消息（对应 role: "assistant"）
  - `Human` - 用户消息（对应 role: "user"）
- **内容**：文本编辑框
- **是否为变量**：勾选框，标记该板块是否为 A/B 组之间的唯一变量
- **操作按钮**：上移 [↑]、下移 [↓]、删除 [×]

#### 3.2.2 唯一变量规则
- **只能有一个板块被标记为「变量」**
- 被标记为变量的板块：
  - 显示特殊标识（⭐ + "变量板块" 标签）
  - 显示提示："仅 B 组包含"
  - **A 组请求时：不包含此板块**
  - **B 组请求时：包含此板块**
- 尝试标记第二个板块时，自动取消之前的标记

#### 3.2.3 消息拼接逻辑（LangSmith 风格）

按板块顺序构建 messages 数组：

```typescript
// 示例板块配置
const blocks = [
  { type: "system", content: "You are a helpful assistant.", isVariable: false },
  { type: "system", content: "## User Memory\n...", isVariable: true },  // 变量
  { type: "assistant", content: "Hello! How can I help?", isVariable: false },
  { type: "user", content: "Hi there!", isVariable: false },
];

// A 组消息（不含变量）
const messagesA = [
  { role: "system", content: "You are a helpful assistant." },
  { role: "assistant", content: "Hello! How can I help?" },
  { role: "user", content: "Hi there!" },
];

// B 组消息（含变量）
const messagesB = [
  { role: "system", content: "You are a helpful assistant." },
  { role: "system", content: "## User Memory\n..." },
  { role: "assistant", content: "Hello! How can I help?" },
  { role: "user", content: "Hi there!" },
];
```

**注意**：多个连续的 `system` 类型板块会生成多个 system 消息，不会合并。

#### 3.2.4 消息预览
- 显示 A 组和 B 组的消息数量
- 点击「展开查看」可预览完整的提示词拼接效果

#### 3.2.5 数据结构
```typescript
type PromptBlock = {
  id: string;
  type: "system" | "assistant" | "user";
  content: string;
  isVariable: boolean;
  order: number;
};
```
存储：`mychatplayground.promptBlockTest.promptBlocks`

### 3.3 测试模式

#### 3.3.1 单轮独立测试
- 提供多个测试问题
- 每个问题**独立请求**，不保留上下文
- 请求时，将测试问题追加到基础 messages 末尾：
  ```
  [...baseMessages, { role: "user", content: testQuestion }]
  ```

#### 3.3.2 多轮脚本测试
- 提供多个测试问题
- 按顺序**逐个请求**，保留对话上下文
- 每次请求后，将 AI 回复和下一个问题追加到 messages

### 3.4 测试消息列表

#### 3.4.1 消息管理
- **添加**：点击「添加测试消息」
- **编辑**：点击「编辑」按钮或直接点击消息内容
- **删除**：点击「×」按钮
- **排序**：点击「↑」上移、「↓」下移

#### 3.4.2 数据结构
```typescript
type TestMessage = {
  id: string;
  content: string;
  order: number;
};
```
存储：`mychatplayground.promptBlockTest.testMessages`

### 3.5 测试执行

#### 3.5.1 执行按钮
- **一个按钮**：「▶ 开始 A/B 对比测试」
- 点击后**同时并行**执行 A 组和 B 组测试

#### 3.5.2 实时展示
- A/B 组同时开始，各自独立进度
- 每请求完一个问题，**立即展示**该问题的回复
- 显示各自进度（如 "2/5"）

#### 3.5.3 执行状态
- 未开始：显示占位提示
- 进行中：显示已完成的结果 + 当前正在请求的加载状态
- 已完成：显示全部结果 + "重新测试"按钮
- 出错：显示错误信息，支持重试

### 3.6 结果展示区

#### 3.6.1 布局
- 左右两栏对比：A 组（不含变量板块）| B 组（含变量板块）
- 每栏顶部显示组别标识、状态、进度

#### 3.6.2 单轮模式 UI（独立卡片）
```
┌─ 问题 1 ─────────────────────────┐
│ 👤 Hey! Nice to meet you~        │
│ 🤖 Hello! Nice to meet you too...│
└──────────────────────────────────┘
        ┄┄┄ 独立对话 ┄┄┄
┌─ 问题 2 ─────────────────────────┐
│ 👤 I've been feeling stressed... │
│ 🤖 I'm sorry to hear that...     │
└──────────────────────────────────┘
        ┄┄┄ 独立对话 ┄┄┄
```

#### 3.6.3 多轮模式 UI（连续对话流）
```
┌─ 连续对话 ───────────────────────┐
│ 👤 Hey! How's it going?          │
│ 🤖 Hey! I'm doing great...       │
│                                  │
│ 👤 I've been busy with work...   │
│ 🤖 That sounds tiring...         │
│                                  │
│ 👤 What should I do this weekend?│
│ 🤖 Based on what you told me...  │
└──────────────────────────────────┘
```

#### 3.6.4 导出功能
- 导出测试结果为 JSON 或 Markdown

---

## 4. 数据结构

### 4.1 localStorage Keys
| Key | 说明 |
|-----|------|
| `mychatplayground.promptBlockTest.modelId` | 选择的模型 ID |
| `mychatplayground.promptBlockTest.promptBlocks` | 提示词板块列表 JSON |
| `mychatplayground.promptBlockTest.testMessages` | 测试消息列表 JSON |
| `mychatplayground.promptBlockTest.testMode` | 测试模式 ("single" \| "multi") |

### 4.2 完整类型定义

```typescript
// 提示词板块
type PromptBlock = {
  id: string;
  type: "system" | "assistant" | "user";
  content: string;
  isVariable: boolean;
  order: number;
};

// 测试消息
type TestMessage = {
  id: string;
  content: string;
  order: number;
};

// 单条测试结果
type TestResultItem = {
  messageId: string;
  userMessage: string;
  aiReply: string;
  timestamp: string;
  status: "pending" | "loading" | "success" | "error";
  error?: string;
};

// 测试会话
type TestSession = {
  groupType: "A" | "B";
  testMode: "single" | "multi";
  modelId: string;
  results: TestResultItem[];
  status: "idle" | "running" | "completed" | "error";
};
```

---

## 5. API 调用逻辑

### 5.1 构建基础消息

```typescript
function buildBaseMessages(
  blocks: PromptBlock[], 
  includeVariable: boolean
): OpenRouterMessage[] {
  return blocks
    .filter(block => includeVariable || !block.isVariable)
    .sort((a, b) => a.order - b.order)
    .map(block => ({
      role: block.type === "system" ? "system" 
          : block.type === "assistant" ? "assistant" 
          : "user",
      content: block.content,
    }));
}

// A 组
const baseMessagesA = buildBaseMessages(blocks, false);
// B 组
const baseMessagesB = buildBaseMessages(blocks, true);
```

### 5.2 单轮模式请求

```typescript
async function runSingleRoundTest(
  baseMessages: OpenRouterMessage[],
  testMessages: TestMessage[],
  onResult: (result: TestResultItem) => void
) {
  for (const testMsg of testMessages) {
    onResult({ messageId: testMsg.id, status: "loading", ... });
    
    try {
      const response = await createOpenRouterChatCompletion({
        apiKey,
        request: {
          model: selectedModelId,
          messages: [
            ...baseMessages,
            { role: "user", content: testMsg.content }
          ],
          temperature: 0.7,
          max_tokens: 500,
        },
      });
      
      const aiReply = response.choices[0]?.message?.content || "";
      onResult({ messageId: testMsg.id, aiReply, status: "success", ... });
    } catch (error) {
      onResult({ messageId: testMsg.id, status: "error", error: error.message });
    }
  }
}
```

### 5.3 多轮模式请求

```typescript
async function runMultiRoundTest(
  baseMessages: OpenRouterMessage[],
  testMessages: TestMessage[],
  onResult: (result: TestResultItem) => void
) {
  const conversationHistory = [...baseMessages];

  for (const testMsg of testMessages) {
    conversationHistory.push({ role: "user", content: testMsg.content });
    onResult({ messageId: testMsg.id, status: "loading", ... });
    
    try {
      const response = await createOpenRouterChatCompletion({
        apiKey,
        request: {
          model: selectedModelId,
          messages: [...conversationHistory],
          temperature: 0.7,
          max_tokens: 500,
        },
      });
      
      const aiReply = response.choices[0]?.message?.content || "";
      conversationHistory.push({ role: "assistant", content: aiReply });
      onResult({ messageId: testMsg.id, aiReply, status: "success", ... });
    } catch (error) {
      onResult({ messageId: testMsg.id, status: "error", error: error.message });
      break;  // 多轮模式出错后停止
    }
  }
}
```

### 5.4 并行执行 A/B 测试

```typescript
async function runABTest() {
  const baseMessagesA = buildBaseMessages(blocks, false);
  const baseMessagesB = buildBaseMessages(blocks, true);
  
  // 并行执行
  await Promise.all([
    runTest(baseMessagesA, testMessages, updateResultA),
    runTest(baseMessagesB, testMessages, updateResultB),
  ]);
}
```

---

## 6. 实现优先级

### P0（核心功能）
- [ ] 页面框架和路由
- [ ] 模型选择
- [ ] 提示词板块编辑（增删改）
- [ ] 板块类型选择（System/AI/Human）
- [ ] 板块上下移动排序
- [ ] 唯一变量标记功能
- [ ] 消息拼接预览
- [ ] 测试模式切换
- [ ] 测试消息列表（增删改）
- [ ] 测试消息上下移动排序
- [ ] A/B 并行测试执行
- [ ] 实时结果展示
- [ ] 单轮/多轮 UI 区分展示

### P1（完整功能）
- [ ] 结果导出
- [ ] 错误重试

### P2（增强功能）
- [ ] 拖拽排序
- [ ] 测试历史记录

---

## 7. 文件结构

```
mychatplayground/web/src/app/
└── prompt-block-test/
    └── page.tsx          # 主页面组件
```


