# Chatbot with Image Selection Demo

这是一个基于 Gemini API 的聊天机器人演示，能够根据回复内容的情感自动选择合适的表情图像。

## 功能特性

- 🤖 基于 Gemini API 的智能对话
- 🎭 情感分析驱动的图像选择
- 💬 现代化的 React 聊天界面
- 🖼️ 静态图像库支持多种情感表达

## 项目结构

```
mock_live2d/
├── backend/                 # FastAPI 后端
│   ├── main.py             # 主应用（需要 Gemini API）
│   ├── demo_main.py        # 演示模式（无需 API）
│   ├── requirements.txt    # Python 依赖
│   ├── create_placeholder_images.py  # 生成占位图像
│   └── images/             # 静态图像文件
├── frontend/               # React 前端
│   ├── src/
│   │   ├── App.tsx         # 主组件
│   │   ├── App.css         # 样式文件
│   │   └── index.tsx       # 入口文件
│   └── package.json        # Node.js 依赖
├── start_backend.sh        # 后端启动脚本
├── start_frontend.sh       # 前端启动脚本
├── start_demo.sh           # 一键演示启动
└── README.md              # 说明文档
```

## 快速开始

### 方式一：完整模式（需要 Gemini API 密钥）

#### 1. 设置环境变量

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

#### 2. 启动后端服务

```bash
./start_backend.sh
```

#### 3. 启动前端应用

```bash
./start_frontend.sh
```

### 方式二：演示模式（无需 API 密钥）

一键启动完整演示：

```bash
./start_demo.sh
```

演示模式使用预设的回复和简单的情感分析，无需 Gemini API 密钥即可体验功能。

## 工作原理

1. **对话处理**: 用户发送消息后，后端调用 Gemini API 生成回复
2. **情感分析**: 使用 Gemini API 分析回复内容的情感倾向
3. **图像选择**: 根据情感标签从预定义的图像库中选择合适的图像
4. **智能优化**: 如果选择的图像与上一条消息相同，则不重复发送

## 支持的情感类型

- `happy` - 开心
- `sad` - 悲伤
- `angry` - 愤怒
- `surprised` - 惊讶
- `neutral` - 中性
- `excited` - 兴奋
- `worried` - 担心

## API 接口

### POST /chat

发送聊天消息并获取回复。

**请求体:**
```json
{
  "message": "用户消息",
  "conversation_history": [
    {
      "role": "user",
      "content": "之前的用户消息"
    },
    {
      "role": "assistant", 
      "content": "之前的助手回复",
      "image_url": "/images/happy1.jpg"
    }
  ]
}
```

**响应:**
```json
{
  "message": "助手回复",
  "image_url": "/images/happy1.jpg"
}
```

## 自定义图像

要添加新的情感图像，请：

1. 将图像文件放入 `backend/images/` 目录
2. 在 `backend/main.py` 的 `IMAGE_DATABASE` 中添加对应的情感标签和图像路径

## 技术栈

- **后端**: FastAPI, Google Generative AI
- **前端**: React, TypeScript
- **图像处理**: 静态文件服务
- **情感分析**: Gemini API

## 注意事项

- 确保已安装 Python 3.7+ 和 Node.js 14+
- 需要有效的 Gemini API 密钥
- 图像文件需要放在正确的目录中
- 建议在开发环境中使用，生产环境需要额外的安全配置