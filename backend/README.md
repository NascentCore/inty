# InTy 后端服务

本仓库包含两个 FastAPI 应用：

- **backend/inty**：主后端，面向 IntelliMate Android 的 API。默认端口 8000。
- **backend/ops**：运营平台，提供 evaluation Web UI 与完整 `/api/v1`（evaluation、festival_memory + 与 Android 共用的 shared 端点）。默认端口 8001，Cloud Run 下使用 `PORT`（默认 8080）。部署域名：ops.inty.cc、dev.ops.inty.cc。

## 本地启动后端服务

```bash
# 启动数据库服务
docker run --rm --name pg-vec-inty -p 5432:5432 \
   -e POSTGRES_PASSWORD=sxwl666! -e POSTGRES_DB='inty' -d postgres:16

# 安装后端 Python 服务依赖
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 安装后端服务配置
cp devops/config.yaml.test config.yaml
./backend/inty/start.sh --dev
```

启动 Ops（evaluation 专用，可与 inty 同时运行）：

```bash
# 跳过 evaluation 前端构建（加快启动；需已有 app/static/evaluation）
./backend/ops/start.sh --local --no-build-frontend
# 默认 http://localhost:8001，Cloud Run 下 PORT=8080；需重建静态资源时去掉 --no-build-frontend
```

## GCS 配置

GCS public access

<img width="800" alt="image" src="https://github.com/user-attachments/assets/9230dc1f-1430-467b-b12e-bfba1def3922" />

获取 GCP 凭证密钥 JSON 文件以允许后端访问 GCS buckets：

<img width="3018" height="1218" alt="image" src="https://github.com/user-attachments/assets/df5c7bfb-b4ad-4d0a-b4cb-65b25c7d4560" />

## Chat LLM 与记忆抽取分离配置

- **默认**：Agent 聊天与记忆抽取均使用 `agent.base_url` + `agent.api_key`（如 OpenRouter）。
- **可选**：在配置中设置 `agent.chat_llm_base_url` 与 `agent.chat_llm_api_key` 后，**仅 Agent 聊天**使用该端点（如自建 LiteLLM）；**记忆抽取**仍使用 `base_url` + `api_key`。
- 每条 AI 聊天消息的 `meta_data.llm_provider` 会记录实际使用的网关：`openrouter` 或 `litellm`。

## 部署

详情查看：.github/workflows/build_and_deploy_backend.yml

## 服务帐号密钥生成

配置文件中需要配置 GCS 和 FireBase 的服务帐号密钥

### Firebase 服务账号密钥生成

1. 进入 Firebase Console：
   - 访问 <https://console.firebase.google.com/>
   - 选择项目（Inty）

2. 生成服务账号密钥：
   - 在项目设置 -> 服务账号 -> 生成新的私钥
   - 下载的文件重命名为：inty-firebase-key.json

### Google Cloud Storage 服务账号密钥生成

1. 进入 Google Cloud Console：
   - 访问 <https://console.cloud.google.com/>
   - 选择项目（Inty）

2. 创建服务账号（service account）：
   - 设置 "roles/storage.admin" 角色
   - 点击创建的服务帐号 -> 密钥 -> 创建新密钥
   - 下载的文件重命名为：inty-backend-key.json
