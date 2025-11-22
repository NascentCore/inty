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

```bash
# 1. 克隆仓库并初始化子模块：
git clone --recurse-submodules git@github.com:NascentCore/inty.git
```

Android App 开发使用 Android Studio 打开`inty/android_app`，
详情参考 [android_app/README.md](android_app/README.md)。

后端开发，代码位于 `app` 目录（目前正在逐步向 `backend` 目录迁移），
请参考 [backend/README.md](backend/README.md)。

如果子模块出现脏数据（如下图所示），可以按照下面的流程重置：

<img width="480" height="436" alt="image" src="https://github.com/user-attachments/assets/23852e45-cfe6-4686-9282-c138d40bf96f" />

```bash
# 清理子模块的缓存配置
git submodule deinit -f .

# 重新拉取子模块代码
git submodule update --init --recursive
```

更新子模块使用 [update_inty_sdk_submodule.sh](update_inty_sdk_submodule.sh)

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

## 如何修改代码库中的文件内容

以 [ui_configs.kt](android_app/app/src/main/kotlin/com/ai/intellimate/ui/ui_configs.kt#L96)
中的 `WhatsAppGroupInvite` 为例：

1. 打开 GitHub 文件链接：ui_configs.kt，点击右上角铅笔图标编辑文件，可以按照路径从 https://github.com/NascentCore/inty 找到对应的目标文件
   ![img_v3_02sa_4f309e3d-a334-4b25-8006-91f361222d5g](https://github.com/user-attachments/assets/18a2d9c0-a596-4095-bea3-18f376b33657)
2. 定位要修改的地方，修改
   ![img_v3_02sa_6259fdaf-e194-4d91-8120-56b79317f7ag](https://github.com/user-attachments/assets/af713402-c9da-4821-b46e-1a5eaeb7bc23)
3. 修改完成点击 commit changes，弹窗填入改动标题，其他不用修改，点击右下角 propose changes
   ![img_v3_02sa_f539d752-b939-405f-8ec7-98d696d47c8g](https://github.com/user-attachments/assets/bad0e20f-0b66-4265-8af0-4d18b152ee0d)
4. 下一个页面点击 create pull request 生成改动
   ![img_v3_02sa_a2fef23c-5902-4154-8ff6-9a97a1d384bg](https://github.com/user-attachments/assets/fa985e25-a821-4a14-91e9-5e164b387114)
5. 生成改动链接，发给@赵亚雄 确认；之后就可以提交
   ![img_v3_02sa_c2d1a841-1cbe-417f-a52b-04061565a83g](https://github.com/user-attachments/assets/165e57c6-b151-4968-9e67-cfbcff959d6f)

## 说明

更多详细信息请参考各子目录的 README 文件：
- 后端开发：参见 [backend/README.md](backend/README.md)
