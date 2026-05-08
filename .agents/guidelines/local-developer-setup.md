# 人类工程师本地快速开始与链接

摘自 [`/AGENTS.md`](/AGENTS.md) 中「For human engineers」「快速开始」「相关链接」。

## For human engineers

![](https://api.checklyhq.com/v1/badges/checks/6c7437a4-e239-473b-b08d-8285fc16ce4e?style=flat&theme=default&responseTime=true)
![](https://api.checklyhq.com/v1/badges/checks/1e149f71-dcad-49cc-a7bb-e0aecc429e6c?style=flat&theme=default&responseTime=true)
![](https://api.checklyhq.com/v1/badges/checks/f2988f0a-f58a-4e75-87bc-e5700869ba68?style=flat&theme=default&responseTime=true)

[![Android App Tests](https://github.com/NascentCore/inty/actions/workflows/ci_android_app.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/ci_android_app.yaml)
[![CI - Backend](https://github.com/NascentCore/inty/actions/workflows/ci_backend.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/ci_backend.yaml)
[![CI - Web App](https://github.com/NascentCore/inty/actions/workflows/ci_web_app.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/ci_web_app.yaml)
[![Validate configs](https://github.com/NascentCore/inty/actions/workflows/validate_config.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/validate_config.yaml)

[![dev-prod 同步 AI 角色](https://github.com/NascentCore/inty/actions/workflows/sync_ai_chars.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/sync_ai_chars.yaml)
[![Release - IntelliMate GPlay 内测轨道](https://github.com/NascentCore/inty/actions/workflows/build_and_upload_android.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/build_and_upload_android.yaml)
[![Release - 构建部署 Inty Backend](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_backend.yml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_backend.yml)
[![Release - 构建部署 Inty Push Worker](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_push_worker.yml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_push_worker.yml)

## 快速开始

[添加 SSH key 到你的 GitHub 账户](https://docs.github.com/zh/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account)

```bash
# 克隆仓库并初始化子模块：
git clone --recurse-submodules git@github.com:NascentCore/inty.git
```

Android Studio 打开`inty/android_app`，详情参考 [android_app/README.md](/android_app/README.md)。

后端系统代码位于 `app` 目录（目前正在逐步向 `backend` 目录迁移），参考 [backend/README.md](/backend/README.md)。

如果子模块出现脏数据（如下图所示），可以按照下面的流程重置：

<img width="480" height="436" alt="image" src="https://github.com/user-attachments/assets/23852e45-cfe6-4686-9282-c138d40bf96f" />

```bash
# 清理子模块的缓存配置
git submodule deinit -f .

# 重新拉取子模块代码
git submodule update --init --recursive

# 使用下面步骤启动后端服务
cp devops/config.yaml.local config.yaml

# 创建虚拟环境供后端 python 代码运行
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 启动 postgres 数据库
docker run --rm --name pg-inty -p 5432:5432 \
  -e POSTGRES_PASSWORD=sxwl666! \
  -e POSTGRES_DB=inty \
  -d postgres:16

# 启动主后端（Android API）
./backend/inty/start.sh --dev

# 启动 ops 平台（evaluation Web UI + ops API，默认 8001）
./backend/ops/start.sh --local
```

本地联调：本地后端+Android Studio App（USB 连接、wifi 连接不支持）指向本地后端

```bash
# 打开 Android Studio
# 选择 debug build type，编译运行
# 然后在 me->settings->backend 选择 local

# 同时打开端口代理、让模拟器可以访问本机端口
# -s 在多个模拟器时可以指向特定模拟器
adb reverse [-s <设备 ID>] tcp:8000 tcp:8000
```

## 相关链接

1. [IntelliMate Figma 设计稿](https://www.figma.com/design/ASvjVuWFM13S3u5GdIJlTL/HeartMate?node-id=0-1&p=f&t=nxD7Qrq5d8fZXSYl-0)
2. [IntelliMate 飞书需求池文档](https://tricorder.feishu.cn/wiki/Vx8zwSRiwigRUlkOyF5czkmdnDg?table=tblrLV9XLqUmPBu8&view=vewP2B92zv)
3. [IntelliMate Firebase 崩溃报告](https://console.firebase.google.com/project/alien-paratext-461204-i9/crashlytics/app/android:com.ai.intellimate/issues?fb_gclid=CjwKCAjwwNbEBhBpEiwAFYLtGL7ajs2-xPHLL4coQR6eSTui8PqkfhB7tNmotp8PWywmhtvPMR2hKhoCr5QQAvD_BwE&time=24h&state=open&types=crash&tag=all&sort=eventCount)
4. [IntelliMate Google Play Consle](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/app-dashboard)
