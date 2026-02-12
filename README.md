# InTy - 长期 AI 情感陪伴

- **InTy 是基于 AI 的情感陪伴系统，不是伴侣/聚焦情感因为其没有物理实体（仅手机 App）、长期在于目标是建立长期关系（角色与用户、用户与长期陪伴体验/app）**
- **本代码库是多语言（Python 后端、Kotlin 安卓 app、Typescript 运营系统）monorepo**

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

## IntelliMate 2026 Q1 目标

**建立生活节奏（晨午晚仪式）+ 共同记忆（挚爱馆/歌/回顾）+ 角色人生线三位一体的长期陪伴底座，使关系可回溯、可延续、可生长。**

## 快速开始

[添加 SSH key 到你的 GitHub 账户](https://docs.github.com/zh/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account)

```bash
# 克隆仓库并初始化子模块：
git clone --recurse-submodules git@github.com:NascentCore/inty.git
```

Android Studio 打开`inty/android_app`，详情参考 [android_app/README.md](android_app/README.md)。

后端系统代码位于 `app` 目录（目前正在逐步向 `backend` 目录迁移），参考 [backend/README.md](backend/README.md)。

如果子模块出现脏数据（如下图所示），可以按照下面的流程重置：

<img width="480" height="436" alt="image" src="https://github.com/user-attachments/assets/23852e45-cfe6-4686-9282-c138d40bf96f" />

```bash
# 清理子模块的缓存配置
git submodule deinit -f .

# 重新拉取子模块代码
git submodule update --init --recursive

# 使用下面步骤启动后端服务
evaluation/build.sh # 构建评测 web ui 静态文件
cp devops/config.yaml.local config.yaml
# 创建虚拟环境供后端 python 代码运行
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 启动 postgres 数据库
docker compose up pgvector -d
# 注意拷贝 admin bearer token 用来登录 http://localhost:8000/evaluation
./start.sh --dev
```

<img width="1028" height="932" alt="image" src="https://github.com/user-attachments/assets/59c52323-9ee3-4042-85ca-39344815b71c" />

### 启动 Dummy 服务

```bash
docker compose up pgvector -d
cp devops/config.yaml.test config.yaml

# 修改相关 py 代码，会自动加载，无需重启
./start.sh --dev
```

修改 app/core/config.py 中的 APIEndpointsConfig `use_dummy_*` 等相关开关；
找到你需要返回特定测试值的 endpoints 文件

用 `local` build type 来构建 Android App IntelliMate 就能访问。
记住打开本地反向代理 `adb -s 34181JEHN02316 reverse tcp:8000 tcp:8000`


## 代码库其他组件说明

更多详细信息请参考各子目录的 README 文件：

- 后端开发：参见 [backend/README.md](backend/README.md)
- [mychatplayground](mychatplayground/README.md): 用于测试提示词和聊天效果的 web 工具

### 相关链接

1. [IntelliMate Figma 设计稿](https://www.figma.com/design/ASvjVuWFM13S3u5GdIJlTL/HeartMate?node-id=0-1&p=f&t=nxD7Qrq5d8fZXSYl-0)
2. [IntelliMate 飞书需求池文档](https://tricorder.feishu.cn/wiki/Vx8zwSRiwigRUlkOyF5czkmdnDg?table=tblrLV9XLqUmPBu8&view=vewP2B92zv)
3. [IntelliMate Firebase 崩溃报告](https://console.firebase.google.com/project/alien-paratext-461204-i9/crashlytics/app/android:com.ai.intellimate/issues?fb_gclid=CjwKCAjwwNbEBhBpEiwAFYLtGL7ajs2-xPHLL4coQR6eSTui8PqkfhB7tNmotp8PWywmhtvPMR2hKhoCr5QQAvD_BwE&time=24h&state=open&types=crash&tag=all&sort=eventCount)
4. [IntelliMate Google Play Consle](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/app-dashboard)
