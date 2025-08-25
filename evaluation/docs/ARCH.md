# 技术架构

## 前端技术栈

```
React 18                    # 用户界面库
├── TypeScript              # 类型安全的JavaScript超集
├── Vite                    # 快速的构建工具和开发服务器
├── Ant Design 5            # 企业级UI组件库
├── @ant-design/icons       # 丰富的图标组件
└── Docker                  # 容器化部署
```

## 项目结构

```
app/static/evaluation/
├── components/                   # React组件库
│   ├── auth/                    # 认证相关组件
│   │   ├── AuthProvider.tsx    # 认证上下文提供者
│   │   └── AuthStatus.tsx      # 认证状态显示
│   ├── evaluation/              # 评测功能组件
│   │   ├── TestConfigForm.tsx   # 评测配置表单
│   │   ├── AgentSelector.tsx    # 智能体选择器
│   │   ├── QuestionManager.tsx  # 问题管理器
│   │   ├── MultiAgentChatDisplay.tsx # 多智能体对话展示
│   │   └── EvaluationMonitor.tsx # 实时评测监控
│   └── common/                  # 通用组件
├── pages/                       # 页面级组件
│   ├── EvaluationPage.tsx      # 评测创建和管理主页面
│   ├── EvaluationHistoryPage.tsx # 评测历史记录页面
│   ├── ChatPage.tsx            # 智能体聊天页面
│   ├── AgentManagePage.tsx     # 智能体管理页面
├── hooks/                       # React自定义Hooks
│   ├── useAgents.ts            # 智能体数据管理Hook
│   ├── useEvaluationSession.ts # 评测会话管理Hook
│   └── useForm.ts              # 表单状态管理Hook
├── services/                    # API服务层
│   ├── api.ts                  # 统一API客户端
│   ├── auth.ts                 # 认证服务
│   └── modelCache.ts           # 模型缓存服务
├── types/                       # TypeScript类型定义
│   └── index.ts                # 全局类型定义
├── styles/                      # 样式文件
│   └── index.css               # 全局样式
├── utils/                       # 工具函数库
├── Dockerfile                   # Docker构建文件
├── vite.config.ts              # Vite配置文件
├── tsconfig.json               # TypeScript配置
├── package.json                # 项目依赖和脚本
└── nginx.conf                  # Nginx配置文件
```
