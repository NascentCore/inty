# Inty Evaluation（inty-eval/角色评测工具）

* **⚠️ 注意：所有人操作的都是同一份后端数据，使用同样的 API key**

这是一个使用 React/TypeScript 构建的运行于浏览器内的 Web 应用程序，用于评估 AI 角色、管理提示和显示聊天交互。

## 更新 inty_sdk 版本

本地运行 `./build_evaluation.sh` 然后如果 `evaluation/package-lock.json` 改变了
`inty_sdk/dist` 版本，则提交改动，创建 pull request 然后提交。
如 <https://github.com/NascentCore/inty/pull/655/files> 所示。

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

* Inty eval 是一个浏览器内运行的应用，直接与 backend 对接
* `postgres <---> backend <---> inty-eval`
* Inty eval 内的 API key 来自环境变量，详情见 [start.sh](start.sh)

页面列表

* 智能体管理页面：pages/AgentManagePage.tsx
* 智能体对话页面：pages/ChatPage.tsx
* 智能体评测页面：pages/EvaluationPage.tsx
* 智能体评测历史页面：pages/EvaluationHistoryPage.tsx
