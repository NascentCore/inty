# 仓库背景与组件

摘自 [`/AGENTS.md`](/AGENTS.md) 中与产品定位、目录与部署相关的说明。

## 产品定位（摘要）

Inty 代表 Intelligent Entity；本仓库是以该理念组织的智能体系统与消费者产品 Monorepo：Python 云端服务、Android 客户端、Ops 运营工具等。

- 智能体内核：[`/app/core/companion_harness/`](/app/core/companion_harness/)
- 工程师主要使用 [Cursor](https://cursor.com/)；产品经理侧可参考 Claude Code、OpenAI Codex 文档

[IntelliMate Android App](/android_app/)：传统角色扮演类 17+ 产品，基于后端 [chat completions](/app/core/chat.py)。

[iMate Android App](/imate_android_app/)：面向 35+ 男性用户，基于 [Companion Harness](/app/core/companion_harness/)。

## General background

- Components
  - IntelliMate app
    - [IntelliMate: the user-facing Android App](/android_app)
    - [Inty backend: IntelliMate Android APP's backend](/backend/inty/)
    - [Push worker: offline scheduled tasks processor](/backend/push_worker/)
    - [Ops: Inty operational web app](/web_app) and [corresponding Ops backend](/backend/ops)
      - Extract memory from user and AI chat messages
- Deployment
  - IntelliMate is published on Google Play
  - Inty backend, push worker, ops backend, are all deployed on 1 same GCE VM
    - TODO: Add service account key or SSH key for accessing the VM
  - All backend services have 2 stages `dev` `prod`
    - IntelliMate `debug` build type talks to `dev` backend, `release` build type talks to `prod` backend

## Android App Tips

- Do not try to run android app in kvm for testing, as the agent cloud environment has no kvm
- Use standard components: <https://developer.android.com/develop/ui/compose/components>

## Backend

- Backend services
  - Inty backend: `backend/inty` 支持 Android App 的主 API 后端，提供对话、生图、语音播报、语音通话等功能
  - Operational app:
    - `backend/ops` backend`evaluation/` operational app, creating iMates, view user behavior data etc.
  - Serving
  - 部署在一台 GCP VM
  - 后端所有应用都有 2 个环境：dev prod
    - .secrets/alien-paratext-461204-i9-cursor-log-viewer.json 可以用来访问

## Python-Kotlin HTTP APIs 数据类型定义

以下两处需同步修改：

- [Kotlin API 数据类型](/android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model)
- [Python HTTP API 数据类型](/app/schemas)
