# Inty Evaluation（inty-eval/角色评测工具）

- **⚠️ 注意：所有人操作的都是同一份后端数据**

这是一个使用 React/TypeScript 构建的运行于浏览器内的 Web 应用程序，用于评估 AI 角色、管理提示和显示聊天交互。

**出于安全性和维护成本考虑：inty-eval 使用本地运行，不提供共享的服务器部署**

- **共享的服务器部署需要比较复杂的部署维护：静态 html+nginx（nginx 有密码保护）**
- **共享的服务器部署存在长期维护成本**

## 使用步骤

1. 注册登录 GitHub，@yaxiong 邀请 sxwl.ai Email 加入 [NascentCore 组织](https://github.com/orgs/NascentCore)

   <img width="680" height="326" alt="image" src="https://github.com/user-attachments/assets/a4255e17-e51c-4244-8138-89cb1b3b4d65" />

2. 下载安装 [github desktop](https://desktop.github.com/download/)

   <img width="800" height="1152" alt="image" src="https://github.com/user-attachments/assets/3cb0721e-aaa3-4bfb-896a-f29eaa5acbb3" />

3. 下载安装 [node.js](https://nodejs.org/en/download/)

   <img width="680" height="1136" alt="image" src="https://github.com/user-attachments/assets/1eeba49f-f249-4451-ae84-781ab24fd960" />

4. 启动 GitHub Desktop，使用上述账户登录，通过网页认证，详情按屏幕提示操作
5. 在 GitHub Desktop 中克隆 inty 代码库

   <img width="600" height="1182" alt="image" src="https://github.com/user-attachments/assets/5c878ad4-b75c-43ce-92fb-349066c2b497" />

6. 然后打开终端：`cmd-space terminal`

   <img width="480" height="270" alt="image" src="https://github.com/user-attachments/assets/3cea99fd-2dc2-48f6-9efd-6928be881685" />

7. 在终端中下载安装 yarn：`npm install -g corepack`，在终端输入 `yarn` 验证安装是否成功
8. 在终端中打开 inty-eval：`cd Documents/GitHub/inty` 然后 `evaluation/start.sh`；如果系统提示权限，点击同意

## 开发步骤

```bash
git clone https://github.com/NascentCore/inty.git
cd inty

# 默认对接 https://dev.inty.sxwl.ai/api/v1
# 打开 http://localhost:3000/
evaluation/start.sh

# 如果需要对接本地运行的后端服务
# 会在数据库内初始化超级用户
docker compose up --build -d

# 或者手动启动 pgvector，然后手动启动后端服务
docker compose up pgvector -d
# --dev 选项会初始化数据库，向内填充管理员账户
./start.sh --dev

# 指向本地服务
# 打开 http://localhost:3000/
evaluation/start.sh --backend-url http://localhost:8000/api/v1
```

## 更新 inty sdk submodule

```bash
pushd evaluation/inty_sdk
git checkout main
git pull
popd
git commit -a -m '更新 evaluation/inty_sdk submodule'
# 更新 evaluation/package-lock.json
evaluation/start.sh
git commit -a -m '更新 package-lock.json'
git push
```

## langsmith 上查看大模型调用请求

点击单角色聊天的 langsmith 标志；如请求没有显示，则需要刷新页面
<img width="800" height="1026" alt="image" src="https://github.com/user-attachments/assets/ab88bf82-fb3b-4cab-b169-bf7b0f17bdeb" />

## 架构简介

- Inty eval 是一个浏览器内运行的应用，直接与 backend 对接
- `postgres <---> backend <---> inty-eval`
- Inty eval 内的 API key 来自环境变量，详情见 [start.sh](start.sh)

页面列表

- 智能体管理页面：pages/AgentManagePage.tsx
- 智能体对话页面：pages/ChatPage.tsx
- 智能体评测页面：pages/EvaluationPage.tsx
- 智能体评测历史页面：pages/EvaluationHistoryPage.tsx
