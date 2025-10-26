# evaluation

Inty Evaluation（评测与运营工具），基于 React/TypeScript 与 Vite 构建。
当前前端在构建后被拷贝至后端 `FastAPI` 静态目录，并由后端统一在 `/evaluation` 路由提供访问。

- **⚠️ 注意：所有人操作的都是同一份后端数据，使用同样的 API key（仅用于 dev 环境）。请勿泄露或在公网展示。**

## Repo 初始化

```bash
git clone https://github.com/NascentCore/inty.git
cd inty
git submodule update --init --recursive
```

## 快速开始（后端集成方式）

方式一：本地直接运行后端并访问集成页面

```bash
# 构建前端并拷贝到 app/static/evaluation
./build_evaluation.sh

# 启动后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 浏览器访问（集成静态资源）
# http://localhost:8000/evaluation
```

方式二：使用 Docker 构建（多阶段构建自动产出并拷入静态资源）

```bash
docker build --build-arg CONFIG_FILE=config.yaml -t inty-backend .
docker run -p 8000:8000 -v $(pwd)/config.yaml:/config.yaml inty-backend

# 浏览器访问
# http://localhost:8000/evaluation
```

## 开发模式（HMR）

仍可使用前端开发服务器进行联调（HMR）——该模式下由脚本设置 `REACT_APP_API_BASE_URL` 等环境变量，并在本机 `:3000` 端口启动。

```bash
# 默认对接 `https://dev.inty.sxwl.ai/api/v1`
evaluation/start.sh

# 或指定本地后端
evaluation/start.sh --backend-url http://localhost:8000/api/v1
```

## 构建与预览（仅前端）

如需单独在 `evaluation/` 目录内构建并预览静态资源，可使用：

```bash
evaluation/build.sh
# 或（在 evaluation 目录）
npm install && npm run build && npm run preview
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

## 环境变量说明

- 集成构建（生产访问）：构建时不注入环境变量，前端使用相对路径访问后端 API。
- 开发模式（HMR）：由 `evaluation/start.sh` 设置下列变量，仅用于本地开发：
  - `REACT_APP_API_BASE_URL`：默认 `https://dev.inty.sxwl.ai/api/v1`
  - `INTY_BASE_URL`：从上者去掉 `api/v1` 的基础地址
  - `INTY_API_KEY`：仅 dev 用，勿泄露

脚本还会：

- 检测并尝试释放 `:3000` 端口
- 构建 `evaluation/inty_sdk`（包含手动安装 `tsc-multi`）

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

## 与后端集成（代码位置）

- 构建与拷贝脚本：`build_evaluation.sh`（构建 `evaluation/`，拷贝至 `app/static/evaluation/`）
- FastAPI 路由：`app/main.py`
  - 静态资源挂载：`/static` 指向 `app/static`
  - 页面入口：`GET /evaluation` 返回 `app/static/evaluation/index.html`
  - 资源访问：`GET /evaluation/{path}` 返回对应静态文件
- Docker 多阶段构建：`Dockerfile`
  - 第一阶段构建前端并将产物置于 `/app/static/evaluation/`
  - 第二阶段复制上述产物到后端镜像的 `app/static/evaluation/`

## Cursor Summary

- 技术栈：React + TypeScript + Vite；浏览器直连后端
- 集成访问：后端在 `/evaluation` 提供页面与静态资源
- 启动脚本：`evaluation/start.sh`（本地联调/HMR）
- 环境变量：`REACT_APP_API_BASE_URL`、`INTY_BASE_URL`、`INTY_API_KEY`
- 子模块：`evaluation/inty_sdk`；通过脚本或手动指令同步与构建
- 主要页面：`AgentManagePage`、`ChatPage`、`EvaluationPage`、`EvaluationHistoryPage`
