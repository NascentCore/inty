# InTy - AI 智能伴侣平台

```text
IntelliMate: Ultimate companionship, reimagined with AI

Role-play with AI characters.
Create your own IntelliMate, powered by carefully tuned AI agents,
experience your own imagination.
```

[![Android App Tests](https://github.com/NascentCore/inty/actions/workflows/ci_android_app.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/ci_android_app.yaml)
[![Build and deploy Inty backend](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_backend.yml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_backend.yml)
[![Build and deploy IntelliMate web app](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_web_app.yml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_web_app.yml)
[![CI - Backend](https://github.com/NascentCore/inty/actions/workflows/ci_backend.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/ci_backend.yaml)
[![CI - Web App](https://github.com/NascentCore/inty/actions/workflows/ci_web_app.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/ci_web_app.yaml)
[![Sync AI characters from dev to prod](https://github.com/NascentCore/inty/actions/workflows/sync_ai_chars.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/sync_ai_chars.yaml)
[![Validate configs](https://github.com/NascentCore/inty/actions/workflows/validate_config.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/validate_config.yaml)

![](https://api.checklyhq.com/v1/badges/checks/6c7437a4-e239-473b-b08d-8285fc16ce4e?style=for-the-badge&theme=default&responseTime=true)
![](https://api.checklyhq.com/v1/badges/checks/1e149f71-dcad-49cc-a7bb-e0aecc429e6c?style=for-the-badge&theme=default&responseTime=true)

InTy 是一个 AI 智能伴侣平台，包含后端服务、Android 应用和 Web 应用。后端基于 FastAPI 和 PostgreSQL，集成了 LangChain 和 LangGraph 技术栈，支持多种 AI 模型和智能体管理。

## 快速开始

1. 克隆仓库并初始化子模块：

```bash
git clone --recurse-submodules git@github.com:NascentCore/inty.git
```

> 没有 SSH 权限的开发者可以改用 `https://github.com/NascentCore/inty-backend.git`。

2. 如需本地开发后端服务，请参考 [backend/README.md](backend/README.md)。

如果子模块出现脏数据（如下图所示），可以按照下面的流程重置：

<img width="480" height="436" alt="image" src="https://github.com/user-attachments/assets/23852e45-cfe6-4686-9282-c138d40bf96f" />

```bash
# 清理子模块的缓存配置
git submodule deinit -f .

# 重新拉取子模块代码
git submodule update --init --recursive
```

### Git submodule 常用操作

- **回滚到指定提交**：进入目标子模块目录后执行 `git checkout <commit-hash>`。
- **拉取子模块最新代码**：在仓库根目录执行 `git submodule update --remote --recursive`。
- **同步子模块远程信息**：在仓库根目录执行 `git submodule sync`

<img width="960" height="236" alt="image" src="https://github.com/user-attachments/assets/a3b34dad-45f4-43d0-b1fb-c066f8397bd2" />

更多进阶技巧可参考 [Git Submodule 使用指南](https://www.atlassian.com/git/articles/core-concept-workflows-and-tips)。

## 使用 Docker 容器本地运行后端服务和 Android app（适用于 app 开发者）

1. 访问 <https://docs.docker.com/desktop/setup/install/mac-install/> 安装 Docker Desktop。
2. 拷贝配置文件（config.yaml）及密钥文件到 inty-backend 代码库顶层目录。

    ```bash
    git clone git@github.com:NascentCore/inty-backend.git
    cd inty-backend

    mkdir -p .secrets

    # 拷贝 config.yaml 文件到代码库顶层目录下
    # 拷贝 cosmic-gizmo-424300-t1-6499a9d5bd94.json inty-firebase-key.json inty-backend-key.json
    # 这三个文件到代码库顶层目录下 .secrets/ 目录下
    # 然后运行下面的命令，服务在 http://localhost:8000
    docker compose up --build --detach

    # 删除所有容器及其挂载的存储卷
    # 如果不删除数据库卷，旧数据可能导致数据库 schema 不兼容而无法启动
    docker compose down --volumes
    ```

3. 创建端口映射后选择 local build type 构建 Android app：

   ```bash
   adb devices
   adb -s emulator-5554 reverse tcp:8000 tcp:8000
   ```

   <img width="600" height="1850" alt="image" src="https://github.com/user-attachments/assets/9dc4e50d-91b5-4fbf-b04c-2c154db42b29" />

## 项目结构

- `app/` - InTy 后端服务（Python FastAPI）
- `android_app/` - IntelliMate Android 应用（Kotlin Compose）
- `web_app/` - IntelliMate Web 应用（React）
- `evaluation/` - 运营工具（React）
- `backend/` - 后端相关文档和规划
- `alembic/` - 数据库迁移
- `scripts/` - 各类脚本
- `devops/` - 运维相关代码

更多详细信息请参考各子目录的 README 文件：
- 后端开发：参见 [backend/README.md](backend/README.md)
