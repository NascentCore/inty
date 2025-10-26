# evaluation

Inty Evaluation（评测与运营工具），基于 React/TypeScript 与 Vite 构建，运行于浏览器，直接对接后端用于智能体（角色）管理、对话体验与评测。

- **⚠️ 注意：所有人操作的都是同一份后端数据，使用同样的 API key（仅用于 dev 环境）。请勿泄露或在公网展示。**

## Repo 初始化

```bash
git clone https://github.com/NascentCore/inty.git
cd inty
git submodule update --init --recursive
```

## 快速开始（对接 dev 后端）

```bash
# 默认对接 https://dev.inty.sxwl.ai/api/v1
# 启动并打开 http://localhost:3000/
evaluation/start.sh
```

## 对接本地后端

```bash
# 启动依赖（pgvector 数据库容器）
docker compose up pgvector -d

# 启动后端（初始化数据库并创建管理员）
./start.sh --dev

# 将前端指向本地后端
# 打开 http://localhost:3000/
evaluation/start.sh --backend-url http://localhost:8000/api/v1
```

## 构建与预览

```bash
# 在 evaluation 目录内进行生产构建
evaluation/build.sh

# 或使用 npm 指令（evaluation 目录）
npm install
npm run build
npm run preview
```

## SDK 子模块与版本

更新 evaluation/inty_sdk 子模块：

```bash
pushd evaluation/inty_sdk
git checkout main
git pull
popd
git commit -a -m '更新 evaluation/inty_sdk submodule'

# 同步生成 dist 并刷新 evaluation/package-lock.json
evaluation/start.sh
git commit -a -m '更新 package-lock.json'
git push
```

更新 inty_sdk 版本：

```bash
# 在仓库根目录运行
./build_evaluation.sh

# 若 evaluation/package-lock.json 中的 inty_sdk/dist 版本发生变化
# 请提交改动，创建 PR 并合并
```

示例参考：`https://github.com/NascentCore/inty/pull/655/files`

## 环境变量（由 start.sh 设置）

- `REACT_APP_API_BASE_URL`: 前端使用的后端 API 根路径，默认 `https://dev.inty.sxwl.ai/api/v1`
- `INTY_BASE_URL`: 从 `REACT_APP_API_BASE_URL` 去掉 `api/v1` 得到的基础地址
- `INTY_API_KEY`: 仅用于 dev 环境的测试密钥，切勿泄露

详见脚本 `evaluation/start.sh`，脚本会：
- 写入上述环境变量
- 在端口 3000 已被占用时尝试终止占用进程
- 构建 `evaluation/inty_sdk`（包含手动安装 `tsc-multi` 以规避 yarn 的安装问题）

## 目录与页面

- 交互式管理与对话、评测：
  - `pages/AgentManagePage.tsx`
  - `pages/ChatPage.tsx`
  - `pages/EvaluationPage.tsx`
  - `pages/EvaluationHistoryPage.tsx`
- 其他目录：
  - `components/`、`hooks/`、`services/`、`utils/`

## LangSmith 调试

在单角色聊天页面点击 LangSmith 图标查看调用链路；如未显示，请刷新页面。

<img width="800" height="1026" alt="image" src="https://github.com/user-attachments/assets/ab88bf82-fb3b-4cab-b169-bf7b0f17bdeb" />

## 功能预览

### 单角色聊天

与 APP 类似的聊天功能。

<img width="960" height="1756" alt="image" src="https://github.com/user-attachments/assets/f89e9c07-1b3e-487d-91f2-a2fd15de3fe3" />

### 智能体（角色）管理

<img width="960" height="1198" alt="image" src="https://github.com/user-attachments/assets/caefe026-62d9-4e48-8555-26a45ee5e9c2" />

### 智能体评测

<img width="480" height="1648" alt="image" src="https://github.com/user-attachments/assets/a19f42e0-2f94-435f-bb94-fd3d4a820be6" />
<img width="480" height="1464" alt="image" src="https://github.com/user-attachments/assets/29b15d93-92d5-476e-9bad-7ce4acb2dbb5" />

## 故障排查（FAQ）

- 端口被占用：`http://localhost:3000` 必须使用 3000 端口；`evaluation/start.sh` 会尝试终止占用进程
- Node/npm 未安装：脚本提供 nvm 自动安装选项；在 CI/服务器环境请自行安装
- `tsc-multi` 安装失败：脚本已通过 tarball 手动安装（见 `evaluation/start.sh`）

## Cursor Summary

- 技术栈：React + TypeScript + Vite；浏览器直连后端
- 启动脚本：`evaluation/start.sh`（设置环境变量、构建 SDK、启动 dev 服务器）
- 环境变量：`REACT_APP_API_BASE_URL`、`INTY_BASE_URL`、`INTY_API_KEY`
- 子模块：`evaluation/inty_sdk`；通过脚本或手动指令同步与构建
- 主要页面：`AgentManagePage`、`ChatPage`、`EvaluationPage`、`EvaluationHistoryPage`
